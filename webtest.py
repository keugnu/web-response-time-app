"""
This is a class for creating web test objects.
"""

class WebTest(object):
    """ The web test object """

    def __init__(self, name, interval, browser, username, password):
        self.name = name
        self.interval = interval
        self.browser = browser
        self.username = username
        self.password = password


    def __repr__(self):
        return 'WebTest({}, {}, {})'.format(self.name, self.interval, self.browser)
