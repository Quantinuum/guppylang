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

- Defining stubs to program against

Currently, a library does not support the following:

- Exporting generic functions of any kind (see [the proposal](proposals/generic.md))
- Automatically collecting functions to be included in a library (see [the proposal](proposals/collection.md))
- Automatically generating stubs for a library (see [the proposal](proposals/stubs.md))

## Compiling a library

- Compiling the library, and what to do with the Hugr package

## Using a library

- Programming and compiling against the headers
- Oh no, its not a runnable Hugr yet (but still a valid one)
- Providing the library Hugr package to the user program executor

    - This is the most open / underspecified part
    - Should be able to do this manually via ``hugr-py``
    - But also via simply passing more things to selene
    - Mention auto-discovery functions
