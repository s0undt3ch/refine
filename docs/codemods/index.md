# Codemods

Codemods are python modules which provide a subclass of [BaseCodemod][refine.abc.BaseCodemod], these classes
are resposible for the code modifications.

How to modify code can be read on [libCST's](https://libcst.readthedocs.io/en/latest/codemods_tutorial.html) documentation.
Do note that our [BaseCodemod][refine.abc.BaseCodemod] differs from the libCST implementation.
A good place to know how to implement a codemod can be see in this project's source tree under `src/refine/mods`.

# Included codemods

There are a few `codemod`'s included with the project, and issuing a `--list` on the `refine` CLI will show
you what's available.

```
Available codemods:
 - cli-dashes-over-underscores: Replace `_` with `-`, ie, `--a-command` instead of `--a_command` in CLI commands.
 - sqlfmt: Format SQL queries using the `sqlfluff` python package.
```

## Project Specific Codemods

Probably some of the `codemods` of a project are quite tailored to the project and not that broad that could be
contributed to the `refine` project.

In such cases, a project can host their own codemods in a directory and configure the [codemod_paths][refine.config.Config.codemod_paths]
configuration setting.

When properly configured, issuing `--list` will now include the project codemods.

## Testing codemods

We include [Modcase][refine.testing.Modcase] which is a dataclass prepared to test codemods from files which serve as
before and after examples, as long as a pattern is followed.

For example:
```python
from __future__ import annotations

import pathlib

import pytest

from refine.mods.sql.fmt import FormatSQL
from refine.mods.sql.fmt import FormatSQLConfig
from refine.testing import Modcase

FILES_PATH = pathlib.Path(__file__).parent.resolve() / "files" / "fmt"


def _get_case_id(case: Modcase) -> str:
    return case.name


def _get_cases() -> list[Modcase]:
    cases = []
    for path in FILES_PATH.glob("*.py"):
        if ".updated." in path.name:
            # We don't want to collect the .updated files
            continue
        cases.append(
            Modcase(
                path=path,
                codemod=FormatSQL,
                codemod_config=FormatSQLConfig(),
            )
        )
    return cases


@pytest.fixture(params=_get_cases(), ids=_get_case_id)
def fmt_case(request) -> Modcase:
    return request.param


def test_format_sql(fmt_case: Modcase):
    fmt_case.assert_codemod()
```

The above `FILES_PATH` contains examples of code changes that are being tested, here's an example directory listing:
```
Permissions Size User           Date Modified Name
.rw-r--r--@  287 pedro.algarvio 16 Nov 12:44   attribute-with-comment.py
.rw-r--r--@  307 pedro.algarvio 16 Nov 12:40   attribute-with-comment.updated.py
.rw-r--r--@  210 pedro.algarvio 22 Nov 12:34   bytestrings.py
.rw-r--r--@  202 pedro.algarvio 22 Nov 12:34   bytestrings.updated.py
.rw-r--r--@ 2.4k pedro.algarvio 24 Nov 21:06   case-when.py
.rw-r--r--@ 2.8k pedro.algarvio 24 Nov 21:06   case-when.updated.py
.rw-r--r--@  293 pedro.algarvio 10 Nov 19:53   funcall-with-comment.py
.rw-r--r--@  313 pedro.algarvio 10 Nov 19:52   funcall-with-comment.updated.py
.rw-r--r--@  140 pedro.algarvio 10 Nov 12:26   multiline-attribute.py
.rw-r--r--@  132 pedro.algarvio 10 Nov 12:21   multiline-attribute.updated.py
.rw-r--r--@   28 pedro.algarvio  9 Nov 12:50   oneline-attribute.py
.rw-r--r--@   28 pedro.algarvio  9 Nov 12:50   oneline-attribute.updated.py
.rw-r--r--@ 1.6k pedro.algarvio 24 Nov 21:06   weird-indentation-attr.py
.rw-r--r--@ 1.6k pedro.algarvio 24 Nov 21:06   weird-indentation-attr.updated.py
.rw-r--r--@ 1.3k pedro.algarvio 22 Nov 12:34   weird-indentation-call.py
.rw-r--r--@ 1.3k pedro.algarvio 22 Nov 12:34   weird-indentation-call.updated.py
```

To note that if a file before any codemods getting applied is called `a-file.py` then the updated file should be named `a-file.updated.py`.
