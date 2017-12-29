""" Behave environment setup module. """

# pylint: disable=C0111, E0602, E0102, W0613

import os
import time
import logging
import logging.handlers
import csv
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions


def before_all(context):
    context.fail_count = 0
    context.username = context.config.userdata.get('username')
    context.password = context.config.userdata.get('password')
    context.job_name = context.config.userdata.get('job_name')
    if context.config.userdata.get('browser'):
        context.driver = context.config.userdata.get('browser').lower()


def before_feature(context, feature):
    current_feature = feature.filename.split('.')[0][9:]

    log_filename = os.path.join(os.path.abspath(__file__).split('features')[0], 'logs',
                                current_feature + '.log')
    logger = logging.getLogger('job')       # pylint: disable=C0103
    jobhandler = logging.handlers.RotatingFileHandler(
        filename=log_filename, maxBytes=10485760, backupCount=5)
    logformat = logging.Formatter('%(asctime)s %(levelname)s : %(name)s | %(message)s')
    jobhandler.setFormatter(logformat)
    logger.addHandler(jobhandler)
    logger.setLevel(logging.DEBUG)

    logger.info('Beginning feature \"%s\".', current_feature)


def before_scenario(context, scenario):
    logger = logging.getLogger('job')

    if context.driver == 'firefox':
        context.browser = webdriver.Firefox(
            firefox_binary='C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe',
            firefox_profile='C:\\SeleniumWebdrivers\\FFProfile',
            log_path='logs\\geckodriver.log',
            executable_path="C:\\SeleniumWebdrivers\\geckodriver.exe")
        logger.debug('Firefox webdriver will be used.')

    else:
        chrome_options = ChromeOptions()
        chrome_options.add_argument('--disable-extentions')
        chrome_options.add_argument('test-type')
        chrome_options.add_argument('--enable-automation')
        chrome_options.add_argument('--js-flags=--expose-gc')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('test-type=browser')
        chrome_options.add_argument('disable-infobars')

        chrome_args = ', '.join([row for row in chrome_options.arguments])
        logger.debug('Chrome webdriver will be used with arguments: %s', chrome_args)
        context.browser = webdriver.Chrome(
            chrome_options=chrome_options,
            executable_path='C:\\SeleniumWebdrivers\\chromedriver.exe')

    context.browser.maximize_window()


def after_step(context, step):
    logger = logging.getLogger('job')

    if step.status == 'failed' or context.failed:
        logger.error('Step \"%s\" has failed with error: %s', step.name, step.error_message)
    else:
        logger.info('Step \"%s\" finished with status %s in %.3f seconds.',
                    step.name, step.status, step.duration)


def after_scenario(context, scenario):
    context.browser.quit()


def after_feature(context, feature):
    logger = logging.getLogger('job')

    if context.failed:
        logger.error('Feature \"%s\" has failed.', feature.name)
        context.fail_count += 1
    if context.fail_count > 1:
        logger.error('Feature \"%s\" has failed more than once. Exiting...', feature.name)
        sys.exit("Too many feature failures.")
    else:
        current_feature = feature.filename.split('.')[0][9:]
        logger.info('Feature \"%s\" took %.3f seconds to complete.',
                    current_feature, feature.duration)


def after_all(context):
    if os.path.exists(os.path.join('results', context.job_name + '_results.json')):
        durations = []
        with open(os.path.join('results', context.job_name + '_results.json')) as results:
            json_data = json.load(results)
            for step in json_data[0]['elements'][0]['steps']:
                try:
                    durations.append(step['result']['duration'])
                except KeyError:
                    break

        durations = ['{:.3f}'.format(i) for i in durations]
        durations.insert(0, time.strftime('%Y-%m-%d %H:%M:%S'))
        with open(os.path.join('results', context.job_name + '_results.csv'), 'ab+') as csvfile:
            durationwriter = csv.writer(csvfile)
            durationwriter.writerow(durations)
    else: pass
