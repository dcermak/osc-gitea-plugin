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

  Scenario: Delete a forked package
    When I set the working directory to "{context.tmpdir}/Virtualization:containers/trivy"
    And I run osc "fork"
    When I run osc "fork delete --yes"
    Then stdout contains "{context.gitea_user}/trivy"

  Scenario: Fork a package with scmsync
    When I set the working directory to "{context.tmpdir}/Virtualization:containers/trivy"
    And I run osc "fork --create-scmsync"
    When I run "git remote -v"
    Then stdout contains "{context.gitea_user}"
    When I run osc "meta pkg home:{context.osc_user}:branches:Virtualization:containers trivy"
    Then stdout contains "<scmsync>https://src.opensuse.org/{context.gitea_user}/trivy.git#factory</scmsync>"
