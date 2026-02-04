# Changelog

First release of `guppylang_internals` package containing refactored out internal components
from `guppylang`.

## [0.28.0](https://github.com/Quantinuum/guppylang/compare/guppylang-internals-v0.27.0...guppylang-internals-v0.28.0) (2026-02-04)


### ⚠ BREAKING CHANGES

* Tket is now a non-optional dependency. Most systems already have this installed, rerunning the package manager should fix any issues.

### Features

* Label `FuncDefn`s with qualified names in HUGR ([#1452](https://github.com/Quantinuum/guppylang/issues/1452)) ([a92f274](https://github.com/Quantinuum/guppylang/commit/a92f274a14668b7ac88713a69a6902aca62d4483))
* Make tket a non-optional dependency ([#1440](https://github.com/Quantinuum/guppylang/issues/1440)) ([4af4360](https://github.com/Quantinuum/guppylang/commit/4af4360495c9d6155e69310d5bfb8f22953fc1ff))
* use hugr used_extensions in engine.py ([#1451](https://github.com/Quantinuum/guppylang/issues/1451)) ([c16b96b](https://github.com/Quantinuum/guppylang/commit/c16b96bd5dc6ab4df13e3242ffe55279b317dd7e))


### Bug Fixes

* Add a copy before fallable `synthesize_call` call  ([#1460](https://github.com/Quantinuum/guppylang/issues/1460)) ([84137c3](https://github.com/Quantinuum/guppylang/commit/84137c39b7e8ca24142ffe73afcce6a1bcceffe2))
* Raise type inference error when not all function argument types could be resolved. ([#1439](https://github.com/Quantinuum/guppylang/issues/1439)) ([4120d59](https://github.com/Quantinuum/guppylang/commit/4120d590917245258d69ceb07c763c7633c7c5f8)), closes [#1437](https://github.com/Quantinuum/guppylang/issues/1437)
* Remove leading tab characters from diagnostics during rendering ([#1447](https://github.com/Quantinuum/guppylang/issues/1447)) ([a1cf792](https://github.com/Quantinuum/guppylang/commit/a1cf792deaf90e31721505ac17fd4911737e6c26)), closes [#1101](https://github.com/Quantinuum/guppylang/issues/1101)
* Support comptime expressions in subscript assignments ([#1433](https://github.com/Quantinuum/guppylang/issues/1433)) ([108c104](https://github.com/Quantinuum/guppylang/commit/108c104d55ecb052d4d7c363062f444efc689724)), closes [#1363](https://github.com/Quantinuum/guppylang/issues/1363)
* Support more cases of comptime subscripts ([#1436](https://github.com/Quantinuum/guppylang/issues/1436)) ([9aefdcc](https://github.com/Quantinuum/guppylang/commit/9aefdcc50b142acf842cf60314b5bccc49e01614)), closes [#1435](https://github.com/Quantinuum/guppylang/issues/1435)

## [0.27.0](https://github.com/Quantinuum/guppylang/compare/guppylang-internals-v0.26.0...guppylang-internals-v0.27.0) (2026-01-08)


### ⚠ BREAKING CHANGES

* The first argument to `add_unitarity_metadata` is now named `node`
instead of `func`, since its type was raised to allow for more HUGR
nodes to be fed. Migration is trivial. 
* `DiagnosticsRenderer.PREFIX_CONTEXT_LINES` constant has been removed.

### Features

* Add qubit hints on Guppy functions, allowing elision when building emulators ([#1378](https://github.com/Quantinuum/guppylang/issues/1378)) ([b7f10c6](https://github.com/Quantinuum/guppylang/commit/b7f10c6798aa20841fae844084d8a1606661fd7b)), closes [#1297](https://github.com/Quantinuum/guppylang/issues/1297)
* Add unsafe array take and put operations ([#1165](https://github.com/Quantinuum/guppylang/issues/1165)) ([7f342e7](https://github.com/Quantinuum/guppylang/commit/7f342e788e2f179382bab46dcc7e69a24dd64de3))
* **internals:** update to hugr-py 0.15 ([#1418](https://github.com/Quantinuum/guppylang/issues/1418)) ([cf970ba](https://github.com/Quantinuum/guppylang/commit/cf970ba7403a126fbd5d2fd53445e65270581df4))


### Bug Fixes

* Add a line break for printing WASM files ([#1386](https://github.com/Quantinuum/guppylang/issues/1386)) ([495aba5](https://github.com/Quantinuum/guppylang/commit/495aba5b9bb2218224193c7b2da2c5586744505a))
* added deepcopy in `OverloadedFunctionDef.{check_call,synthesize_call}` ([#1426](https://github.com/Quantinuum/guppylang/issues/1426)) ([9be6fef](https://github.com/Quantinuum/guppylang/commit/9be6fefcdfb9fc9eb1025774d2dd2727b3e719b1))
* **checker:** handle imported ParamDef with aliases in expr_checker ([#1385](https://github.com/Quantinuum/guppylang/issues/1385)) ([f2838a3](https://github.com/Quantinuum/guppylang/commit/f2838a34a315599c5b46eae92b72e9758e428a16))
* Convert symbolic pytket circuits angle inputs into rotations ([#1425](https://github.com/Quantinuum/guppylang/issues/1425)) ([4724d90](https://github.com/Quantinuum/guppylang/commit/4724d9039d8dffae8fd939f62ae80ec307d8918a))
* Ensure errors from `[@wasm](https://github.com/wasm)_module` are rendered correctly ([#1398](https://github.com/Quantinuum/guppylang/issues/1398)) ([a6a539f](https://github.com/Quantinuum/guppylang/commit/a6a539fe07cc94f4a788fef506969e4c9027faee)), closes [#1397](https://github.com/Quantinuum/guppylang/issues/1397)
* Fix another wasm diagnostics rendering issue ([#1399](https://github.com/Quantinuum/guppylang/issues/1399)) ([6604175](https://github.com/Quantinuum/guppylang/commit/660417542f2b36c387e73765f8647c11cd3d1a7b))
* Fix Hugr generation for tuples in `Result` and `Either` ([#1395](https://github.com/Quantinuum/guppylang/issues/1395)) ([f8b0d47](https://github.com/Quantinuum/guppylang/commit/f8b0d47eb275aae3f5ba804dfeb3640c4a3baef6)), closes [#1388](https://github.com/Quantinuum/guppylang/issues/1388)
* improve diagnostics rendering ([#1382](https://github.com/Quantinuum/guppylang/issues/1382)) ([e7ce7f6](https://github.com/Quantinuum/guppylang/commit/e7ce7f6d1a4f2b12ff680a6e54dae96637c5fa92))
* Stop parsing entrypoints twice ([#1410](https://github.com/Quantinuum/guppylang/issues/1410)) ([4a167e5](https://github.com/Quantinuum/guppylang/commit/4a167e5642cedc8f47ad027ed08483caa1558830))
* Support comptime expressions in generic argument applications ([#1409](https://github.com/Quantinuum/guppylang/issues/1409)) ([c1aad34](https://github.com/Quantinuum/guppylang/commit/c1aad346adb15e3636e5586987422d74e36189a1)), closes [#1087](https://github.com/Quantinuum/guppylang/issues/1087)

## [0.26.0](https://github.com/Quantinuum/guppylang/compare/guppylang-internals-v0.25.0...guppylang-internals-v0.26.0) (2025-12-11)


### ⚠ BREAKING CHANGES

* `FunctionType` constructor no longer accepts the `input_names` argument. Instead, input names should be provided as an optional argument to `FuncInput`
* Removed `guppylang_internals.nodes.ResultExpr` Moved `guppylang_internals.std._internal.checker.{TAG_MAX_LEN, TooLongError}` to `guppylang_internals.std._internal.compiler.platform`
* 
* The `tag` field of `guppylang_internals.nodes.{ResultExpr, StateResultExpr}` has been replaced with a const `tag_value` and a `tag_expr` expression
* `guppylang_internals.tys.ty.SumType` has been removed
* 
* `modifier_checker.check_modified_block_signature` now requires the `ModifiedBlock` as first argument

### Features

* Allow dynamic tag and signal in `panic`/`exit` ([#1327](https://github.com/Quantinuum/guppylang/issues/1327)) ([bae0da1](https://github.com/Quantinuum/guppylang/commit/bae0da1d42eea88d34c5c7bdd3d7f8a2504f1501))
* Unitarity annotations for functions ([#1292](https://github.com/Quantinuum/guppylang/issues/1292)) ([54dc200](https://github.com/Quantinuum/guppylang/commit/54dc200de881d065d3ee92bdc9a8ca076990d412))
* Validate signatures against wasm file ([#1339](https://github.com/Quantinuum/guppylang/issues/1339)) ([e57059b](https://github.com/Quantinuum/guppylang/commit/e57059b0ed61e6d76492e52d2a6f8c83f421e46b))


### Bug Fixes

* Allow comptime string arguments as result tags ([#1354](https://github.com/Quantinuum/guppylang/issues/1354)) ([cdc5c68](https://github.com/Quantinuum/guppylang/commit/cdc5c680879ae160bb592212cc8ed2fe6fc9ddbe))
* Fix calls with comptime args inside comptime functions ([#1360](https://github.com/Quantinuum/guppylang/issues/1360)) ([8321303](https://github.com/Quantinuum/guppylang/commit/83213034a3c74e158bb58bbd1ff34ab7d253d981)), closes [#1359](https://github.com/Quantinuum/guppylang/issues/1359)
* Fix internal compiler error when returning generic functions as values in comptime ([#1337](https://github.com/Quantinuum/guppylang/issues/1337)) ([8e2eba7](https://github.com/Quantinuum/guppylang/commit/8e2eba7e75e965405a903308b237344b83a3b168)), closes [#1335](https://github.com/Quantinuum/guppylang/issues/1335)
* Handle subscript borrows involving index coercions ([#1358](https://github.com/Quantinuum/guppylang/issues/1358)) ([aee0dd8](https://github.com/Quantinuum/guppylang/commit/aee0dd8b34932b6badef6b9336a7f350e241815b)), closes [#1356](https://github.com/Quantinuum/guppylang/issues/1356)


### Miscellaneous Chores

* Remove `SumType` ([#1345](https://github.com/Quantinuum/guppylang/issues/1345)) ([b914dfe](https://github.com/Quantinuum/guppylang/commit/b914dfe374a6d7c2a4fe9f95d4f6e8f2ac0675e7))


### Code Refactoring

* Implement `result` using overloads instead of a custom node ([#1361](https://github.com/Quantinuum/guppylang/issues/1361)) ([1da2c5d](https://github.com/Quantinuum/guppylang/commit/1da2c5dbb82bf6da35949b505a69f4e2f51acd3b))
* Store function argument names in `FuncInput` ([#1286](https://github.com/Quantinuum/guppylang/issues/1286)) ([b701840](https://github.com/Quantinuum/guppylang/commit/b70184098a65cde48c82da89ccbb4e50d1750f1d))

## [0.25.0](https://github.com/quantinuum/guppylang/compare/guppylang-internals-v0.24.0...guppylang-internals-v0.25.0) (2025-10-28)


### ⚠ BREAKING CHANGES

* (guppy-internals) Arrays are now lowered to `borrow_array`s instead of `value_array`s so elements do no longer need to be wrapped in options during lowering.
* `checker.core.requires_monomorphization` renamed into `require_monomorphization` and now operating on all parameters simultaneously `tys.subst.BoundVarFinder` removed. Instead, use the new `bound_vars` property on types, arguments, and consts. `tys.parsing.parse_parameter` now requires a `param_var_mapping`.

### Features

* compiler for modifiers ([#1287](https://github.com/quantinuum/guppylang/issues/1287)) ([439ff1a](https://github.com/quantinuum/guppylang/commit/439ff1ae6bd872bb7a6eb5441110d2febebd1e47))
* modifiers in CFG and its type checker (experimental) ([#1281](https://github.com/quantinuum/guppylang/issues/1281)) ([fe85018](https://github.com/quantinuum/guppylang/commit/fe8501854507c3c43cec2f26bba75198766a4a17))
* Turn type parameters into dependent telescopes ([#1154](https://github.com/quantinuum/guppylang/issues/1154)) ([b56e056](https://github.com/quantinuum/guppylang/commit/b56e056a6b4795c778ed8124a09a194fb1d97dda))
* update hugr, tket-exts and tket ([#1305](https://github.com/quantinuum/guppylang/issues/1305)) ([6990d85](https://github.com/quantinuum/guppylang/commit/6990d850170e6901f60ef1d1e718c99349105b56))
* Use `borrow_array` instead of `value_array` for array lowering ([#1166](https://github.com/quantinuum/guppylang/issues/1166)) ([f9ef42b](https://github.com/quantinuum/guppylang/commit/f9ef42b2baf61c3e1c2cfcf7bd1f3bcac33a1a25))


### Bug Fixes

* compilation of affine-bounded type variables ([#1308](https://github.com/quantinuum/guppylang/issues/1308)) ([49ecb49](https://github.com/quantinuum/guppylang/commit/49ecb497bf450d0853baec1de9c516a3804a80eb))
* Detect unsolved generic parameters even if they are unused ([#1279](https://github.com/quantinuum/guppylang/issues/1279)) ([f830db0](https://github.com/quantinuum/guppylang/commit/f830db00c416cfc1e9fe7ec70c612b6b558aa740)), closes [#1273](https://github.com/quantinuum/guppylang/issues/1273)
* Fix bug in symbolic pytket circuit loading with arrays ([#1302](https://github.com/quantinuum/guppylang/issues/1302)) ([e6b90e8](https://github.com/quantinuum/guppylang/commit/e6b90e8e4d275d36514a75e87eb097383495a291)), closes [#1298](https://github.com/quantinuum/guppylang/issues/1298)
* Improve track_hugr_side_effects, adding Order edges from/to Input/Output ([#1311](https://github.com/quantinuum/guppylang/issues/1311)) ([3c6ce7a](https://github.com/quantinuum/guppylang/commit/3c6ce7aaf7a1c93c6412501976fc97afd61a062d))
* multiline loop arguments  ([#1309](https://github.com/quantinuum/guppylang/issues/1309)) ([836ef72](https://github.com/quantinuum/guppylang/commit/836ef722d8f8bdb02c56e5f06934246a718e68d3))

## [0.24.0](https://github.com/quantinuum/guppylang/compare/guppylang-internals-v0.23.0...guppylang-internals-v0.24.0) (2025-09-19)


### ⚠ BREAKING CHANGES

* `guppylang_internals.decorator.extend_type` now returns a `GuppyDefinition` by default. To get the previous behaviour of returning the annotated class unchanged, pass `return_class=True`.
* `TypeDef`s now require a `params` field
* guppylang_internals.ty.parsing.parse_function_io_types replaced with parse_function_arg_annotation and check_function_arg
* Significant changes to the WASM decorators, types and operations
* Deleted `guppylang_internals.nodes.{IterHasNext, IterEnd}`
* guppylang_internals.tracing.unpacking.update_packed_value now returns a bool signalling whether the operation was successful.
* `CompilationEngine` now initialises all it's fields
* Calling `CompilationEngine.reset` no longer nullifies `additional_extensions`
* `CompilationEngine.register_extension` no longer adds duplicates to the `additional_extensions` list

### Features

* Infer type of `self` arguments ([#1192](https://github.com/quantinuum/guppylang/issues/1192)) ([51f5a2b](https://github.com/quantinuum/guppylang/commit/51f5a2b3a9b06bc4ab054f32a4d07f7395df8ff4))


### Bug Fixes

* Add init to CompilationEngine; don't trash additional_extensions ([#1256](https://github.com/quantinuum/guppylang/issues/1256)) ([e413748](https://github.com/quantinuum/guppylang/commit/e413748532db3895cab4925a222177a4fa3fd61b))
* Allow generic specialization of methods ([#1206](https://github.com/quantinuum/guppylang/issues/1206)) ([93936cc](https://github.com/quantinuum/guppylang/commit/93936cc275c56dd856d11fabc7aac20176304147)), closes [#1182](https://github.com/quantinuum/guppylang/issues/1182)
* Correctly update borrowed values after calls and catch cases where it's impossible ([#1253](https://github.com/quantinuum/guppylang/issues/1253)) ([3ec5462](https://github.com/quantinuum/guppylang/commit/3ec54627729b49689da006a743e9e2c359cd3728))
* Fix `nat` constructor in comptime functions ([#1258](https://github.com/quantinuum/guppylang/issues/1258)) ([e257b6f](https://github.com/quantinuum/guppylang/commit/e257b6fc2fe3793d6d8f63feca83bf5ed6643673))
* Fix incorrect leak error for borrowing functions in comptime ([#1252](https://github.com/quantinuum/guppylang/issues/1252)) ([855244e](https://github.com/quantinuum/guppylang/commit/855244e2d5e3aeb04c2028f9f2310dba0e74210a)), closes [#1249](https://github.com/quantinuum/guppylang/issues/1249)
* wasm module updates based on tested lowering ([#1230](https://github.com/quantinuum/guppylang/issues/1230)) ([657cea2](https://github.com/quantinuum/guppylang/commit/657cea27af00a9c02e8d1a3190db535bbd1e7981))


### Miscellaneous Chores

* Delete unused old iterator AST nodes ([#1215](https://github.com/quantinuum/guppylang/issues/1215)) ([2310897](https://github.com/quantinuum/guppylang/commit/231089750e33cf70754e5218feed64053c558c17))

## [0.23.0](https://github.com/quantinuum/guppylang/compare/guppylang-internals-v0.22.0...guppylang-internals-v0.23.0) (2025-08-19)


### ⚠ BREAKING CHANGES

* `check_rows_match` no longer takes `globals` Deleted `GlobalShadowError` and `BranchTypeError.GlobalHint`

### Bug Fixes

* Fix globals vs locals scoping behaviour to match Python ([#1169](https://github.com/quantinuum/guppylang/issues/1169)) ([a6a91ca](https://github.com/quantinuum/guppylang/commit/a6a91ca32ad7c67bf1d733eb26c016a2662256ef))
* Fix scoping issues with comprehensions in comptime expressions ([#1218](https://github.com/quantinuum/guppylang/issues/1218)) ([0b990e2](https://github.com/quantinuum/guppylang/commit/0b990e2b006c31352675004aec63a857f03a0793))


### Documentation

* use results sequence protocol for simplicity ([#1208](https://github.com/quantinuum/guppylang/issues/1208)) ([f9c1aee](https://github.com/quantinuum/guppylang/commit/f9c1aee38776c678660ede5495989ac4d75baaeb))

## [0.22.0](https://github.com/quantinuum/guppylang/compare/guppylang-internals-v0.21.2...guppylang-internals-v0.22.0) (2025-08-11)


### ⚠ BREAKING CHANGES

* RangeChecker has been deleted.

### Features

* Add float parameter inputs to symbolic pytket circuits ([#1105](https://github.com/quantinuum/guppylang/issues/1105)) ([34c546c](https://github.com/quantinuum/guppylang/commit/34c546c3b5787beb839687fdbf4db8bc94f36c4a)), closes [#1076](https://github.com/quantinuum/guppylang/issues/1076)
* Allow custom start and step in `range` ([#1157](https://github.com/quantinuum/guppylang/issues/1157)) ([a1b9333](https://github.com/quantinuum/guppylang/commit/a1b9333712c74270d5efaaa72f83d6b09047c068))
* Improve codegen for array unpacking ([#1106](https://github.com/quantinuum/guppylang/issues/1106)) ([f375097](https://github.com/quantinuum/guppylang/commit/f3750973a719b03d27668a3ae39f58c8424deffc))
* Insert drop ops for affine values ([#1090](https://github.com/quantinuum/guppylang/issues/1090)) ([083133e](https://github.com/quantinuum/guppylang/commit/083133e809873fce265bb78547fc3e519cb66ea1))


### Bug Fixes

* Fix builtins mock escaping the tracing scope ([#1161](https://github.com/quantinuum/guppylang/issues/1161)) ([a27a5c1](https://github.com/quantinuum/guppylang/commit/a27a5c19560d76e46678f846476ea86e873ac8ac))

## [0.21.1](https://github.com/quantinuum/guppylang/compare/guppylang-internals-v0.21.0...guppylang-internals-v0.21.1) (2025-08-05)


### Bug Fixes

* **guppylang-internals:** Fix circular import for custom decorators ([#1146](https://github.com/quantinuum/guppylang/issues/1146)) ([d8474d8](https://github.com/quantinuum/guppylang/commit/d8474d8af3d394275268cd3d0754ff06ecb9bcc2)), closes [#1145](https://github.com/quantinuum/guppylang/issues/1145)
* Support `None` value ([#1149](https://github.com/quantinuum/guppylang/issues/1149)) ([7f606c7](https://github.com/quantinuum/guppylang/commit/7f606c778d98312a0d1c4a9c7a27448c24d80585)), closes [#1148](https://github.com/quantinuum/guppylang/issues/1148)


### Documentation

* Fix docs build ([#1142](https://github.com/quantinuum/guppylang/issues/1142)) ([4dfd575](https://github.com/quantinuum/guppylang/commit/4dfd575bcdfdf1e2db4e61f2f406fff27e0c08f7))

## [0.21.0](https://github.com/quantinuum/guppylang/compare/guppylang-internals-v0.20.0...guppylang-internals-v0.21.0) (2025-08-04)


### ⚠ BREAKING CHANGES

* All compiler-internal and non-userfacing functionality is moved into a new `guppylang_internals` package

### Code Refactoring

* Split up into `guppylang_internals` package ([#1126](https://github.com/quantinuum/guppylang/issues/1126)) ([81d50c0](https://github.com/quantinuum/guppylang/commit/81d50c0a24f55eca48d62e4b0275ef2126c5e626))
