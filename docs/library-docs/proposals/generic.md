# (Proposal) Exporting generic functions

- Need to restrict / make finite the monomorphisations to be included in the library
- For private functions, this is easy: Just include all the variants that are used
- For public functions, usage is not yet clear (since they may be called arbitrarily)
- Thus, developer needs to specify which monomorphisations to *at least* include in the library, for example via

```python
from guppylang import guppy

T = guppy.type_var("T")


# Choice 1, includes at least the monomorphisations for int and float, and any privately required ones
@guppy.instances([{T: int}, {T: float}, ...])  # may be unpacked, as QOL for manual specification
def my_generic_func(x: T) -> T: ...


# Choice 2, different syntax, same effect
@guppy(instances=[{T: int}, {T: float}, ...])  # may be unpacked, as QOL for manual specification
def my_generic_func(x: T) -> T: ...
```

## Optional QOL features

- Allow to easily specify a range of types for each type variable, and form their product
    - This could perhaps be done via `itertools.product` or similar, but this has to be investigated
