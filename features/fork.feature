Feature: Fork a package

  Background:
    Given I set the working directory to "{context.tmpdir}"
    Given I create a tea config for the user "{context.gitea_user}" using token "{context.gitea_token}"
    And I run osc "checkout Virtualization:containers/trivy"

  Scenario: Fork package
    When I set the working directory to "{context.tmpdir}/Virtualization:containers/trivy"
    And I run osc "fork"
    Then stdout contains "Created fork"
    And stdout contains "src.opensuse.org:{context.gitea_user}/trivy.git"
    And stderr is
      """
      """
    And I run "git remote -v"
    Then stdout contains "origin"
    And stdout contains "{context.gitea_user}"
    And I run "git remote get-url origin"
    Then stdout is
      """
      https://src.opensuse.org/pool/trivy.git
      """
    And I run "git remote get-url {context.gitea_user}"
    Then stdout contains "src.opensuse.org:{context.gitea_user}/trivy.git"

  Scenario: Fork an already forked package
    When I set the working directory to "{context.tmpdir}/Virtualization:containers/trivy"
    And I run "git remote -v"
    Then stdout contains "origin"
    When I run osc "fork"
    Then stdout contains "Reusing existing fork"
    And I run "git remote get-url {context.gitea_user}"
    Then stdout contains "src.opensuse.org:{context.gitea_user}/trivy.git"
