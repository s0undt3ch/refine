# Installation

## Using pip

To install the `re-code` tool for use in the CLI, use the following command:

```sh
pip install re-code
```

## Using pre-commit

To use the `re-code` tool with pre-commit, add the following configuration to your `.pre-commit-config.yaml` file:

```yaml
- repo: https://github.com/s0undt3ch/re-code
  rev: v1.0.0  # Use the appropriate version or branch
  hooks:
    - id: re-code
```

Then, install the pre-commit hook by running:

```shell
pre-commit install --install-hooks
```

This will set up the ``re-code`` tool to run automatically on your codebase as part of the pre-commit hooks.
