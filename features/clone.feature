Feature: Clone a package

  Background:
    Given I set the working directory to "{context.tmpdir}"
    Given I create a tea config for the user "{context.gitea_user}" using token "{context.gitea_token}"

  Scenario: Clone trivy
    And I run osc "clone trivy"
    Then stdout contains "{context.tmpdir}/trivy"
    When I run "ls"
    Then stdout contains "trivy"
    When I set the working directory to "{context.tmpdir}/trivy"
    And I run osc "st"
    Then stdout is
      """
      """
    And I run "git remote -v"
    Then stdout contains "origin"
