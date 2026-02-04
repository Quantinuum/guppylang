# Guppy

[![pypi][]](https://pypi.org/project/guppylang/)
[![codecov][]](https://codecov.io/gh/quantinuum/guppylang)
[![py-version][]](https://pypi.org/project/guppylang/)

  [codecov]: https://img.shields.io/codecov/c/gh/quantinuum/guppylang?logo=codecov
  [py-version]: https://img.shields.io/pypi/pyversions/guppylang
  [pypi]: https://img.shields.io/pypi/v/guppylang

Guppy is a quantum programming language that is fully embedded into Python.
It allows you to write high-level hybrid quantum programs with classical control flow and mid-circuit measurements using Pythonic syntax:

```python
from guppylang import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import cx, h, measure, qubit, x, z


@guppy
def teleport(src: qubit @ owned, tgt: qubit) -> None:
    """Teleports the state in `src` to `tgt`."""
    # Create ancilla and entangle it with src and tgt
    tmp = qubit()
    h(tmp)
    cx(tmp, tgt)
    cx(src, tmp)

    # Apply classical corrections
    h(src)
    if measure(src):
        z(tgt)
    if measure(tmp):
        x(tgt)

teleport.check()
```

More examples and tutorials are available [here][examples].

[examples]: https://github.com/quantinuum/guppylang/tree/main/examples

## Install

Guppy can be installed via `pip`. Requires Python >= 3.10.

```sh
pip install guppylang
```

## Development

See [DEVELOPMENT.md] information on how to develop and contribute to this package.

  [DEVELOPMENT.md]: https://github.com/quantinuum/guppylang/blob/main/DEVELOPMENT.md

## License

This project is licensed under Apache License, Version 2.0 ([LICENCE][] or <http://www.apache.org/licenses/LICENSE-2.0>).

  [LICENCE]: ./LICENCE
