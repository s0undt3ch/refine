<h1 align="center">
  <img width="240px" src="https://raw.githubusercontent.com/s0undt3ch/refine/main/docs/imgs/refine.png" alt="refine"/>
</h1>

<h2 align="center">
  <em>Polishing and improving codebases automatically</em>
</h2>

`refine` leverages the capabilities of [libCST](https://libcst.readthedocs.io/) (Library for Concrete Syntax Trees), a Python
library designed for parsing, manipulating, and generating Python code in a syntax-preserving way. It builds upon libCST's
[codemod](https://libcst.readthedocs.io/en/latest/codemods_tutorial.html) module, which provides utilities for transforming code
programmatically.

## Key Differentiators

### Chained Codemod Execution

`refine` enables running multiple `codemod`'s in a single CLI execution, streamlining workflows compared to libCST's one-codemod-per-execution approach.

### Priority Management

Codemods are applied in a predefined order based on priorities defined by the modules. This ensures automatic logical sequencing of transformations.

## Streamlined Features

### Single-Pass Efficiency

Chained execution minimizes redundant parsing and tree-building processes, improving efficiency for large-scale projects.

### Focus on Developer Productivity

By reducing the need for multiple executions, `refine` enhances developer workflows, especially in CI/CD pipelines or batch processing.
