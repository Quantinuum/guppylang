
# AGENTS.md

## Compiling Guppy functions
- Always compile a `@guppy`-decorated function before inspecting or serializing it — never access HUGR directly from the function object.
- Use `f.compile_function()` for functions with parameters; use `f.compile()` for functions with no parameters. Do not interchange them.
- To get the HUGR as a JSON string, call `program.to_str()` on the compiled result, not on the function itself.

## Validating a compiled HUGR
- Use `check_hugr` from `selene_hugr_qis_compiler` to verify a compiled HUGR is valid.
- `check_hugr` takes the byte encoding of a `Package` — call `package.to_bytes()` to get it.
- If you have a `PackagePointer`, unwrap it first: `package = package.package`.
- If you have a `Hugr`, wrap it: `package = Package([hugr])`.
- Minimal validation pattern:
  ```python
  from hugr import Hugr
  from hugr.package import Package, PackagePointer
  from selene_hugr_qis_compiler import check_hugr

  if isinstance(package, PackagePointer):
      package = package.package
  if isinstance(package, Hugr):
      package = Package([package])
  check_hugr(package.to_bytes())
  ```
