# (Proposal) More ways to define a library / auto-collection

Currently, functions must be manually fed into `guppy.library(...)` to be included in the library. This proposal
concerns additional ways to define (members of) a library, and automatically collect functions to be included in it.

A potential addition would be a `@guppy(export=...)` argument, that registers the function to be included in *the*
library in some global Guppy store (like the `DEF_STORE`). A function could then be included simply by adding that
argument, e.g.:

```python
from guppylang import guppy


@guppy(export=True)
def included() -> None:
    ...


@guppy  # or @guppy(export=False) for explicit exclusion
def not_included() -> None:
    ...
```

This is similar to a `public` / `private` modifier, and indirectly determines the visibility of the function in the Hugr
package. It may be added to `@guppy.struct` and `@guppy.enum` as well, to include the functions on these constructs in
the library as public as well.

A call to `guppy.library` could then be simplified to an explicit opt-in to auto-collection:

```python
from guppylang import guppy

# ... the functions above ...

# Includes `included`, but not `not_included` as a public member.
library = guppy.library(auto_collect=True)
```

## Optional: Keys

In addition to supporting `True | False | None` for the `export` argument, it may be useful to support string keys as
well, to allow for more fine-grained control over the produced packages in which the function is included (concerning
both the visibility in the produced Hugr package and the stubs that are generated, e.g.
through [the stub proposal](stubs.md)).

For example, one may want to include certain (core) functions in all versions of the library, but specify certain sets
of functions to be included (akin to `extras` from Python packages):

```python
from guppylang import guppy


@guppy(export=True)
def included_in_all_libs() -> None:
    ...


@guppy(export='key1')
def included_when_key_1() -> None:
    ...


@guppy(export='key2')
def included_when_key_2() -> None:
    ...


@guppy(export='key3')
def included_when_key_3() -> None:
    ...
```

Auto-collection may then take a range of keys to include:

```python
from guppylang import guppy

# ... the functions above ...

# Includes all functions with export=True, export='key1', and export='key2', but not export='key3'
library = guppy.library(auto_collect=['key1', 'key2'])
```
