# Configuration

`recode` can be configured at the root of your repository with a `.recode.toml` file or in your project's `pyproject.toml`.

All configuration options can seen on the [Config][recode.config.Config] class reference, but here are a few examples.

## Example `.recode.toml`

```toml
[recode]
select = [
    "sqlfmt",
]
exclude = [
    # Exclude only makes sense if no select is defined, since all available
    # codemods will be used, at which time we might want to exclude some.
    "sqlfmt",
]
codemod_paths = [
    ".codemods/"
]
process_pool_size = 2
```

## Example `pyproject.toml`

```toml
[tool.recode]
select = [
    "sqlfmt",
]
exclude = [
    # Exclude only makes sense if no select is defined, since all available
    # codemods will be used, at which time we might want to exclude some.
    "sqlfmt",
]
codemod_paths = [
    ".codemods/"
]
process_pool_size = 2
```
