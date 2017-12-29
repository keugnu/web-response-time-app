""" step definitions for the site1 test """

# pylint: disable=C0111, E0602, E0102

from behave import use_step_matcher
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


A_VERY_LONG_WAIT = 30
use_step_matcher("re")


@given("I open site1")
def step_impl(context):
    pass


@when("I submit the site1 login form")
def step_impl(context):
    pass


@then("I verify that I have logged in successfully and the site is finished loading")
def step_impl(context):
    pass
