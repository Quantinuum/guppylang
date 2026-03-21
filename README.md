![](https://raw.githubusercontent.com/quantinuum/guppylang/refs/heads/main/assets/guppy_logo.svg)

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

## Documentation

🌐 [Guppy website][website]

📖 [Language guide][guide]

📒 [Example notebooks][examples]

[examples]: ./examples/
[guide]: https://docs.quantinuum.com/guppy/language_guide/language_guide_index.html
[website]: https://guppylang.org

## Install

Guppy can be installed via `pip`. Requires Python >= 3.10.

```sh
pip install guppylang
```

## Development

See [DEVELOPMENT.md](https://github.com/quantinuum/guppylang/blob/main/DEVELOPMENT.md) for instructions on setting up the development environment.

## Attribution

If you use this software in your work, please cite with:
```
@misc{koch2025guppy,
  title = {{{GUPPY}}: {{Pythonic Quantum-Classical Programming}}},
  shorttitle = {{{GUPPY}}},
  author = {Koch, Mark and Lawrence, Alan and Singhal, Kartik and Sivarajah, Seyon and Duncan, Ross},
  year = 2025,
  month = oct,
  number = {arXiv:2510.12582},
  eprint = {2510.12582},
  primaryclass = {cs},
  publisher = {arXiv},
  doi = {10.48550/arXiv.2510.12582},
  archiveprefix = {arXiv}
}
```
or
```
M. Koch, A. Lawrence, K. Singhal, S. Seyon, and R. Duncan, GUPPY: Pythonic Quantum-Classical Programming (2025), arXiv:2510.12582.
```

## License

This project is licensed under Apache License, Version 2.0 ([LICENCE][] or <http://www.apache.org/licenses/LICENSE-2.0>).

  [LICENCE]: ./LICENCE
