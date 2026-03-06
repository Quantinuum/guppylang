# (Proposal) Easily referencing headers to implement

A new syntax, that allows function definitions to easily reference the declarations they are providing an implementation
for.
Signatures are validated similar to [the stub validation](./stubs.md).
The declarations link name and other keyword args should be largely copied onto the definition.
The main use case is not running risk of desyncing the link name when doing something like this.

```python
from guppylang import guppy
from some_lib import some_declaration


@guppy.impl(some_declaration)  # or @guppy.implements(...)
def my_implementation(...) -> ...:
    ...
```
