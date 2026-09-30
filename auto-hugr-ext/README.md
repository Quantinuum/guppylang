# auto-hugr-ext

Declare extension types and operations in a Python file with `@ext_type` and `@ext_op`, then generate the HUGR extension and its Guppy declarations:

```sh
uv run auto-hugr-ext gen path/to/declarations.py my.extension
```

The command writes `declarations.json` and `declarations_generated.py` beside the input. The generated module loads and registers the extension with Guppy's compiler. Import it from your program, or run it directly if it defines a `@guppy` `main()` that compiles:

```sh
uv run python path/to/declarations_generated.py
```

Use `@ext_type(copyable=..., droppable=...)` on opaque type classes and `@ext_op` on operation declarations; `@ext_op(override_name="...")` sets the HUGR operation name. PEP 695 type parameters support Guppy bounds such as `T: Copy` and `T: Drop`. Use Guppy's `@ owned` annotation for consumed inputs, for example `self: "Self" @ owned`.

Keep the JSON beside the generated Python file. Regenerate both after changing declarations. The input file is imported during generation, so it must be valid, importable Python; operation bodies are declarations, not implementations.
