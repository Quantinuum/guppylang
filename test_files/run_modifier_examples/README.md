# Running modifier examples

This directory contains the helper script for regenerating and running the
modifier examples in `test_files/modifier_examples/`.

## Workflow

Each modifier example is a Python file in `test_files/modifier_examples/`.
When run, the example compiles its Guppy program and writes a `.hugr` file with
the same stem in that directory.

`run_examples.py` performs three steps:

1. Run each selected example Python file to regenerate its `.hugr` file.
2. Load the generated `.hugr` and apply `tket.passes.ModifierResolverPass`.
3. Run the resolved package with `guppylang.emulator.EmulatorBuilder` and write
   a readable statevector summary to `hugr_results.txt`.

The modifier resolver is applied in memory by the runner. It does not write a
separate resolved HUGR file.

## Commands

From the repository root:

```sh
just recompile-modifiers
just recompile-modifier assign_in_dagger
```

From this directory:

```sh
just run-hugrs
just rh assign_in_dagger
just run-existing
```

`run-existing` skips the Python recompilation step and runs the existing `.hugr`
files from `test_files/modifier_examples/`.

The script can also be called directly:

```sh
uv run python run_examples.py
uv run python run_examples.py assign_in_dagger
uv run python run_examples.py --skip-compile
uv run python run_examples.py --n-qubits 12
```

Example names may be passed with or without the `.py` suffix.
