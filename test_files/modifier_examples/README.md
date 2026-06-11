# Modifier examples

This directory contains test guppy programs with modifier
operations (`dagger` and `control`). The examples are used for regression
testing of modifier compilation.

Each example is defined as a `.py` file that defines the Guppy program.
The compiled HUGR is stored alongside it with a `.hugr` extension.

## Generating and running

| Command | Where | Effect |
|---------|-------|--------|
| `just recompile-hugrs` | this directory | Recompile all `.hugr` files |
| `just recompile-modifiers` | repo root | Recompile all `.hugr` files and run them in the emulator |
| `just run-hugrs` | `test_files/run_modifier_examples/` | Recompile all `.hugr` files and run them in the emulator |

Each `.py` file writes its compiled HUGR to the matching `.hugr` file next to
it. The run commands then load those `.hugr` files, apply the tket modifier
resolver, run the resolved package with the Guppy emulator, and regenerate the
human-readable summary in `test_files/run_modifier_examples/hugr_results.txt`.

To recompile and run a single example, use `just recompile-modifier <example_name>`
from the repo root or `just rh <example_name>` in `test_files/run_modifier_examples/`.
