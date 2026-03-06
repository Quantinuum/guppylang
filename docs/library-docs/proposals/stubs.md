# (Proposal) Generating stubs automatically

One of the more arduous tasks of creating a library is writing the stubs for it.
This proposal aims to provide tooling to simplify this process and potentially fully automate it.
There are existing stub generators for Python (like [
`stubgen` from `mypy`](https://mypy.readthedocs.io/en/stable/stubgen.html), tooling from [
`pyright`](https://github.com/microsoft/pyright/blob/main/docs/type-stubs.md#generating-type-stubs-from-command-line),
and more), but these usually do not fit the needs of Guppy libraries, since we not only need to transform signatures,
but also make sure that we use `@guppy.declare` instead of `@guppy`. Link names should be explicitly specified in the
stubs, to make them independent of changes in the default link name inference mechanisms.

These stub generators are often meant to provide a start for writing stubs for the library, but often require manual
labor to clean, fix, and clarify generated code.

```{note}
Nonetheless, it might be worthwhile testing existing stub generators on real-world examples for Guppy libraries. Perhaps
the only thing we need to worry about is the decorator transformation after all.
```

Difficulties surrounding stub generation include:

- Types mentioned in signatures may come from imports (which you want to preserve, since importing from their
  implementing module may reveal implementation details), or be defined locally, in which case you need to include them
  in the stubs as well.
- Pythonic public re-exports should be preserved / made available in the stubs
- When depending on types provided from imports (i.e. defined in other files), these types need to be included in the
  stubs for that other file
- Structs and enums need to be included in the stubs as well, with their methods as stubbed functions

## Validation

When writing stubs (especially those generated automatically), it is important to be able to validate that a stub
faithfully represents the definition it corresponds to (or rather, that the definition can be substituted for the stub
without violating the [Liskov substitution principle](https://en.wikipedia.org/wiki/Liskov_substitution_principle)).
Checking may be optionally (i.e. via a flag) strengthened to require equality rather than a subtyping relationship, to
effectively check that:

1. A definition can replace the stub without violating LSP, *and*
2. The stub is the most specific signature that can be used for the definition

This can be extended to take two arbitrary function signatures (with accompanying flags, i.e. from
`@guppy(unitary=True)`), and subsequently check LSP on them.

Such a validation mechanism would be useful for the following use cases:

1. Verifying (automatically, and fit for use in CI) that a definition did not observably break against the stub it
   corresponds to (at least with the typed contract, written contracts cannot be checked).
2. Verifying (mainly for our test cases) that the automatically generated stubs work as intended, and one did not
   discover a new edge case where they do not.
3. Probably more.
