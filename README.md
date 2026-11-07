# basic-template

Minimal GitHub repository template with common automation.

## Included files

- `.github/workflows/assign-pr.yml`: assigns unassigned pull requests to the repository maintainer. Set the `PR_ASSIGNEE` repository variable to override the assignee. For repositories owned by an organization, `PR_ASSIGNEE` is required.
- `.github/dependabot.yml`: checks GitHub Actions dependencies daily.

## Usage

Create a new repository using this GitHub template. Configure `PR_ASSIGNEE` if the default repository-owner assignment is not suitable.

