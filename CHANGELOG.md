# Changelog

All notable changes to this project will be documented in this file.

## [0.13.0](https://github.com/s0undt3ch/refine/releases/tag/0.13.0) - 2025-07-09

### 🚀 Features

- *(progress)* Allow NOT to show progress output.
- *(testing)* We now get diff's from pytest on `refine.testing`

### 🚜 Refactor

- *(config)* Make sure the config object gets updated with CLI options

## [0.12.4](https://github.com/s0undt3ch/refine/releases/tag/0.12.4) - 2025-06-10

### ⚙️ Miscellaneous Tasks

- *(depedencies)* Lock to libcst < 1.8.0 since it breaks refine

## [0.12.3](https://github.com/s0undt3ch/refine/releases/tag/0.12.3) - 2025-06-10

### 🚀 Features

- *(flags)* Reduced complexity of the `cli-dashes-over-underscores` codemod

### 🐛 Bug Fixes

- *(sqlfluff)* Set `sqlfluff` logging level to `INFO` on verbose
- *(cli)* Hardcode `**/__pycache__/**` into the exclude filters
- *(config)* Properly run validation checks on codemos configs

### 💼 Other

- *(deps)* Bump astral-sh/setup-uv from 5 to 6

### ⚙️ Miscellaneous Tasks

- *(dependencies)* Upgrade to ``sqlfluff==3.4.0``
- *(pre-commit)* Update pre-commit hook versions
- *(pre-commit)* Lock `libcst` version in pre-commit config
- *(pre-commit)* Update ruff check pre-commit hook to `ruff-check`
- *(release)* Lock to `action-gh-release@2.2.2` since 2.3.0 is broken

## [0.12.2](https://github.com/s0undt3ch/refine/releases/tag/0.12.2) - 2025-04-21

### 🚀 Features

- *(imports)* Simplify adding and removing imports in codemods
- *(logging)* Allow passing `-v/--verbose` to switch to debug logging
- *(SQL regex matching)* Separated logic into a few reusable utilities
- *(cli)* Differentiate `--exclude` and `--exclude-extend`
- *(cli)* Differentiate `--select` and `--select-extend`
- *(cli)* Differentiate `--codemods-path` and `--codemods-path-extend`
- *(sql formatter)* Skip modules that don't contain query strings

### 🐛 Bug Fixes

- *(sqlfmt)* Remove auto skip tests files logic
- *(sqlfmt)* Properly handle big query strings

### 🚜 Refactor

- *(cli)* Refactor CLI code to enable simplified testing

### 🧪 Testing

- *(registry)* Refactor registry to enable testing
- *(cli)* Add CLI usage tests

### ⚙️ Miscellaneous Tasks

- *(cleanup)* Remove unused variable
- Define `__all__` in `refine/__init__.py`
- *(config)* Add `as_dict` method to `refine.config.Config`
- *(pre-commit)* Run `ruff-format` before `ruff`

## [0.12.0](https://github.com/s0undt3ch/refine/releases/tag/0.12.0) - 2025-04-06

### 🚀 Features

- *(config)* Replace `pydantic` with `msgspec`

### ⚙️ Miscellaneous Tasks

- *(release)* Automate the releases
- *(changelog)* Update changelog with links to tags
- *(docs)* Build documentation in the same CI job
- *(gh-actions)* Build docs and test after pre-commit completes
- *(docs)* Build and publish docs as the final step
- *(cleanup)* Fix cache keys and other minor cleanups
- *(release)* Don't echo the multiline changelog string

## [0.11.0](https://github.com/s0undt3ch/refine/releases/tag/0.11.0) - 2025-04-04

### 🚀 Features

- Improve codemod CLI handling
- *(dependencies)* Add `py-walk` as a dependency
- *(codemods)* Allow configuring `exclude` for each codemod
- *(testing)* Allow `assert_codemod` to also validate equality
- *(gitignore)* Allow respecting `.gitignore` when excluding collected files

### 🐛 Bug Fixes

- Fix logical check variable
- Make sure custom codemod paths are importable
- *(cli)* Fix help message about default config file
- *(entry-points)* Don't blowup when failing to load an entry-point
- *(project name)* Fixed references to the old project names

## [0.10.2](https://github.com/s0undt3ch/refine/releases/tag/0.10.2) - 2025-03-31

### 📚 Documentation

- Provide a full URL to the logo so it shows on PyPi

## [0.10.1](https://github.com/s0undt3ch/refine/releases/tag/0.10.1) - 2025-03-31

### 📚 Documentation

- Bring focus to the project message
- Generate the reference docs
- *(release)* Update changelog

### ⚙️ Miscellaneous Tasks

- *(pre-commit)* Make sure we don't commit a `uv.lock` file not up to date

## [0.10.0](https://github.com/s0undt3ch/refine/releases/tag/0.10.0) - 2025-03-31

### 🚀 Features

- *(release)* Rename package to avoid conflicts on PyPi

### 📚 Documentation

- Bring focus to the project message
- Generate the reference docs

### ⚙️ Miscellaneous Tasks

- *(pre-commit)* Make sure we don't commit a `uv.lock` file not up to date

## [0.9.2](https://github.com/s0undt3ch/refine/releases/tag/0.9.2) - 2025-03-31

### 💼 Other

- Update changelog for release

### ⚙️ Miscellaneous Tasks

- Address mypy complaints, again.
- *(release)* Fix dynamic release version support
- *(release)* Switch to `hatch-vcs` for the dynamic version support

## [0.9.1](https://github.com/s0undt3ch/refine/releases/tag/0.9.1) - 2025-03-30

### 🚀 Features

- Implement `get_short_description` classmethod
- Fail if no codemods are selected

### ⚙️ Miscellaneous Tasks

- Quiet down mypy
- *(release)* Add changelog file

## [0.9.0](https://github.com/s0undt3ch/refine/releases/tag/0.9.0) - 2025-03-25

### 🚀 Features

- First Release!

<!-- generated by git-cliff -->
