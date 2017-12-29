"""
This module contains the scheduler process and all functions to begin a new process as well as thier
supporting functions.
"""
# pylint: disable=C0103, W0621, C0411

import os
import hashlib
import logging
import logging.config
import logging.handlers
import datetime
import json
import yaml
import webtest

from time import sleep
from subprocess import run, TimeoutExpired
from apscheduler.schedulers.background import BackgroundScheduler


def start_logging():
    """ Initializes all logging from logging.yaml. """

    logging_config = yaml.safe_load(open('logging.yaml'))
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger('top')
    logger.debug('Logging initialized.')


def create():
    """
    Initailizes all the jobs from the configuration file and sends them as a list to the scheduler.
    """

    logger = logging.getLogger('top')

    webtestconf = yaml.safe_load(open(PATH_TO_CONF))

    add_jobs = []
    for key, value in webtestconf.items():
        add_jobs.append(webtest.WebTest(key,
                                        value['interval'],
                                        value['browser'],
                                        value['username'],
                                        value['password']
                                       ))

        logger.debug('Created WebTest(%s, %d, %s)', key, value['interval'], value['browser'])
    return add_jobs


def find_next_run(scheduler):
    """
    Returns the time for the next scheduled run of a task or the current time if no tasks
    are scheduled.

    Args:
        scheduler (BackgroundScheduler): scheduler object for apscheduler.
    """
    toplogger = logging.getLogger('top')

    try:
        list_of_next_run_times = []
        for task in scheduler.get_jobs():
            list_of_next_run_times.append(task.next_run_time)
        return max(list_of_next_run_times)
    except ValueError:
        toplogger.warning('There are no scheduled jobs.')
        return datetime.datetime.now()


def seleniumtest(curr_job):
    """
    Spawns test processes.

    Args:
        curr_job (WebTest): contains info for the new process.
    """

    logger = logging.getLogger('top')

    path_of_test = os.path.join(os.getcwd(), 'features', curr_job.name)
    path_of_results = os.path.join(os.getcwd(), 'results', curr_job.name)
    userdata = ''.join([' -D username=', curr_job.username,
                        ' -D password=', curr_job.password,
                        ' -D job_name=', curr_job.name,
                        ' -D browser=', curr_job.browser,
                        ' -f json.pretty', ' --no-logcapture', ' --no-summary',
                        ' -o ', path_of_results, '_results.json'])

    test_durations = []
    for i in range(5):
        try:
            logger.info('Run %d/5 of %s starting.', i+1, curr_job.name)
            run(''.join(['behave ', path_of_test, '.feature', userdata]), timeout=1800)
            step_durations = []
            with open(os.path.join('results', curr_job.name + '_results.json')) as results:
                try:
                    json_data = json.load(results)
                    for step in json_data[0]['elements'][0]['steps']:
                        try:
                            step_durations.append(step['result']['duration'])
                        except KeyError:    # raised when steps were skipped
                            break
                    step_durations = [float(i) for i in step_durations]
                    test_durations.append(sum(step_durations))
                except ValueError:      # raised when the json file is blank
                    logger.error('%s_results.json could not be loaded.', curr_job.name)
        except TimeoutExpired:
            logger.critical('The test has timed out. Run %s/5', i)
        logger.info('Run %d/5 of %s has finished.', i+1, curr_job.name)

    test_results_file = os.path.join(os.getcwd(), 'results', 'totals', curr_job.name + '.txt')

    if len(test_durations) > 3:
        test_durations.remove(max(test_durations))
        test_durations.remove(min(test_durations))

    with open(test_results_file, 'w') as outfile:
        try:
            num = sum(test_durations) / len(test_durations)
            outfile.write('{:.3f}'.format(num))
            outfile.write('\n')
        except ZeroDivisionError:
            logger.debug('len(test_durations) is zero.')
            logger.error('%s has failed and thus cannot calculate the average.', curr_job.name)


def check_for_updates(scheduler, init_conf_md5):
    """
    Checks the config file for updates and applies them to the scheduler.

    Args:
        scheduler (BackgroundScheduler): scheduler object for apscheduler.
        init_conf_md5 (string): md5 checksum of webtesterconf.yaml before the function call.
    """
    global init_conf        # pylint: disable=W0603

    logger = logging.getLogger('listener')

    if os.path.exists(PATH_TO_CONF):
        logger.debug('Checking for updates to the jobs config...')

        new_md5 = hashlib.md5(open(PATH_TO_CONF, 'rb').read()).hexdigest()

        if init_conf_md5 == new_md5:
            logger.debug('No change detected in the jobs configuration.')
        else:
            logger.warning('A change has been detected in the jobs config file.')

            new_conf = yaml.safe_load(open(PATH_TO_CONF))
            diff = {k : new_conf[k] for k in set(new_conf) - set(init_conf)}

            while True:
                try:
                    name, values = diff.popitem()
                    interval = values['interval']
                    browser = values['browser']
                    username = values['username']
                    password = values['password']

                    next_run_time = find_next_run(scheduler) + datetime.timedelta(0, 900)
                    add_job = webtest.WebTest(name, interval, browser, username, password)
                    scheduler.add_job(func=seleniumtest,
                                      trigger='interval',
                                      seconds=add_job.interval,
                                      args=[add_job],
                                      next_run_time=next_run_time,
                                      misfire_grace_time=10
                                     )
                    logger.info('Added %s to queue. Next run: %s', str(add_job), next_run_time)
                except KeyError:
                    logger.warning('Finished adding all additional jobs in the config.')
                    break

            init_conf_md5 = new_md5     # setting the new hash after update
            init_conf = new_conf        # setting new conf content after update
    else:
        # logger.addHandler('top')
        logger.error('The config file could not be located by the listener in %s', PATH_TO_CONF)
        # logger.removeHandler('top')


def find_file(filename, start_path):
    """
    Looks for a file with exact name of filename and returns its absolute path.

    Args:
        filename (string): the file name that will be searched for.
        start_path (string): where the search will begin.
    """

    for root, dirs, files in os.walk(start_path):           # pylint: disable=W0612
        if filename in files:
            return os.path.join(root, filename)

def main():
    """ Begin. """

    start_logging()
    toplogger = logging.getLogger('top')

    scheduler = BackgroundScheduler()
    jobs = create()
    last_scheduled = find_next_run(scheduler)

    for i, job in enumerate(jobs):
        next_run_time = last_scheduled + datetime.timedelta(0, (i+1)*900)

        scheduler.add_job(func=seleniumtest,
                          trigger='interval',
                          seconds=job.interval,
                          args=[job],
                          next_run_time=next_run_time,
                          misfire_grace_time=10,
                          max_instances=3
                         )

        toplogger.debug('Added job %s to scheduler.', str(job))

    scheduler.add_job(func=check_for_updates,
                      trigger='interval',
                      seconds=300,
                      args=[scheduler, init_conf_md5],
                      misfire_grace_time=5,
                     )

    scheduler.start()
    print('Press Ctrl+C to exit')

    # Execution will block here until Ctrl+C is pressed.
    try:
        while True:
            sleep(2)
    except (KeyboardInterrupt, SystemExit):
        toplogger.critical('KeyboardInterrupt encountered. Stopping...')


if __name__ == '__main__':
    PATH_TO_CONF = find_file('webtesterconf.yaml', os.getcwd())
    init_conf_md5 = hashlib.md5(open(PATH_TO_CONF, 'rb').read()).hexdigest()
    init_conf = yaml.safe_load(PATH_TO_CONF)
    main()
