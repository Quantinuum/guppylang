# Overview

## Defining a library

A Guppy library is, at its simplest, a collection of functions that are compiled together into a Hugr package.
In contrast to the usual executable Hugr packages (like those produced from compiling single entrypoint functions), such
library Hugr packages feature (usually multiple) *public* functions, possibly with arguments and non-``None`` return
types.

A developer may define a bunch of functions beyond this collection, for example for internally sharing functionality
between the public functions. Furthermore, developers may want to create different libraries / Hugr packages from a
single codebase, requiring to export different public functions in each such library.
In Guppy, a library is defined by calling the ``guppy.library(...)`` function, passing the functions to be exported as
public.
Any functions reachable via those functions are still included in the Hugr package, but with private visibility.

For example, a library may be defined as follows:

```python
from guppylang import guppy


@guppy
def my_func() -> None:
    pass


@guppy
def another_func(x: int) -> None:
    pass


@guppy
def a_third_func(x: int) -> int:
    return x + 1


# Creates the library object, but does not compile it
library = guppy.library(
    my_func,
    another_func,
    a_third_func,
)
```

The following are not yet supported:

- Exporting generic functions of any kind (see the [proposal](proposals/generic.md))
- Automatically collecting functions to be included in a library (see the [proposal](proposals/collection.md))

## Compiling a library and creating stubs

Once a library object is created, it can be compiled into a Hugr package, which can be distributed and used
independently of the source code:

```python
from guppylang import guppy
from hugr.package import Package

library = guppy.library(...)  # As above

# Hugr package contains any specified functions as public, and otherwise reachable functions as private
hugr_package: Package = library.compile()
with open("library.hugr", "wb") as f:
    f.write(hugr_package.to_bytes())
```

However, this Hugr package does not expose an interface that can be programmed against by consumers of the library *in
Guppy*. For this, the library author must define *stubs* for all exposed functions, utilising `@guppy.declare(...)`
decorators.

For the example above, this would look like:

```python
from guppylang import guppy


@guppy.declare
def my_func() -> None: ...


@guppy.declare
def another_func(x: int) -> None: ...


@guppy.declare
def a_third_func(x: int) -> int: ...
```

Creation of these stubs is a manual process; it is currently not possible to automatically generate stubs for a
library or validate that definitions faithfully implement their corresponding stubs (see the
[proposal](proposals/stubs.md) for both). Furthermore, it is currently not possible to define the stubs, and
subsequently reference the stubs in the library function definitions for easier consistency checks (see the
[proposal](proposals/impls.md) for that).

Finally, these stubs (in `*.pyi` files) should be distributed using regular Python packaging mechanisms, so that users
of the library can install and program against them. This distribution may or may not contain the Hugr package as well.

## Using a library

Let's call the library in the example above `super_guppy`.
That is, the library author has published a distribution containing the stubs above, to be imported `from super_guppy`.
A consumer of the library has installed that distribution using their favourite package manager (either from an index,
or by downloading the stub repository).

The consumer may now program against the API as follows:

```python
from guppylang import guppy
from guppylang.std.builtins import result
from super_guppy import my_func, a_third_func


@guppy
def consumer_func() -> None:
    my_func()
    result("library_call", a_third_func(5))


@guppy
def main() -> None:
    consumer_func()
```

In this case, the consumer aims to create an executable Hugr package (e.g. by calling `main.compile()` and creating a
package with a single, argument-less entrypoint). However, the created Hugr package is incomplete: It lacks the function
bodies of the library functions, and thus cannot be executed.

Thus, `hugr-py` MUST provide means to link the library Hugr package into the consumer Hugr package. For convenience, the
library Hugr package may be provided to the consumer program executor, so that it can be automatically linked in before
lowering to QIR. For example, using selene, this may look like:

```python
main.emulator(n_qubits=0, libraries=[hugr_package]).with_shots(100).run()
```

Currently, Hugr packages have to be manually downloaded / imported from whatever distribution mechanism the library
author chose. In the future, library authors may opt to distribute Hugr packages in Python wheels as well, and have
consuming code auto-collect these from the Python environment (see the [proposal](proposals/discovery.md) for this).

```{note}
A consumer of `super_guppy` may as well be another library author. Dependency of a library should be specified as usual
in Python requirements by depending on the header distributions (or through other common mechanisms).
```
