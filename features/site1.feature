Feature: Response times for site1

  Scenario: Measure response times for site1
    Given I open site1
    When  I submit the site1 login form
    Then  I verify that I have logged in successfully and the site is finished loading
