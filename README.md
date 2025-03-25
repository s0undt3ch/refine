<h1 align="center">
  <img width="240px" src="docs/imgs/recode.png" alt="recode"/>
</h1>

`recode` leverages the capabilities of [libCST](https://libcst.readthedocs.io/) (Library for Concrete Syntax Trees), a Python
library designed for parsing, manipulating, and generating Python code in a syntax-preserving way. It builds upon libCST's
[codemod](https://libcst.readthedocs.io/en/latest/codemods_tutorial.html) module, which provides utilities for transforming code
programmatically.

## Key Differentiators

### Chained Codemod Execution

`recode` enables running multiple `codemod`'s in a single CLI execution, streamlining workflows compared to libCST's one-codemod-per-execution approach.

### Priority Management

Codemods are applied in a predefined order based on priorities defined by the modules. This ensures automatic logical sequencing of transformations.

## Streamlined Features

### Single-Pass Efficiency

Chained execution minimizes redundant parsing and tree-building processes, improving efficiency for large-scale projects.

### Focus on Developer Productivity

By reducing the need for multiple executions, `recode` enhances developer workflows, especially in CI/CD pipelines or batch processing.
