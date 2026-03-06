# (Proposal) Automatic discovery of Hugr packages in installed distributions

This proposal concerns how Hugr packages are distributed and discovered.
At a high level, Hugr packages should be distributed as part of Python wheels, and discovered by Guppy at runtime
without the need for manual configuration or other custom user code.

The proposal is to leverage the
Python [entry points mechanism](https://packaging.python.org/en/latest/specifications/entry-points/) for this (as one of
the common drivers behind
[plugin discovery](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-package-metadata)
in Python). Library authors can define an entry point in the group `guppylang.hugr` in their `pyproject.toml`, and
specify a loader function that returns a list of paths to Hugr packages to be loaded.

For example, assuming the library was compiled to a `library.hugr` binary file, a library author may include the
following in a top-level `loader.py` inside their distribution:

```python
from pathlib import Path


def load_hugrs() -> list[Path]:
    return [Path(__file__).parent / "library.hugr"]
```

Additionally, they would include the `library.hugr` file, and the following configuration in the `pyproject.toml` of
their distribution (e.g. `super-guppy-hugr`):

```toml
[project]
name = "super-guppy-hugr"
version = "0.1.0"
description = "HUGR distribution for {self.metadata.name}"

[project.entry-points."guppylang.hugr"]
hugr_loader = "loader:load_hugrs"
```

```{note}
Hugr packages may also be included in stub distributions, and discovered in the same way by including the loader and
the entry point configuration. They do not have to be separate distributions.
```

`guppylang` can now auto-discover Hugr packages by looking for entry points in the `guppylang.hugr` group, and calling
the corresponding loader. An example implementation of this discovery mechanism may look like the following:

```python
from pathlib import Path
from importlib.metadata import entry_points


def discover_hugr_packages() -> list[Path]:
    eps = entry_points(group='guppylang.hugr')
    hugr_packages = []
    for ep in eps:
        # Can use `ep.dist.name` to get the distribution name, if needed for logging, debugging, or filtering.
        loader_func = ep.load()
        hugr_packages.extend(loader_func())

    return hugr_packages
```

Finally, consumers of the library would simply install the `super-guppy-hugr` distribution, and call the discovery
function before executing their Hugr code, to ensure that the library Hugr package is linked in:

```python
from guppylang.library import discover_hugr_packages

main = ...  # Define some consuming entry point

main.emulator(n_qubits=..., libraries=discover_hugr_packages()).with_shots(100).run()
```

Optionally, omission of `libraries` may lead to internal calls to automatic discovery, and other means of configuring
the used Hugr packages may be provided as well (e.g. environment variables, or a configuration file).

## Open questions

- How does a user sort out which Hugr packages to use with multiple Hugr packages for the same stubs installed?
  It is unclear how this case can be discovered (e.g. for a nice error message if they do not choose).
