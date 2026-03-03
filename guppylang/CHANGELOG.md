---
file_format: mystnb
kernelspec:
  name: python3
---

# Changelog

The Guppy language is distributed via the [guppylang](https://pypi.org/project/guppylang/) pypi package.

This changelog documents user-facing changes to the Guppy language excluding changes to the compiler internals. The Guppy compiler is versioned with the [guppylang-internals](https://pypi.org/project/guppylang-internals/) package.

## Versioning Policy

As of August 2025, The Guppy language is undergoing rapid development and is currently unstable. There is a Guppy v1.0 stability [milestone](https://github.com/quantinuum/guppylang/milestone/12) that is a work in progress and subject to change.

## [0.21.9](https://github.com/Quantinuum/guppylang/compare/guppylang-v0.21.8...guppylang-v0.21.9) (2026-02-18)


### Features

* Add function to swap two array elements that lowers to hugr swap op ([#1459](https://github.com/Quantinuum/guppylang/issues/1459)) ([15da521](https://github.com/Quantinuum/guppylang/commit/15da521d27354d294dd7f69c4494f9a1bc4d7032))
* Add missing bool methods (__rxor__, __rand__, __ror__) ([#1498](https://github.com/Quantinuum/guppylang/issues/1498)) ([6078136](https://github.com/Quantinuum/guppylang/commit/6078136b26d0155cd663bf3ee245f97fd0e56a33))
* Allow panicking with different signal values ([#1461](https://github.com/Quantinuum/guppylang/issues/1461)) ([e624d4f](https://github.com/Quantinuum/guppylang/commit/e624d4f8b99dc2db7207f3148e8b2e378cfeb648))
* Compile time array bounds check for literal indices ([#1438](https://github.com/Quantinuum/guppylang/issues/1438)) ([d2dd890](https://github.com/Quantinuum/guppylang/commit/d2dd890951c7ef06d6baf98b2f55acef86a53a25))
* Lower nat to int conversion to `iu_to_s` hugr op ([#1480](https://github.com/Quantinuum/guppylang/issues/1480)) ([2ba5720](https://github.com/Quantinuum/guppylang/commit/2ba57202db6e6f7a72f80238742c671c823f59aa))
* Make tket a non-optional dependency ([#1440](https://github.com/Quantinuum/guppylang/issues/1440)) ([4af4360](https://github.com/Quantinuum/guppylang/commit/4af4360495c9d6155e69310d5bfb8f22953fc1ff))


### Bug Fixes

* Improve docstring formatting array methods ([#1499](https://github.com/Quantinuum/guppylang/issues/1499)) ([4b8ce4c](https://github.com/Quantinuum/guppylang/commit/4b8ce4c06762f7d9627457d8571b5a27fed9ae38))
* Upgrade selene-sim version to fix state ordering bug ([#1444](https://github.com/Quantinuum/guppylang/issues/1444)) ([d976df9](https://github.com/Quantinuum/guppylang/commit/d976df90410e0452202671c481a28163e5f8aae5))


### Documentation

* Add API docs for std modules ([#1428](https://github.com/Quantinuum/guppylang/issues/1428)) ([7b38fc6](https://github.com/Quantinuum/guppylang/commit/7b38fc61e0996c2a2bc8fbd1180c7a0cc6ac2312))

## [0.21.8](https://github.com/Quantinuum/guppylang/compare/guppylang-v0.21.7...guppylang-v0.21.8) (2026-01-09)

### Features

* Add qubit hints on Guppy functions, allowing elision when building emulators ([#1378](https://github.com/Quantinuum/guppylang/issues/1378)) ([b7f10c6](https://github.com/Quantinuum/guppylang/commit/b7f10c6798aa20841fae844084d8a1606661fd7b)), closes [#1297](https://github.com/Quantinuum/guppylang/issues/1297)
* Add unsafe array take and put operations ([#1165](https://github.com/Quantinuum/guppylang/issues/1165)) ([7f342e7](https://github.com/Quantinuum/guppylang/commit/7f342e788e2f179382bab46dcc7e69a24dd64de3))
* update to guppylang-internals 0.27 ([#1430](https://github.com/Quantinuum/guppylang/issues/1430)) ([be02891](https://github.com/Quantinuum/guppylang/commit/be02891955ac07819144e1e27374c3324d521536))
* Update to hugr v0.15, includes collated_digitstring_counts to extend bitstring collation to digits (#2788) (191c473)

### Bug Fixes

* Fix regression in `result` calls ([#1426](https://github.com/Quantinuum/guppylang/issues/1426)) ([9be6fef](https://github.com/Quantinuum/guppylang/commit/9be6fefcdfb9fc9eb1025774d2dd2727b3e719b1))
* Convert symbolic pytket circuits angle inputs into rotations ([#1425](https://github.com/Quantinuum/guppylang/issues/1425)) ([4724d90](https://github.com/Quantinuum/guppylang/commit/4724d9039d8dffae8fd939f62ae80ec307d8918a))
* Fix Hugr generation for tuples in `Result` and `Either` ([#1395](https://github.com/Quantinuum/guppylang/issues/1395)) ([f8b0d47](https://github.com/Quantinuum/guppylang/commit/f8b0d47eb275aae3f5ba804dfeb3640c4a3baef6)), closes [#1388](https://github.com/Quantinuum/guppylang/issues/1388)
* Improve diagnostics rendering ([#1382](https://github.com/Quantinuum/guppylang/issues/1382)) ([e7ce7f6](https://github.com/Quantinuum/guppylang/commit/e7ce7f6d1a4f2b12ff680a6e54dae96637c5fa92))
* Improve diagnostics rendering for wasm ([#1399](https://github.com/Quantinuum/guppylang/issues/1399)) ([6604175](https://github.com/Quantinuum/guppylang/commit/660417542f2b36c387e73765f8647c11cd3d1a7b)), ([#1398](https://github.com/Quantinuum/guppylang/issues/1398)) ([a6a539f](https://github.com/Quantinuum/guppylang/commit/a6a539fe07cc94f4a788fef506969e4c9027faee))
* Support comptime expressions in generic argument applications ([#1409](https://github.com/Quantinuum/guppylang/issues/1409)) ([c1aad34](https://github.com/Quantinuum/guppylang/commit/c1aad346adb15e3636e5586987422d74e36189a1)), closes [#1087](https://github.com/Quantinuum/guppylang/issues/1087)

## [0.21.7](https://github.com/Quantinuum/guppylang/compare/guppylang-v0.21.6...guppylang-v0.21.7) (2025-12-15)

### Features

* Unitarity annotations for functions ([#1292](https://github.com/Quantinuum/guppylang/issues/1292)) ([54dc200](https://github.com/Quantinuum/guppylang/commit/54dc200de881d065d3ee92bdc9a8ca076990d412))


### Bug Fixes

* Fix rendering of `compile_entrypoint` diagnostics ([#1343](https://github.com/Quantinuum/guppylang/issues/1343)) ([fcd2131](https://github.com/Quantinuum/guppylang/commit/fcd2131d58ad9c0bd9fba868f7581012d8f83916)), closes [#1340](https://github.com/Quantinuum/guppylang/issues/1340)


### Miscellaneous Chores

* **guppylang:** upgrade to internals 0.26 ([#1381](https://github.com/Quantinuum/guppylang/issues/1381)) ([8575890](https://github.com/Quantinuum/guppylang/commit/85758904d1cb61556c456362817003e7210910a1))


### Code Refactoring

* Implement `result` using overloads instead of a custom node ([#1361](https://github.com/Quantinuum/guppylang/issues/1361)) ([1da2c5d](https://github.com/Quantinuum/guppylang/commit/1da2c5dbb82bf6da35949b505a69f4e2f51acd3b))

## [0.21.6](https://github.com/quantinuum/guppylang/compare/guppylang-v0.21.5...guppylang-v0.21.6) (2025-10-29)


### Features

* implement str() for PartialVector  ([d85efc9](https://github.com/quantinuum/guppylang/commit/d85efc971c81f60eb6e7f2881623803ff45b43d1)), closes [#1225](https://github.com/quantinuum/guppylang/issues/1225)
* **qsystem:** add `RNG.random_advance()` ([#1295](https://github.com/quantinuum/guppylang/issues/1295)) ([f6271a2](https://github.com/quantinuum/guppylang/commit/f6271a29768241e6e285f05c3eb3ccd2db9d12ac))
* Use `borrow_array` instead of `value_array` for array HUGR codegen ([#1166](https://github.com/quantinuum/guppylang/issues/1166)) ([f9ef42b](https://github.com/quantinuum/guppylang/commit/f9ef42b2baf61c3e1c2cfcf7bd1f3bcac33a1a25))

## [0.21.5](https://github.com/quantinuum/guppylang/compare/guppylang-v0.21.4...guppylang-v0.21.5) (2025-09-22)

> [!WARNING]
> The `.compile()` method now assumes the function being compiled is an execution entrypoint and therefore checks it takes no arguments.
> If you have an existing workflow that produces a HUGR with a non-executable function this will break, use `compile_function` instead.

### Features

* `compile_entrypoint` and `compile_function` methods ([#1271](https://github.com/quantinuum/guppylang/issues/1271)) ([44883e2](https://github.com/quantinuum/guppylang/commit/44883e20ed3bdbad69a73b939aec53b250dbc166))

## [0.21.4](https://github.com/quantinuum/guppylang/compare/guppylang-v0.21.3...guppylang-v0.21.4) (2025-09-19)


### Features

* Add `Result` type ([#1171](https://github.com/quantinuum/guppylang/issues/1171)) ([a36630e](https://github.com/quantinuum/guppylang/commit/a36630eac71c85e255cdce8b44ee1f04d250677d)), closes [#1170](https://github.com/quantinuum/guppylang/issues/1170)
* Preserve previous results upon error ([#1245](https://github.com/quantinuum/guppylang/issues/1245)) ([2fa9969](https://github.com/quantinuum/guppylang/commit/2fa996919d61430f26da982039b5ac81d599eab1))


### Bug Fixes

* comptime should act as identity in python context  ([#1240](https://github.com/quantinuum/guppylang/issues/1240)) ([d800ad6](https://github.com/quantinuum/guppylang/commit/d800ad6b9383a0e596a1af08b5618109bf223b92)), closes [#1239](https://github.com/quantinuum/guppylang/issues/1239)
* **emulator:** update selene compiler to pull in cz fix ([#1237](https://github.com/quantinuum/guppylang/issues/1237)) ([550d6fc](https://github.com/quantinuum/guppylang/commit/550d6fccdb6bb84c85cb3f65cbc46e02b0989ce2))
* Fix `nat` constructor in comptime functions ([#1258](https://github.com/quantinuum/guppylang/issues/1258)) ([e257b6f](https://github.com/quantinuum/guppylang/commit/e257b6fc2fe3793d6d8f63feca83bf5ed6643673))
* Fix signature of `nat.__mod__` ([#1259](https://github.com/quantinuum/guppylang/issues/1259)) ([fe7d4b2](https://github.com/quantinuum/guppylang/commit/fe7d4b2955362a347e0fba8b02e02833e70faa06)), closes [#1257](https://github.com/quantinuum/guppylang/issues/1257)
* Use qualified `extend_type` function ([#1263](https://github.com/quantinuum/guppylang/issues/1263)) ([6878b0b](https://github.com/quantinuum/guppylang/commit/6878b0b9ffd61b5e13f01f7679b9516b5d466693))
* wasm module updates based on tested lowering ([#1230](https://github.com/quantinuum/guppylang/issues/1230)) ([657cea2](https://github.com/quantinuum/guppylang/commit/657cea27af00a9c02e8d1a3190db535bbd1e7981))
* **wasm:** off by one error in WASM module ([#1236](https://github.com/quantinuum/guppylang/issues/1236)) ([2ac81da](https://github.com/quantinuum/guppylang/commit/2ac81daa3cfe4e96b04decd94b2ee517ae5249d5))


### Documentation

* use root README for pypi page ([#1227](https://github.com/quantinuum/guppylang/issues/1227)) ([9790e03](https://github.com/quantinuum/guppylang/commit/9790e03fd77c3393d71d386bbba856a5a7656a17))


### Miscellaneous Chores

* update internals dependency to 0.24 ([#1268](https://github.com/quantinuum/guppylang/issues/1268)) ([153afa1](https://github.com/quantinuum/guppylang/commit/153afa17e4f533433a4f2849a6b0e4d14f25a67a))

## [0.21.3](https://github.com/quantinuum/guppylang/compare/guppylang-v0.21.2...guppylang-v0.21.3) (2025-08-19)


### Features

* De-deprecate 'py' (still just a shorter alias for `comptime`) ([#1202](https://github.com/quantinuum/guppylang/issues/1202)) ([32fbee1](https://github.com/quantinuum/guppylang/commit/32fbee19124b1361f4fb0c2a0e836eaa3e39ca51))
* Make collections iterable and discardable ([#1164](https://github.com/quantinuum/guppylang/issues/1164)) ([eb5d817](https://github.com/quantinuum/guppylang/commit/eb5d8173f59b0ccdf2402872deb4aabff7ff634b))


### Bug Fixes

* cache state extraction to allow multiple access ([#1184](https://github.com/quantinuum/guppylang/issues/1184)) ([ac4531c](https://github.com/quantinuum/guppylang/commit/ac4531c02870f00edc135de613e84d01e1120760)), closes [#1183](https://github.com/quantinuum/guppylang/issues/1183)
* **emulator:** incorrect pure state check ([20651db](https://github.com/quantinuum/guppylang/commit/20651db5663d00382d67ddccb44c1ee79caefb6a))


### Documentation

* Extended emulator docs ([20651db](https://github.com/quantinuum/guppylang/commit/20651db5663d00382d67ddccb44c1ee79caefb6a))
* Several docstring fixes

## [0.21.2](https://github.com/quantinuum/guppylang/compare/guppylang-v0.21.1...guppylang-v0.21.2) (2025-08-11)


### Features

* We can now pass a `start` and `step` for the [range](../../api/generated/guppylang.std.iter.range.rst) function just as we can in Python. ([#1157](https://github.com/quantinuum/guppylang/issues/1157)) ([a1b9333](https://github.com/quantinuum/guppylang/commit/a1b9333712c74270d5efaaa72f83d6b09047c068))
* pin to selene-sim [0.2.0](https://github.com/quantinuum/selene/releases/tag/v0.2.0) ([#1156](https://github.com/quantinuum/guppylang/issues/1156)) ([08c52c0](https://github.com/quantinuum/guppylang/commit/08c52c01f6034a315d03bd978f255358e6f92930))
* Update to guppylang-internals 0.22.0
* Support float parameters as inputs to symbolic circuits loaded with `guppy.load_pytket`. ([#1105](https://github.com/quantinuum/guppylang/issues/1105)) ([34c546c](https://github.com/quantinuum/guppylang/commit/34c546c3b5787beb839687fdbf4db8bc94f36c4a)), closes [#1076](https://github.com/quantinuum/guppylang/issues/1076) (see example below).

```{code-cell} ipython3
from guppylang import guppy
from guppylang.std.angles import pi
from guppylang.std.quantum import qubit, rx, discard

from pytket import Circuit
from sympy import Symbol

a = Symbol("alpha")

circ = Circuit(1, 1)
circ.Rx(a, 0)
circ.Measure(0, 0)

rx_func = guppy.load_pytket("rx", circ, use_arrays=False)

@guppy
def perform_rx_flip() -> int:
    """Perform an X gate as Rx(q, pi)"""
    q = qubit()
    res = int(rx_func(q, pi))
    discard(q)
    return res

perform_rx_flip.check()
```

### Bug Fixes

* **emulator:** pass runtime option to selene ([ac969e8](https://github.com/quantinuum/guppylang/commit/ac969e8ce8d8bad90f9cfd9cb0470c62d08cfe79))
* Fix a scoping issue with builtins functions [#1122](https://github.com/quantinuum/guppylang/issues/1122)

### Documentation

* Create CITATIONS.bib ([#1133](https://github.com/quantinuum/guppylang/issues/1133)) ([ff5d354](https://github.com/quantinuum/guppylang/commit/ff5d35407c5790953f12e27ad80150cc30e7f8c3))
* fix some docstring formatting ([#1172](https://github.com/quantinuum/guppylang/issues/1172)) ([f84b756](https://github.com/quantinuum/guppylang/commit/f84b7565e7465f99d0fbb16f640a91cfe700a45e))


## [0.21.1](https://github.com/quantinuum/guppylang/compare/guppylang-v0.21.0...guppylang-v0.21.1) (2025-08-05)


### Bug Fixes

* **guppylang-internals:** Fix circular import for custom decorators ([#1146](https://github.com/quantinuum/guppylang/issues/1146)) ([d8474d8](https://github.com/quantinuum/guppylang/commit/d8474d8af3d394275268cd3d0754ff06ecb9bcc2)), closes [#1145](https://github.com/quantinuum/guppylang/issues/1145)
* overwrite generator metadata with guppylang version ([#1147](https://github.com/quantinuum/guppylang/issues/1147)) ([2e20693](https://github.com/quantinuum/guppylang/commit/2e206933b4f87515e375034ab108523bad7ebb5e)), closes [#1138](https://github.com/quantinuum/guppylang/issues/1138)
* **std:** remove deprecated decorators ([#1151](https://github.com/quantinuum/guppylang/issues/1151)) ([b309ba5](https://github.com/quantinuum/guppylang/commit/b309ba524b70ebc704facdeebc709f78b273e449))
* Support `None` value ([#1149](https://github.com/quantinuum/guppylang/issues/1149)) ([7f606c7](https://github.com/quantinuum/guppylang/commit/7f606c778d98312a0d1c4a9c7a27448c24d80585)), closes [#1148](https://github.com/quantinuum/guppylang/issues/1148)


### Documentation

* Fix docs build ([#1142](https://github.com/quantinuum/guppylang/issues/1142)) ([4dfd575](https://github.com/quantinuum/guppylang/commit/4dfd575bcdfdf1e2db4e61f2f406fff27e0c08f7))

## [0.21.0](https://github.com/quantinuum/guppylang/compare/guppylang-v0.20.0...guppylang-v0.21.0) (2025-08-04)


### ⚠ BREAKING CHANGES

* All compiler-internal and non-userfacing functionality is moved into a new `guppylang_internals` package
* `guppy.compile(foo)` and `guppy.check(foo)` are both now deprecated and will be removed in a future release. Their usage should be replaced with `foo.compile()` and `foo.check()`.
* The `main` function no longer has a special status in Guppy. Any function which takes no arguments can be a valid entrypoint
to a program.
* default HUGR output uses compressed binary encoding.
* `guppylang.tracing.object.GuppyDefinition` moved to `guppylang.defs.GuppyDefinition` `guppylang.tracing.object.TypeVarGuppyDefinition` moved and renamed to `guppylang.defs.GuppyTypeVarDefinition`
* All `to_hugr` methods on types, arguments, and parameters now require a `ToHugrContext` `CompilableDef.compile_outer` now requires a `ToHugrContext` `guppy.hugr_op` now passes the compiler context to the function generating the op `CheckedFunctionDef` now implements `MonomorphizableDef` instead of `CompilableDef` `CompilerContext.build_compiled_def` now requires an instantiation for the definition's type parameters The `ToHugrContext` protocol now requires two additional methods: `type_var_to_hugr` and `const_var_to_hugr` `CompilerContext.{compiled, worklist}` and `CompilationEngine.compiled` are now indexed by a tuple of `DefId` and optional `PartiallyMonomorphizedArgs`
* Any [comptime](../../language_guide/comptime.md) code that previously used constant integers outside the 64-bit signed integer range will now fail to compile.
* Capturing closures are now disabled by default. Enabling them requires calling `guppylang.enable_experimental_features()`, however note that they are not supported throughout the stack.

### Features

* Add emulation of Guppy programs powered by the [Selene](https://github.com/quantinuum/selene) framework ([#1127](https://github.com/quantinuum/guppylang/issues/1127))([5e2f595](https://github.com/quantinuum/guppylang/commit/5e2f5951dff8782f7bbfe656ed02edf761a66593)). See the [Getting Started](../../../sphinx/getting_started.md) guide and the [Examples Gallery](../../../sphinx/examples_index.md) for example usage.
* Add `Future` type ([#1075](https://github.com/quantinuum/guppylang/issues/1075)) ([5ad7673](https://github.com/quantinuum/guppylang/commit/5ad76734c58e6d0c48a487c0645a4265abf3763e))
* add error when constant integer out of bounds ([#1084](https://github.com/quantinuum/guppylang/issues/1084)) ([eee77ae](https://github.com/quantinuum/guppylang/commit/eee77ae92d0490f9a6fc843b02729a4fc88ba16c))
* Add guppy version metadata to hugr entrypoint ([#1039](https://github.com/quantinuum/guppylang/issues/1039)) ([0eafbd9](https://github.com/quantinuum/guppylang/commit/0eafbd9f8e52484ae823aba830c1d38d30dd9755)), closes [#1037](https://github.com/quantinuum/guppylang/issues/1037)
* Add manual registration of extensions ([#1045](https://github.com/quantinuum/guppylang/issues/1045)) ([4b42936](https://github.com/quantinuum/guppylang/commit/4b42936372d408b1b3c79a86e21d2a09a4220799))
* add qsystem op for measure leaked ([#1057](https://github.com/quantinuum/guppylang/issues/1057)) ([c555727](https://github.com/quantinuum/guppylang/commit/c55572716333b1b88026c6d0221a1cb9fbd7d1a1))
* add selene via optional feature and use for testing ([#1081](https://github.com/quantinuum/guppylang/issues/1081)) ([cefc70e](https://github.com/quantinuum/guppylang/commit/cefc70e9a51c6fe5cac318d35473f953b9bff893))
* Add support for V and Vdg. ([#1094](https://github.com/quantinuum/guppylang/issues/1094)) ([6b0d44a](https://github.com/quantinuum/guppylang/commit/6b0d44a5b1b6661a0d67e3df261a188bdb9a7f0b))
* Allow indexing on tuples ([#1038](https://github.com/quantinuum/guppylang/issues/1038)) ([0e9097e](https://github.com/quantinuum/guppylang/commit/0e9097eb14d3fd254ad1220f6feeaac74314afe6)), closes [#711](https://github.com/quantinuum/guppylang/issues/711)
* Declare WASM modules in guppy ([#942](https://github.com/quantinuum/guppylang/issues/942)) ([e1240fb](https://github.com/quantinuum/guppylang/commit/e1240fbec33703bf8a311dd7c0139ca36c11aed8))
* Extend comptime arguments to arbitrary non-linear types ([#1110](https://github.com/quantinuum/guppylang/issues/1110)) ([384dd8c](https://github.com/quantinuum/guppylang/commit/384dd8cdebdd68c13279e096e7d74bcb50f9667c))
* Make decorator return types more precise ([#1115](https://github.com/quantinuum/guppylang/issues/1115)) ([c84e8b1](https://github.com/quantinuum/guppylang/commit/c84e8b13d63bc2c3453ffd1adb47451f2009db16))
* set hugr entrypoint to compiled function ([#1063](https://github.com/quantinuum/guppylang/issues/1063)) ([16bd267](https://github.com/quantinuum/guppylang/commit/16bd2675bffa30d09ef700625e65afdac131aaa9))
* store used extensions and versions in HUGR metadata ([#1049](https://github.com/quantinuum/guppylang/issues/1049)) ([a9a300c](https://github.com/quantinuum/guppylang/commit/a9a300c6d4e1f517002b4bf83885c2f6653efa70)), closes [#1048](https://github.com/quantinuum/guppylang/issues/1048)
* Support arbitrary const generics via monomorphisation ([#1033](https://github.com/quantinuum/guppylang/issues/1033)) ([bcf9865](https://github.com/quantinuum/guppylang/commit/bcf986539daf4794172e7b078d4bae432bed331f))
* Support Python 3.12 generic syntax ([#1051](https://github.com/quantinuum/guppylang/issues/1051)) ([ab2e118](https://github.com/quantinuum/guppylang/commit/ab2e118e5d697f71d8226bc06ce9068e689fb367)), closes [#823](https://github.com/quantinuum/guppylang/issues/823)
* update to hugr-py v0.13 ([#1083](https://github.com/quantinuum/guppylang/issues/1083)) ([8f071c8](https://github.com/quantinuum/guppylang/commit/8f071c8c3c7bb88d0fbe79e41a7f5ccf768248ec))
* use `core.` prefix for metadata keys ([#1055](https://github.com/quantinuum/guppylang/issues/1055)) ([2bf0d68](https://github.com/quantinuum/guppylang/commit/2bf0d68eefc1f1211130328555e1f288235baef3))


### Bug Fixes

* Allow array comprehension syntax in comptime functions ([#1068](https://github.com/quantinuum/guppylang/issues/1068)) ([da8f04a](https://github.com/quantinuum/guppylang/commit/da8f04a04485b0e362ce736887235089b04b2ef7)), closes [#1067](https://github.com/quantinuum/guppylang/issues/1067)
* Allow struct redefinitions for Python &lt; 3.13 ([#1108](https://github.com/quantinuum/guppylang/issues/1108)) ([959a4e4](https://github.com/quantinuum/guppylang/commit/959a4e4d93fde387a669f47bdbe1fbcff2090046)), closes [#1107](https://github.com/quantinuum/guppylang/issues/1107)
* Correctly detect `[@custom](https://github.com/custom)_guppy_decorator` in nested scopes ([#1086](https://github.com/quantinuum/guppylang/issues/1086)) ([678583c](https://github.com/quantinuum/guppylang/commit/678583c173407d2827ae44c7e22a96639170685f))
* Fix diagnostics rendering for comptime entrypoints ([#1099](https://github.com/quantinuum/guppylang/issues/1099)) ([fdd2676](https://github.com/quantinuum/guppylang/commit/fdd26760a0ab8c3a3df2bdc6a5eb5dc4c816bd9c)), closes [#1097](https://github.com/quantinuum/guppylang/issues/1097)
* Fix frame lookup for Python 3.12 annotation scopes ([#1120](https://github.com/quantinuum/guppylang/issues/1120)) ([a69e489](https://github.com/quantinuum/guppylang/commit/a69e4899d49ecae00335e47cdbed5953f0a16012)), closes [#1116](https://github.com/quantinuum/guppylang/issues/1116)
* Fix hugr conversion and bounds checks on numeric literals ([#1100](https://github.com/quantinuum/guppylang/issues/1100)) ([73d5e92](https://github.com/quantinuum/guppylang/commit/73d5e92ac7af1b9f900a2f55b461d925f143a3f0))
* Fix Jupyter notebook diagnostic rendering ([#1109](https://github.com/quantinuum/guppylang/issues/1109)) ([6002474](https://github.com/quantinuum/guppylang/commit/6002474a533ac22c18837c2a560e4478c188f9f9))
* Fix nested function definitions in Python 3.12 ([#1064](https://github.com/quantinuum/guppylang/issues/1064)) ([090f920](https://github.com/quantinuum/guppylang/commit/090f920646703a40ece6cc5305d1011f2a220ff5))
* Stop showing temporary variables in comptime diagnostics ([#1112](https://github.com/quantinuum/guppylang/issues/1112)) ([63854c5](https://github.com/quantinuum/guppylang/commit/63854c54492e66de0d2e70d6f06a411093dab992)), closes [#1111](https://github.com/quantinuum/guppylang/issues/1111)
* support comptime entrypoint ([#1079](https://github.com/quantinuum/guppylang/issues/1079)) ([721e3dd](https://github.com/quantinuum/guppylang/commit/721e3dde7ca18d2a1eaa541ff6d5c8b81d296c23))
* Turn capturing closures into experimental feature ([#1065](https://github.com/quantinuum/guppylang/issues/1065)) ([a959b18](https://github.com/quantinuum/guppylang/commit/a959b1848f96c7899fd5d4ba173bd371c9aa286a))


### Documentation

* add docstrings for emulator module ([#1131](https://github.com/quantinuum/guppylang/issues/1131)) ([b33e065](https://github.com/quantinuum/guppylang/commit/b33e0656f152ce8dc4bc09b7a44d7b3017e28c8b))
* add quantum and qsystem gate definitions ([#912](https://github.com/quantinuum/guppylang/issues/912)) ([32a4bbc](https://github.com/quantinuum/guppylang/commit/32a4bbced00b4603c2c4d04af3c35e40bcac427f))
* Fix docstrings ([#1128](https://github.com/quantinuum/guppylang/issues/1128)) ([0aded85](https://github.com/quantinuum/guppylang/commit/0aded8524807d521adfd3137a62d92da0291b937))
* Improve RNG docs ([#1043](https://github.com/quantinuum/guppylang/issues/1043)) ([8640f06](https://github.com/quantinuum/guppylang/commit/8640f06f78a56d8c7a931481ca224eb7ac596c8a))
* replace `compile_module` usage in README ([#1041](https://github.com/quantinuum/guppylang/issues/1041)) ([03ccf3a](https://github.com/quantinuum/guppylang/commit/03ccf3a27d8f7f1f186483acec0573d57c2cc1c0))
* Update guppy examples ([#1121](https://github.com/quantinuum/guppylang/issues/1121)) ([b994655](https://github.com/quantinuum/guppylang/commit/b9946559856232398e757a10159bbe140c6cb27f))


### Code Refactoring

* Split up into `guppylang_internals` package ([#1126](https://github.com/quantinuum/guppylang/issues/1126)) ([81d50c0](https://github.com/quantinuum/guppylang/commit/81d50c0a24f55eca48d62e4b0275ef2126c5e626))

## [0.20.0](https://github.com/quantinuum/guppylang/compare/v0.19.1...v0.20.0) (2025-06-19)


### ⚠ BREAKING CHANGES

Explicit Guppy modules have been removed. Instead, use the regular `@guppy` decorator everywhere without passing an explicit module. Compilation is now triggered via the `.compile` method.

#### 0.19.0 syntax

```{code-cell} ipython3
---
tags: [skip-execution]
---
@guppy
def main() -> None:
    ...

guppy.compile_module()
```

#### 0.20.0 syntax

```{code-cell} ipython3
---
tags: [skip-execution]
---
@guppy
def main() -> None:
    ...

main.compile()
```

### Features

* `with_owned` std library function to temporarily take ownership of a borrowed value ([#994](https://github.com/quantinuum/guppylang/issues/994)) ([7bf75df](https://github.com/quantinuum/guppylang/commit/7bf75dff290b3b652c1939bffb86a915555207d2)), closes [#992](https://github.com/quantinuum/guppylang/issues/992)
* Add an [Either](../../api/generated/guppylang.std.either.Either.rst) type to the standard library. ([#993](https://github.com/quantinuum/guppylang/issues/993)) ([75c1804](https://github.com/quantinuum/guppylang/commit/75c18045747017aaacad74f92fc92d4e0cd78182)), closes [#991](https://github.com/quantinuum/guppylang/issues/991)
* Added a [PriorityQueue](../../api/generated/guppylang.std.collections.PriorityQueue.rst) structure to the standard library.
* Guppy programs can now include `state_result` tags which can be used together with Selene to retrieve the statevector at a given point in the program execution ([#905](https://github.com/quantinuum/guppylang/issues/905)) ([2217bbc](https://github.com/quantinuum/guppylang/commit/2217bbc63d910a29b5a4f732d0c3224617ca8dcf)). See the example notebook on [Debugging with State Results](https://github.com/quantinuum/guppylang/blob/main/examples/state_results.ipynb).
* Add optional signature argument to RawCustomFunctionDef ([#1005](https://github.com/quantinuum/guppylang/issues/1005)) ([79e2d5b](https://github.com/quantinuum/guppylang/commit/79e2d5b77acd09645f02755de2e6e4a40ce49b10)), closes [#1003](https://github.com/quantinuum/guppylang/issues/1003)
* Add PriorityQueue to standard library ([#1006](https://github.com/quantinuum/guppylang/issues/1006)) ([4e609f0](https://github.com/quantinuum/guppylang/commit/4e609f08933f4e0f4f459cf10f2ecca9079bb7aa))
* Allow users to wrap `guppy` in their own decorator ([#1017](https://github.com/quantinuum/guppylang/issues/1017)) ([f047c9b](https://github.com/quantinuum/guppylang/commit/f047c9bd16fdb26e757365c0ae8d2ec019f0aa06))
* Comptime `nat` arguments ([#1015](https://github.com/quantinuum/guppylang/issues/1015)) ([d2a9a07](https://github.com/quantinuum/guppylang/commit/d2a9a0736c7466f943f886040865216892e6d3f9))
* **diagnostics:** add miette bindings for enhanced error rendering ([#998](https://github.com/quantinuum/guppylang/issues/998)) ([c8f2724](https://github.com/quantinuum/guppylang/commit/c8f2724c17ed2d7e7523c9c9564417d7962a62f9))
* Function overloading via static dispatch ([#1000](https://github.com/quantinuum/guppylang/issues/1000)) ([6f523d6](https://github.com/quantinuum/guppylang/commit/6f523d6c1f5c207fbc8e256ef12c6600e7999d12)). See the corresponding section of the [language guide](../../language_guide/functions.md#function-overloading--static-dispatch) for more information.
* Remove explicit Guppy modules ([#983](https://github.com/quantinuum/guppylang/issues/983)) ([0b2e652](https://github.com/quantinuum/guppylang/commit/0b2e652d5b4899785de13cb1e0568786777f40c0))

### Bug Fixes

* deterministic worklist iteration order ([#1025](https://github.com/quantinuum/guppylang/issues/1025)) ([effa51b](https://github.com/quantinuum/guppylang/commit/effa51b7b582690be9ca617a66376b448f986da2)), closes [#1024](https://github.com/quantinuum/guppylang/issues/1024)
* Fix invalid Hugr when reassigning a used variable ([#1026](https://github.com/quantinuum/guppylang/issues/1026)) ([8dd0bc4](https://github.com/quantinuum/guppylang/commit/8dd0bc4544d62886a73af935e7e7736ea137aacc))


### Documentation

* Fix sphinx autodoc for Guppy functions ([#1028](https://github.com/quantinuum/guppylang/issues/1028)) ([62f6234](https://github.com/quantinuum/guppylang/commit/62f6234e47e4457791752bd37b9e2f202d3016af))
* remove wrappers on random docs, add doc to get_current_shot ([#1001](https://github.com/quantinuum/guppylang/issues/1001)) ([4de4ef2](https://github.com/quantinuum/guppylang/commit/4de4ef2d3cc8a06d87be0ea9921cdbaee18771f0))
* use the sphinx furo theme for guppy compiler docs ([#1031](https://github.com/quantinuum/guppylang/issues/1031)) ([e0a767b](https://github.com/quantinuum/guppylang/commit/e0a767b07f25ad651bbca85dc3fac4d9b0fc8d39))

## [0.19.1](https://github.com/quantinuum/guppylang/compare/v0.19.0...v0.19.1) (2025-05-27)


### Features

* Add methods for generating random angles ([#979](https://github.com/quantinuum/guppylang/issues/979)) ([129bc5d](https://github.com/quantinuum/guppylang/commit/129bc5d50556141f5e48960e2e570464f58ef485))


### Bug Fixes

* Merge `Bool` and `bool` in builtins ([#977](https://github.com/quantinuum/guppylang/issues/977)) ([5fa2e59](https://github.com/quantinuum/guppylang/commit/5fa2e59be5929dc34d0ee3c03b2939cdf4b50eab))
* Swap back copyable elements in `array.__getitem__` ([#982](https://github.com/quantinuum/guppylang/issues/982)) ([a2b0255](https://github.com/quantinuum/guppylang/commit/a2b02555336c35b1ad9f5e5115472cd2755dd02b)), closes [#980](https://github.com/quantinuum/guppylang/issues/980)

## [0.19.0](https://github.com/quantinuum/guppylang/compare/v0.18.2...v0.19.0) (2025-05-22)


### ⚠ BREAKING CHANGES

* Bools in HUGRs generated by Guppy are represented using a `tket2.bool` instead of the HUGR sum type
* deprecated `hresult` and `qsys_result` modules have been removed. Use `hugr.qysystem.result` directly.
* Generated HUGRs now refer to entrypoints and are always modules in envelopes.

### Features

* Add stack data structure to standard library ([#973](https://github.com/quantinuum/guppylang/issues/973)) ([f82ee42](https://github.com/quantinuum/guppylang/commit/f82ee429eb9703dc4b4014eb8763e6b6907e9bcc))
* Bump to Hugr 0.20 and switch to value arrays for lowering ([#930](https://github.com/quantinuum/guppylang/issues/930)) ([321b68c](https://github.com/quantinuum/guppylang/commit/321b68cfe8d4ae430c2410c4f890de171a6449cf))
* Implement sampling from a generic discrete distribution ([#966](https://github.com/quantinuum/guppylang/issues/966)) ([2cb3c6d](https://github.com/quantinuum/guppylang/commit/2cb3c6d16a2ce6d05127528e92f4ed744fbd1318))
* Stop emitting non-local edges ([#962](https://github.com/quantinuum/guppylang/issues/962)) ([e5e55b1](https://github.com/quantinuum/guppylang/commit/e5e55b13832943771acc3867fd752b6f2f5f0ca6)), closes [#963](https://github.com/quantinuum/guppylang/issues/963)


### Bug Fixes

* Specify bash shell in justfile. ([#971](https://github.com/quantinuum/guppylang/issues/971)) ([1ec956e](https://github.com/quantinuum/guppylang/commit/1ec956e87b793791febe7a26a2009a63515253bc))
* Stop monomorphising higher-order custom function values ([#972](https://github.com/quantinuum/guppylang/issues/972)) ([952dba0](https://github.com/quantinuum/guppylang/commit/952dba0b8f2f1ca7441491f2fcf3e6c9cdbb64fd))
* stop using value ExtensionSet ([#967](https://github.com/quantinuum/guppylang/issues/967)) ([4d47b5f](https://github.com/quantinuum/guppylang/commit/4d47b5f1bfcf3105946fe59412932e1189a6cd99))


### Documentation

* fix docstring backtick ([#976](https://github.com/quantinuum/guppylang/issues/976)) ([498f3fb](https://github.com/quantinuum/guppylang/commit/498f3fbcfe1b59f0bad82153137a3fa50978153e))


### Code Refactoring

* Change bool lowering to an opaque type ([#900](https://github.com/quantinuum/guppylang/issues/900)) ([a71d949](https://github.com/quantinuum/guppylang/commit/a71d94993358f1eb1dd73b1e844289b2093ac26c))
* delete deprecated result modules ([#975](https://github.com/quantinuum/guppylang/issues/975)) ([ab800cc](https://github.com/quantinuum/guppylang/commit/ab800cccd83e95dd521442a26b6b8d495b1e3815))

## [0.18.2](https://github.com/quantinuum/guppylang/compare/v0.18.1...v0.18.2) (2025-05-19)


### Features

* Add some explicit copy diagnostic hints ([#941](https://github.com/quantinuum/guppylang/issues/941)) ([c99526e](https://github.com/quantinuum/guppylang/commit/c99526efe837ef04fd5263e3670c8e5cff3a991a))


### Bug Fixes

* Better error message for unsupported generic comptime functions ([#951](https://github.com/quantinuum/guppylang/issues/951)) ([35bfbcb](https://github.com/quantinuum/guppylang/commit/35bfbcb35829933d457e950fd8c3ac61a79670a8)), closes [#944](https://github.com/quantinuum/guppylang/issues/944)
* Capture entire Python scope when defining comptime functions ([#952](https://github.com/quantinuum/guppylang/issues/952)) ([898a033](https://github.com/quantinuum/guppylang/commit/898a033da0458b8e92fde4b586453a4f69881a0c)), closes [#945](https://github.com/quantinuum/guppylang/issues/945)
* Fix `result` / `panic` /  `exit` calls in comptime functions ([#949](https://github.com/quantinuum/guppylang/issues/949)) ([ac4a515](https://github.com/quantinuum/guppylang/commit/ac4a515514a1263d261e1039f741839a7e078433))
* Fix comptime angle arithmetic ([#950](https://github.com/quantinuum/guppylang/issues/950)) ([dd0fdc3](https://github.com/quantinuum/guppylang/commit/dd0fdc33b4c0e62df5c8a1418432743a5446753b))
* Fix resolution of generic lengths in array constructor ([#940](https://github.com/quantinuum/guppylang/issues/940)) ([0f1d5db](https://github.com/quantinuum/guppylang/commit/0f1d5dbaceaf94f60655231b0c9b5c9658f2ea29))
* Fix too narrow rendering of indented diagnostic labels ([#933](https://github.com/quantinuum/guppylang/issues/933)) ([94821aa](https://github.com/quantinuum/guppylang/commit/94821aad35e2e690e07cccd8a365a03b472bf6fa)), closes [#916](https://github.com/quantinuum/guppylang/issues/916)
* typo ([#947](https://github.com/quantinuum/guppylang/issues/947)) ([d392ea4](https://github.com/quantinuum/guppylang/commit/d392ea46f8285e97edd9f59708de96bdcf2e4a49))
* Use correct copyable/droppable terminology for type arg errors ([#935](https://github.com/quantinuum/guppylang/issues/935)) ([6a44a1c](https://github.com/quantinuum/guppylang/commit/6a44a1c5d39ed6bc4ae29f8bc4d3a5d06c793c1c)), closes [#867](https://github.com/quantinuum/guppylang/issues/867)

## [0.18.1](https://github.com/quantinuum/guppylang/compare/v0.18.0...v0.18.1) (2025-04-26)


### Features

* Add bytecast ops to builtins ([#913](https://github.com/quantinuum/guppylang/issues/913)) ([d3acd28](https://github.com/quantinuum/guppylang/commit/d3acd28d83f83ceeffe74f9b3573ca06a933ee42)), closes [#782](https://github.com/quantinuum/guppylang/issues/782)
* Array results ([#910](https://github.com/quantinuum/guppylang/issues/910)) ([ebb1f41](https://github.com/quantinuum/guppylang/commit/ebb1f4182656a5ea73fe1c551e45fac7bbdfa9ef)), closes [#631](https://github.com/quantinuum/guppylang/issues/631)
* move qsys_result to hugr package ([#918](https://github.com/quantinuum/guppylang/issues/918)) ([d39b51c](https://github.com/quantinuum/guppylang/commit/d39b51c22384cd7534d9ba97334afa31b434d45a))
* **std:** add array shuffling to rng module ([#925](https://github.com/quantinuum/guppylang/issues/925)) ([3ec74d8](https://github.com/quantinuum/guppylang/commit/3ec74d8c6c3bf178f7c70f50960f2fac2e9e7931))


### Bug Fixes

* add missing compilation for int __rshift__ ([#885](https://github.com/quantinuum/guppylang/issues/885)) ([5cd9225](https://github.com/quantinuum/guppylang/commit/5cd9225250abe4548f0fdc791e81682af6f8a41d)), closes [#886](https://github.com/quantinuum/guppylang/issues/886)
* Allow standalone compilation of pytket functions ([#903](https://github.com/quantinuum/guppylang/issues/903)) ([6416513](https://github.com/quantinuum/guppylang/commit/641651365a7ebf59a7d6861415ab509a19edd477))
* deprecate zz_max and define in terms of zz_phase ([#917](https://github.com/quantinuum/guppylang/issues/917)) ([85f5f6b](https://github.com/quantinuum/guppylang/commit/85f5f6b109ffdc47fda4bf8b3599a5a457fc6df9)), closes [#914](https://github.com/quantinuum/guppylang/issues/914)
* Fix diagnostics spans for dynamically defined notebook functions ([#907](https://github.com/quantinuum/guppylang/issues/907)) ([51b1b81](https://github.com/quantinuum/guppylang/commit/51b1b81c06257e88583d68c245223c891dcc4e32)), closes [#906](https://github.com/quantinuum/guppylang/issues/906)

## [0.18.0](https://github.com/quantinuum/guppylang/compare/v0.17.1...v0.18.0) (2025-03-25)


### ⚠ BREAKING CHANGES

* Lists loaded from `py(...)` expressions are now turned into immutable `frozenarray`s instead of regular `array`s.
* Guppy decorators now return instances of `GuppyDefinition`

### Features

* Add frozenarray type for lists loaded from py expressions ([#868](https://github.com/quantinuum/guppylang/issues/868)) ([e619c78](https://github.com/quantinuum/guppylang/commit/e619c782495b036a567e5c20841d46f5951dcc73))
* Comptime functions ([#727](https://github.com/quantinuum/guppylang/issues/727)) ([f9cc5c5](https://github.com/quantinuum/guppylang/commit/f9cc5c5d2c498b75dba6cb3be1f9b9854ce9bda2)), closes [#751](https://github.com/quantinuum/guppylang/issues/751)

## [0.17.1](https://github.com/quantinuum/guppylang/compare/v0.17.0...v0.17.1) (2025-03-24)


### Features

* add exit function that stops a shot ([#874](https://github.com/quantinuum/guppylang/issues/874)) ([8093940](https://github.com/quantinuum/guppylang/commit/809394011a68b88bec47a330e6d525f7f0075e7f))


### Bug Fixes

* **qsystem:** remove unsupported random_nat and maybe_rng ([635e7ed](https://github.com/quantinuum/guppylang/commit/635e7edf1fab854d0e83111ada09b85f27385377))


### Documentation

* add docstring for `result` ([#879](https://github.com/quantinuum/guppylang/issues/879)) ([8b1e2a1](https://github.com/quantinuum/guppylang/commit/8b1e2a11294d25a2119aec668d26c3171c565ec8))
* add supported range to `exit` docstring ([#878](https://github.com/quantinuum/guppylang/issues/878)) ([83f4730](https://github.com/quantinuum/guppylang/commit/83f4730761895ace578c2d796963ca569e6399c8))

## [0.17.0](https://github.com/quantinuum/guppylang/compare/v0.16.0...v0.17.0) (2025-03-18)


### ⚠ BREAKING CHANGES

* `load_pytket` takes arrays by default (pass `use_arrays=False` for qubit arguments)
* `Option` is now a builtin type.
* `angle.{__mul__, __rmul__, __truediv__, __rtruediv__` now take a `float` instead of an `int`.

### Features

* add `get_current_shot()` to qsystem module ([#806](https://github.com/quantinuum/guppylang/issues/806)) ([3632ec6](https://github.com/quantinuum/guppylang/commit/3632ec606f44ee57d5ce484ca019cc683570156f))
* add `Option.unwrap_nothing()` method ([#829](https://github.com/quantinuum/guppylang/issues/829)) ([abb1aa1](https://github.com/quantinuum/guppylang/commit/abb1aa1707e94cbbce82a74b3d0c388c252483ef)), closes [#810](https://github.com/quantinuum/guppylang/issues/810)
* add barrier operation to builtins ([#849](https://github.com/quantinuum/guppylang/issues/849)) ([cf0bcfb](https://github.com/quantinuum/guppylang/commit/cf0bcfb761cf0a4ff0bab931c49c6d06fb9f4778))
* Allow array arguments to `load_pytket` ([#858](https://github.com/quantinuum/guppylang/issues/858)) ([37b8b80](https://github.com/quantinuum/guppylang/commit/37b8b80db373b87809a0303af24b7dade7161396))
* Allow explicit application of type arguments ([#821](https://github.com/quantinuum/guppylang/issues/821)) ([8f90c04](https://github.com/quantinuum/guppylang/commit/8f90c046ac41597b4b0bfdf118648553f1bd7dae)), closes [#770](https://github.com/quantinuum/guppylang/issues/770)
* Generalise scalar angle operations to float ([#824](https://github.com/quantinuum/guppylang/issues/824)) ([d3f5c7f](https://github.com/quantinuum/guppylang/commit/d3f5c7fa8514537c69293b9b422400f71f9e73b7))
* Implement `float` to `int` and `nat` casts ([#831](https://github.com/quantinuum/guppylang/issues/831)) ([b56d66c](https://github.com/quantinuum/guppylang/commit/b56d66c25ec6889619def8cf4f417fc3bdf19054)), closes [#794](https://github.com/quantinuum/guppylang/issues/794)
* **qsystem:** add Random number generation module ([08fbf47](https://github.com/quantinuum/guppylang/commit/08fbf47230e7484795c7ed284d586170c3b6fa79))
* Switch to improved iterator protocol ([#833](https://github.com/quantinuum/guppylang/issues/833)) ([348dfdc](https://github.com/quantinuum/guppylang/commit/348dfdc38ffd3aed6d0423b7fa0d28e340d95cfd))


### Bug Fixes

* Correctly handle assignments of arrays in control-flow ([#845](https://github.com/quantinuum/guppylang/issues/845)) ([32ded02](https://github.com/quantinuum/guppylang/commit/32ded02c216b3fcad1c0da964f4d15e78c887e62)), closes [#844](https://github.com/quantinuum/guppylang/issues/844)
* Define `len` of arrays using Guppy ([#863](https://github.com/quantinuum/guppylang/issues/863)) ([6868ff6](https://github.com/quantinuum/guppylang/commit/6868ff6b9cc7c7783356bc80aeb5715063b2060a)), closes [#804](https://github.com/quantinuum/guppylang/issues/804)
* Fix array comprehensions with generic element type ([#865](https://github.com/quantinuum/guppylang/issues/865)) ([50df0db](https://github.com/quantinuum/guppylang/commit/50df0db09883326cf077c8fbffbea42a7f6231a8)), closes [#864](https://github.com/quantinuum/guppylang/issues/864)
* Fix compiler diagnostics when calling `check` instead of `compile` ([#854](https://github.com/quantinuum/guppylang/issues/854)) ([9993338](https://github.com/quantinuum/guppylang/commit/9993338f8f14474c91f8dcb3cf9479f6652db00b))
* Fix diagnostic spans for indented code ([#856](https://github.com/quantinuum/guppylang/issues/856)) ([d9fc9fd](https://github.com/quantinuum/guppylang/commit/d9fc9fd01125be2da20d2c622f402b2f41a5dfb5)), closes [#852](https://github.com/quantinuum/guppylang/issues/852)
* Fix error message for conditional shadowing of global variables ([#815](https://github.com/quantinuum/guppylang/issues/815)) ([bdaae11](https://github.com/quantinuum/guppylang/commit/bdaae11c3035d7691a1e2ed2e731f2d8764be49d)), closes [#772](https://github.com/quantinuum/guppylang/issues/772)
* Fix linearity checking for array copies ([#841](https://github.com/quantinuum/guppylang/issues/841)) ([d9b085f](https://github.com/quantinuum/guppylang/commit/d9b085f5dd08e9bc3514b18ede5ecfdb065c760e)), closes [#838](https://github.com/quantinuum/guppylang/issues/838)
* Fix mutation of nested arrays ([#839](https://github.com/quantinuum/guppylang/issues/839)) ([ffb64f9](https://github.com/quantinuum/guppylang/commit/ffb64f95b0fdb3b118c444a90184120eb7864230))
* Fix rendering of line breaks in diagnostics ([#819](https://github.com/quantinuum/guppylang/issues/819)) ([75efd22](https://github.com/quantinuum/guppylang/commit/75efd229fcb11514815bfa971d58e323eaaf68eb)), closes [#818](https://github.com/quantinuum/guppylang/issues/818)
* Prevent reordering of operations with side-effects ([#855](https://github.com/quantinuum/guppylang/issues/855)) ([75eb441](https://github.com/quantinuum/guppylang/commit/75eb4416f8cd19be0cfa7e820e9ee7bdd28571bb))


### Documentation

* Fix API docs build ([#843](https://github.com/quantinuum/guppylang/issues/843)) ([cc1e90c](https://github.com/quantinuum/guppylang/commit/cc1e90c271cc014e7e7fa7392e1a67025753f162))

## [0.16.0](https://github.com/quantinuum/guppylang/compare/v0.15.0...v0.16.0) (2025-02-19)


### ⚠ BREAKING CHANGES

* `CompiledGlobals` renamed to `CompilerContext`

### Features

* add `Option.take()` for swapping with None ([#809](https://github.com/quantinuum/guppylang/issues/809)) ([9a459d5](https://github.com/quantinuum/guppylang/commit/9a459d57e19a7194b30468fa15719f9b9ed4a135))


### Code Refactoring

* Stop inlining array.__getitem__ and array.__setitem__ ([#799](https://github.com/quantinuum/guppylang/issues/799)) ([bb199a0](https://github.com/quantinuum/guppylang/commit/bb199a0d581ead991212a2b7afe45e8f856fd214)), closes [#786](https://github.com/quantinuum/guppylang/issues/786)

## [0.15.0](https://github.com/quantinuum/guppylang/compare/v0.14.0...v0.15.0) (2025-02-07)


### ⚠ BREAKING CHANGES

* classical arrays can no longer be implicitly copied
* `pytket` circuits no longer supported by `py` expressions (use `@pytket` or `load_pytket` instead)

### Features

* add `panic` builtin function ([#757](https://github.com/quantinuum/guppylang/issues/757)) ([4ae3032](https://github.com/quantinuum/guppylang/commit/4ae3032088771166de867c5d8f2f19924d9e0cd3))
* Add array copy method ([#784](https://github.com/quantinuum/guppylang/issues/784)) ([15bae6e](https://github.com/quantinuum/guppylang/commit/15bae6eee6f334485f0a71cf3d58a135f5e533bc))
* add boolean xor support ([#747](https://github.com/quantinuum/guppylang/issues/747)) ([7fa4c8d](https://github.com/quantinuum/guppylang/commit/7fa4c8d6cf94bf19faa618d4d48d023da1484514)), closes [#750](https://github.com/quantinuum/guppylang/issues/750)
* Add CH gate to the stdlib ([#793](https://github.com/quantinuum/guppylang/issues/793)) ([1199a14](https://github.com/quantinuum/guppylang/commit/1199a14a80210dbd9dd61f72c35ca7b846a0ec2e)), closes [#792](https://github.com/quantinuum/guppylang/issues/792)
* Add string type ([#733](https://github.com/quantinuum/guppylang/issues/733)) ([aa9341b](https://github.com/quantinuum/guppylang/commit/aa9341b13c9277756296dd98a86989e23c40e3a8))
* Array subscript assignment for classical arrays ([#776](https://github.com/quantinuum/guppylang/issues/776)) ([6880e11](https://github.com/quantinuum/guppylang/commit/6880e111ebba409f37c16b7b6b77fd08a68bdda8))
* Make `True` and `False` branches unconditional ([#740](https://github.com/quantinuum/guppylang/issues/740)) ([748ea95](https://github.com/quantinuum/guppylang/commit/748ea95cc6df449e29454a9b0a6ab1d56f370e1b))
* Refactor to support affine arrays ([#768](https://github.com/quantinuum/guppylang/issues/768)) ([92ec6d1](https://github.com/quantinuum/guppylang/commit/92ec6d19765fb66f548f818778ec02772abd33f3))
* Remove circuits from `py` expressions ([#746](https://github.com/quantinuum/guppylang/issues/746)) ([ee8926b](https://github.com/quantinuum/guppylang/commit/ee8926bb5f3a6b43aea105f702c0e4ff3202b79b))
* support integer exponentiation in guppy source ([#753](https://github.com/quantinuum/guppylang/issues/753)) ([70c8fcf](https://github.com/quantinuum/guppylang/commit/70c8fcf1cbe009f5938cffc5df2a274cb85eee99))


### Bug Fixes

* Allow string py expressions in result and panic ([#759](https://github.com/quantinuum/guppylang/issues/759)) ([53401cc](https://github.com/quantinuum/guppylang/commit/53401cc9bcc51844a59258e505ece941687ca32f))
* Fix error printing for structs defined in notebooks ([#777](https://github.com/quantinuum/guppylang/issues/777)) ([b41e0fc](https://github.com/quantinuum/guppylang/commit/b41e0fcb4aa37d587800059361605bfae3e783c5))
* Fix pytest hanging ([#754](https://github.com/quantinuum/guppylang/issues/754)) ([9ad02bb](https://github.com/quantinuum/guppylang/commit/9ad02bbb92a5d798398376647a7431669e72d4bc))
* panic on negative exponent in ipow ([#758](https://github.com/quantinuum/guppylang/issues/758)) ([821771a](https://github.com/quantinuum/guppylang/commit/821771a12a3aff93a5f7661211197818f3905b3b))
* Properly report errors for unsupported subscript assignments ([#738](https://github.com/quantinuum/guppylang/issues/738)) ([8afa2a9](https://github.com/quantinuum/guppylang/commit/8afa2a93ae224c57932eb6042464f5722668f742)), closes [#736](https://github.com/quantinuum/guppylang/issues/736)
* remove newlines in extension description ([#762](https://github.com/quantinuum/guppylang/issues/762)) ([2f5eed3](https://github.com/quantinuum/guppylang/commit/2f5eed3f9064ae92d397940a337d6453ab9206ce))


### Documentation

* remove broken link in README ([#801](https://github.com/quantinuum/guppylang/issues/801)) ([fb1c3b5](https://github.com/quantinuum/guppylang/commit/fb1c3b5638de5f3e3869dc6e04d08721c258c4dc))

## [0.14.0](https://github.com/quantinuum/guppylang/compare/v0.13.1...v0.14.0) (2024-12-19)


### ⚠ BREAKING CHANGES

* Lists in `py(...)` expressions are now turned into Guppy arrays instead of lists.
* `dirty_qubit` function removed
* measure_return renamed to `project_z`

### Features

* add `maybe_qubit` stdlib function ([#705](https://github.com/quantinuum/guppylang/issues/705)) ([a49f70e](https://github.com/quantinuum/guppylang/commit/a49f70e15048efc5a30ef34625086b341b278db6)), closes [#627](https://github.com/quantinuum/guppylang/issues/627)
* add measure_array and discard_array quantum function ([#710](https://github.com/quantinuum/guppylang/issues/710)) ([3ad49ff](https://github.com/quantinuum/guppylang/commit/3ad49ff43ceb8f08001bba3edd9e43d32912747a))
* Add method to load pytket circuit without function stub ([#712](https://github.com/quantinuum/guppylang/issues/712)) ([ee1e3de](https://github.com/quantinuum/guppylang/commit/ee1e3defb941e9da29f462afc4c16f3e97147828))
* Add Option type to standard library ([#696](https://github.com/quantinuum/guppylang/issues/696)) ([45ea6b7](https://github.com/quantinuum/guppylang/commit/45ea6b7086f75f017eb4830f55dca9c87d9f599b))
* Allow generic nat args in statically sized ranges ([#706](https://github.com/quantinuum/guppylang/issues/706)) ([f441bb8](https://github.com/quantinuum/guppylang/commit/f441bb8e56e1006acd1fa37c6f3edada5a8fc537)), closes [#663](https://github.com/quantinuum/guppylang/issues/663)
* Array comprehension ([#613](https://github.com/quantinuum/guppylang/issues/613)) ([fdc0526](https://github.com/quantinuum/guppylang/commit/fdc052656c6b62a95d42e0757ea50bd1d0226571)), closes [#614](https://github.com/quantinuum/guppylang/issues/614) [#616](https://github.com/quantinuum/guppylang/issues/616) [#612](https://github.com/quantinuum/guppylang/issues/612)
* Implicit coercion of numeric types ([#702](https://github.com/quantinuum/guppylang/issues/702)) ([df4745b](https://github.com/quantinuum/guppylang/commit/df4745bd9343be777ddb78373db5217f63744e61)), closes [#701](https://github.com/quantinuum/guppylang/issues/701)
* Load `pytket` circuit as a function definition ([#672](https://github.com/quantinuum/guppylang/issues/672)) ([b21b7e1](https://github.com/quantinuum/guppylang/commit/b21b7e132a22363b9c2d69485a3f1f4d127b8129))
* Make arrays iterable ([#632](https://github.com/quantinuum/guppylang/issues/632)) ([07b9871](https://github.com/quantinuum/guppylang/commit/07b987129409bf22d09b80661163f206ffc68f48))
* qsystem std functions with updated primitives ([#679](https://github.com/quantinuum/guppylang/issues/679)) ([b0f041f](https://github.com/quantinuum/guppylang/commit/b0f041f262c4757b5f519d3a28f0c2b2d038f623))
* remove dirty_qubit ([#698](https://github.com/quantinuum/guppylang/issues/698)) ([78e366b](https://github.com/quantinuum/guppylang/commit/78e366b1032afefcdedc6f4b78b30999f0e67d2d))
* Turn py expression lists into arrays ([#697](https://github.com/quantinuum/guppylang/issues/697)) ([d52a00a](https://github.com/quantinuum/guppylang/commit/d52a00ae6f9c33d9fe65ddd46bcf94e39f53172f))
* Unpacking assignment of iterable types with static size ([#688](https://github.com/quantinuum/guppylang/issues/688)) ([602e243](https://github.com/quantinuum/guppylang/commit/602e2434acb07ca5906d867affe9d4fd1a06d59d))
* update to hugr 0.10 and tket2 0.6 ([#725](https://github.com/quantinuum/guppylang/issues/725)) ([63ea7a7](https://github.com/quantinuum/guppylang/commit/63ea7a726edc2512e63b89076db5b4c82bec58af))


### Bug Fixes

* Accept non-negative int literals and py expressions as nats ([#708](https://github.com/quantinuum/guppylang/issues/708)) ([a93d4fe](https://github.com/quantinuum/guppylang/commit/a93d4fe0b07e99bd0537f51a21f9cbf3c0502360)), closes [#704](https://github.com/quantinuum/guppylang/issues/704)
* Allow borrowing inside comprehensions ([#723](https://github.com/quantinuum/guppylang/issues/723)) ([02b6ab0](https://github.com/quantinuum/guppylang/commit/02b6ab00f96a7801199d0ec2d3c017d7d81cdf59)), closes [#719](https://github.com/quantinuum/guppylang/issues/719)
* Detect unsupported default arguments ([#659](https://github.com/quantinuum/guppylang/issues/659)) ([94ac7e3](https://github.com/quantinuum/guppylang/commit/94ac7e38c773e4aac8b809ae27cf7e18342a87cb)), closes [#658](https://github.com/quantinuum/guppylang/issues/658)
* docs build command ([#729](https://github.com/quantinuum/guppylang/issues/729)) ([471b74c](https://github.com/quantinuum/guppylang/commit/471b74c2bf5ca6144d6a5dec71b8a0e4aec57a95))
* Ensure `int`s can be treated as booleans ([#709](https://github.com/quantinuum/guppylang/issues/709)) ([6ef6d60](https://github.com/quantinuum/guppylang/commit/6ef6d608dc8c92c7045575fe579637ca482f3516)), closes [#681](https://github.com/quantinuum/guppylang/issues/681)
* Fix array execution bugs ([#731](https://github.com/quantinuum/guppylang/issues/731)) ([0f6ceaa](https://github.com/quantinuum/guppylang/commit/0f6ceaa58648f105e601298081170eaec5a0e026))
* Fix implicit modules in IPython shells ([#662](https://github.com/quantinuum/guppylang/issues/662)) ([4ecb5f2](https://github.com/quantinuum/guppylang/commit/4ecb5f2fb2dd5b4b9baa5546869c46d42c709017)), closes [#661](https://github.com/quantinuum/guppylang/issues/661)
* Properly report error for unsupported constants ([#724](https://github.com/quantinuum/guppylang/issues/724)) ([d0c2da4](https://github.com/quantinuum/guppylang/commit/d0c2da40cdf1fe4e770123d4174bf710dd44e1a6)), closes [#721](https://github.com/quantinuum/guppylang/issues/721)
* Properly report errors for unsupported expressions ([#692](https://github.com/quantinuum/guppylang/issues/692)) ([7f24264](https://github.com/quantinuum/guppylang/commit/7f24264a56b0b620847a189eeec565f80adbdc3a)), closes [#691](https://github.com/quantinuum/guppylang/issues/691)
* remove use of deprecated Ellipsis ([#699](https://github.com/quantinuum/guppylang/issues/699)) ([b819a84](https://github.com/quantinuum/guppylang/commit/b819a844286cfb17ede045a7cb4f52325a36c63f))


### Documentation

* Fix docs build ([#700](https://github.com/quantinuum/guppylang/issues/700)) ([684f485](https://github.com/quantinuum/guppylang/commit/684f485f98ea4cc4f61040af00fbde0b0c908e45)), closes [#680](https://github.com/quantinuum/guppylang/issues/680)
* fix README.md and quickstart.md ([#654](https://github.com/quantinuum/guppylang/issues/654)) ([abb0221](https://github.com/quantinuum/guppylang/commit/abb0221a46c3dcb069c6e0f08242319d7bb16bad))

## [0.13.1](https://github.com/quantinuum/guppylang/compare/v0.13.0...v0.13.1) (2024-11-15)


### Features

* Generic function definitions ([#618](https://github.com/quantinuum/guppylang/issues/618)) ([7519b90](https://github.com/quantinuum/guppylang/commit/7519b9096a02cf75672313bd0bc90c613e5230ee)), closes [#522](https://github.com/quantinuum/guppylang/issues/522)
* mem_swap function for swapping two inout values ([#653](https://github.com/quantinuum/guppylang/issues/653)) ([89e10a5](https://github.com/quantinuum/guppylang/commit/89e10a5e5c4344badcd0a0a16983c8a3a560ad09))


### Bug Fixes

* Fix generic array functions ([#630](https://github.com/quantinuum/guppylang/issues/630)) ([f4e5655](https://github.com/quantinuum/guppylang/commit/f4e5655e0a85d773ec21fc4a9f7a6c23263dae0a))

## [0.13.0](https://github.com/quantinuum/guppylang/compare/v0.12.2...v0.13.0) (2024-11-12)


### ⚠ BREAKING CHANGES

* `prelude` module renamed to `std`

### Features

* add `qubit` discard/measure methods ([#580](https://github.com/quantinuum/guppylang/issues/580)) ([242fa44](https://github.com/quantinuum/guppylang/commit/242fa44f45e676e81efd5df48de9fc80fe0ea516))
* Add `SizedIter` wrapper type ([#611](https://github.com/quantinuum/guppylang/issues/611)) ([2e9da6b](https://github.com/quantinuum/guppylang/commit/2e9da6be24de499f059c3cdb7553604cb9373ca0))
* conventional results post processing ([#593](https://github.com/quantinuum/guppylang/issues/593)) ([db96224](https://github.com/quantinuum/guppylang/commit/db962243670fea4987ef842c67a59f560f08f72a))
* Improve compiler diagnostics ([#547](https://github.com/quantinuum/guppylang/issues/547)) ([90d465d](https://github.com/quantinuum/guppylang/commit/90d465d87bdde777302381367598812e37c501e7)), closes [#551](https://github.com/quantinuum/guppylang/issues/551) [#553](https://github.com/quantinuum/guppylang/issues/553) [#586](https://github.com/quantinuum/guppylang/issues/586) [#588](https://github.com/quantinuum/guppylang/issues/588) [#587](https://github.com/quantinuum/guppylang/issues/587) [#590](https://github.com/quantinuum/guppylang/issues/590) [#600](https://github.com/quantinuum/guppylang/issues/600) [#601](https://github.com/quantinuum/guppylang/issues/601) [#606](https://github.com/quantinuum/guppylang/issues/606)
* restrict result tag sizes to 256 bytes ([#596](https://github.com/quantinuum/guppylang/issues/596)) ([4e8e00f](https://github.com/quantinuum/guppylang/commit/4e8e00ffe733b1b65055f2355d6a538334449e6d)), closes [#595](https://github.com/quantinuum/guppylang/issues/595)


### Bug Fixes

* Mock guppy decorator during sphinx builds ([#622](https://github.com/quantinuum/guppylang/issues/622)) ([1cccc04](https://github.com/quantinuum/guppylang/commit/1cccc04c54c3c3f38e1e2c1ce828935091e07cad))


### Documentation

* Add DEVELOPMENT.md ([#584](https://github.com/quantinuum/guppylang/issues/584)) ([1d29d39](https://github.com/quantinuum/guppylang/commit/1d29d393206484324835764e89dff7a39c83b3f9))
* Fix docs build ([#639](https://github.com/quantinuum/guppylang/issues/639)) ([bd6011c](https://github.com/quantinuum/guppylang/commit/bd6011cd0e7817fbac24a1b28a8d33ea93c92bef))


### Miscellaneous Chores

* Manually set last release commit ([#643](https://github.com/quantinuum/guppylang/issues/643)) ([b2d569b](https://github.com/quantinuum/guppylang/commit/b2d569b19ac0001841bdd2c326447dbeee40d20c))


### Code Refactoring

* rename prelude to std ([#642](https://github.com/quantinuum/guppylang/issues/642)) ([1a68e8e](https://github.com/quantinuum/guppylang/commit/1a68e8e7919487f1465cc587b9855cb43169f63d))

## [0.12.2](https://github.com/quantinuum/guppylang/compare/v0.12.1...v0.12.2) (2024-10-21)


### Features

* Allow py expressions in type arguments ([#515](https://github.com/quantinuum/guppylang/issues/515)) ([b4fae3f](https://github.com/quantinuum/guppylang/commit/b4fae3f7a29b384f8bbe0069dc6131ec115e17ee))
* remove python python 3 upper bound (support python 3.13) ([#578](https://github.com/quantinuum/guppylang/issues/578)) ([73bb94a](https://github.com/quantinuum/guppylang/commit/73bb94a76731afff7edfce681b556122fef486c7)), closes [#558](https://github.com/quantinuum/guppylang/issues/558)


### Bug Fixes

* Enable len for linear arrays ([#576](https://github.com/quantinuum/guppylang/issues/576)) ([117b68e](https://github.com/quantinuum/guppylang/commit/117b68e6b74221ec85822f721c23c8245e2294fe)), closes [#570](https://github.com/quantinuum/guppylang/issues/570)
* Fix array lowering bugs ([#575](https://github.com/quantinuum/guppylang/issues/575)) ([83b9f31](https://github.com/quantinuum/guppylang/commit/83b9f312e3465d83318feaf0f5a8af6a5ed9fa45))
* Fix printing of generic function parameters ([#516](https://github.com/quantinuum/guppylang/issues/516)) ([5c18ef6](https://github.com/quantinuum/guppylang/commit/5c18ef63237ad76a4b0f74d8b3c4d77a438052ef)), closes [#482](https://github.com/quantinuum/guppylang/issues/482)


## [0.12.1](https://github.com/quantinuum/guppylang/compare/v0.12.0...v0.12.1) (2024-09-23)


### Features

* Add Definition.compile producing Hugr Package ([#504](https://github.com/quantinuum/guppylang/issues/504)) ([d8c8bec](https://github.com/quantinuum/guppylang/commit/d8c8bec33075e015dc12d8142891f566c3249c92))
* Add missing tket2 quantum gates, generalise RotationCompile ([#510](https://github.com/quantinuum/guppylang/issues/510)) ([18d4b4c](https://github.com/quantinuum/guppylang/commit/18d4b4c8b324b0f202e262768617d450745004dc))


### Miscellaneous Chores

* release 0.12.1 ([#512](https://github.com/quantinuum/guppylang/issues/512)) ([b309a94](https://github.com/quantinuum/guppylang/commit/b309a944af3d45a6afbdf6fd253b3b764e36c029))

## [0.12.0](https://github.com/quantinuum/guppylang/compare/v0.11.0...v0.12.0) (2024-09-18)


### ⚠ BREAKING CHANGES

* Pytket circuits loaded via a `py` expression no longer take ownership of the passed qubits.
* Lists and function tensors are no longer available by default. `guppylang.enable_experimental_features()` must be called before compilation to enable them.
* The `GuppyModule` argument is now optional for all decorators and no longer the first positional argument. Removed the explicit module objects `builtins`, `quantum`, and `angle`.
* `quantum_functional` is now its own Guppy module and no longer implicitly comes with `quantum`.
* Linear function arguments are now borrowed by default; removed the now redundant `@inout` annotation

### Features

* Add functions to quantum module and make quantum_functional independent ([#494](https://github.com/quantinuum/guppylang/issues/494)) ([0b0b1af](https://github.com/quantinuum/guppylang/commit/0b0b1afbf5bf481d8fdcbe5050dcf9d5fb85d263))
* Hide lists and function tensors behind experimental flag ([#501](https://github.com/quantinuum/guppylang/issues/501)) ([c867f48](https://github.com/quantinuum/guppylang/commit/c867f48d6dc555454db69943f0b420cb53676d3d))
* Make linear types [@inout](https://github.com/inout) by default; add [@owned](https://github.com/owned) annotation ([#486](https://github.com/quantinuum/guppylang/issues/486)) ([e900c96](https://github.com/quantinuum/guppylang/commit/e900c96eb3755ad5d4304eb721e791b8185c8f09))
* Only lower definitions to Hugr if they are used ([#496](https://github.com/quantinuum/guppylang/issues/496)) ([cc2c8a4](https://github.com/quantinuum/guppylang/commit/cc2c8a4f09f43f8913c49ff0dfe0da601a85b7c6))
* Support implicit modules for all decorators and turn builtins into implicit module ([#476](https://github.com/quantinuum/guppylang/issues/476)) ([cc8a424](https://github.com/quantinuum/guppylang/commit/cc8a424ad9a8b8c3c5a3b5cc700ccdb7a5ff8fa9))
* Use inout for pytket circuits ([#500](https://github.com/quantinuum/guppylang/issues/500)) ([a980ec2](https://github.com/quantinuum/guppylang/commit/a980ec2c89e2ebecb16b0ea12750ecf6781f3ee3))


### Bug Fixes

* `angle` is now a struct and emitted as a rotation  ([#485](https://github.com/quantinuum/guppylang/issues/485)) ([992b138](https://github.com/quantinuum/guppylang/commit/992b138a312dace5a6f846e99013a0a0bcfe74e6))
* Evade false positives for inout variable usage ([#493](https://github.com/quantinuum/guppylang/issues/493)) ([6fdb5d6](https://github.com/quantinuum/guppylang/commit/6fdb5d6ff1fb4c2e4db89f885480fbe818fd32a0))
* Fix redefinition of structs ([#499](https://github.com/quantinuum/guppylang/issues/499)) ([0b156e9](https://github.com/quantinuum/guppylang/commit/0b156e9f9894b45fc2ca6c566e496d9242634434))
* Initialise _checked in GuppyModule ([#491](https://github.com/quantinuum/guppylang/issues/491)) ([3dd5dd3](https://github.com/quantinuum/guppylang/commit/3dd5dd3797f1da8b1bd0acdee692d1d5e8a19d98)), closes [#489](https://github.com/quantinuum/guppylang/issues/489)
* use correct array ops ([#503](https://github.com/quantinuum/guppylang/issues/503)) ([720d8b8](https://github.com/quantinuum/guppylang/commit/720d8b814bbd3f76e788cedc4db4cef96ff24160))

## [0.11.0](https://github.com/quantinuum/guppylang/compare/v0.10.0...v0.11.0) (2024-09-11)


### ⚠ BREAKING CHANGES

* `guppy.take_module` renamed to `guppy.get_module` and no longer removes the module from the state.
* Quantum operations `rx`, `rz`, `phased_x`, and `zz_max` use the `angle` type instead of floats.

### Features

* Add implicit importing of modules ([#461](https://github.com/quantinuum/guppylang/issues/461)) ([1b73032](https://github.com/quantinuum/guppylang/commit/1b730320d6f6b7d6a1062f5322ccec0cd888380f))
* Use angle type in quantum operations ([#467](https://github.com/quantinuum/guppylang/issues/467)) ([ce0f746](https://github.com/quantinuum/guppylang/commit/ce0f746dfe6702c68a850380ef8965e58f666354))


### Bug Fixes

* hseries ops use floats instead of angles ([#483](https://github.com/quantinuum/guppylang/issues/483)) ([7ed3853](https://github.com/quantinuum/guppylang/commit/7ed38531bed8dba65859c2185858bee5bb22a000)), closes [#477](https://github.com/quantinuum/guppylang/issues/477)
* Keep track of definitions that are implicitly imported ([#481](https://github.com/quantinuum/guppylang/issues/481)) ([a89f225](https://github.com/quantinuum/guppylang/commit/a89f2251eb753803c2e67aee4bd21ae40f83a5ba)), closes [#480](https://github.com/quantinuum/guppylang/issues/480)

## [0.10.0](https://github.com/quantinuum/guppylang/compare/v0.9.0...v0.10.0) (2024-09-11)


### ⚠ BREAKING CHANGES

* Bumped the `hugr` dependency to `0.8.0`
* `GuppyModule.load` no longer loads the content of modules but instead just brings the name of the module into scope. Use `GuppyModule.load_all` to get the old behaviour.
* Removed `guppylang.hugr_builder.hugr.Hugr`, compiling a module returns a `hugr.Package` instead.

### Features

* Add `__version__` field to guppylang ([#473](https://github.com/quantinuum/guppylang/issues/473)) ([b996c62](https://github.com/quantinuum/guppylang/commit/b996c62a5f1f5d643fb9a2be893911f6021dd0e9))
* Add angle type ([#449](https://github.com/quantinuum/guppylang/issues/449)) ([12e41e0](https://github.com/quantinuum/guppylang/commit/12e41e02354a504b8a527a48b6df8f2ed51891df))
* Add array literals ([#446](https://github.com/quantinuum/guppylang/issues/446)) ([a255c02](https://github.com/quantinuum/guppylang/commit/a255c02f7e1c525b7534f5b08a5c3d6f1fb79392))
* Add equality test for booleans ([#394](https://github.com/quantinuum/guppylang/issues/394)) ([dd702ce](https://github.com/quantinuum/guppylang/commit/dd702ce5e5e5f363b3a31e0075690703f2fe6d29)), closes [#363](https://github.com/quantinuum/guppylang/issues/363)
* Add pi constant ([#451](https://github.com/quantinuum/guppylang/issues/451)) ([9d35a78](https://github.com/quantinuum/guppylang/commit/9d35a78b784ba0c00bcdf3d2a1256606fb797644))
* Add qualified imports and make them the default ([#443](https://github.com/quantinuum/guppylang/issues/443)) ([553ec51](https://github.com/quantinuum/guppylang/commit/553ec51d071ed6f195322685590335fa1712c4a7))
* Allow calling of methods ([#440](https://github.com/quantinuum/guppylang/issues/440)) ([5a59da3](https://github.com/quantinuum/guppylang/commit/5a59da359ee7a098ce069db5cdebd5eb98ec9781))
* Allow imports of function definitions and aliased imports ([#432](https://github.com/quantinuum/guppylang/issues/432)) ([e23b666](https://github.com/quantinuum/guppylang/commit/e23b6668ef0716f7dabb91be73a217c11ca32ecc))
* Array indexing ([#415](https://github.com/quantinuum/guppylang/issues/415)) ([2199b48](https://github.com/quantinuum/guppylang/commit/2199b48d777c28cf5584f537d78360d15d4c924b)), closes [#421](https://github.com/quantinuum/guppylang/issues/421) [#422](https://github.com/quantinuum/guppylang/issues/422) [#447](https://github.com/quantinuum/guppylang/issues/447)
* Inout arguments ([#311](https://github.com/quantinuum/guppylang/issues/311)) ([060649b](https://github.com/quantinuum/guppylang/commit/060649b8e1249489dd5851e0a8578ab715e093ce)), closes [#315](https://github.com/quantinuum/guppylang/issues/315) [#316](https://github.com/quantinuum/guppylang/issues/316) [#349](https://github.com/quantinuum/guppylang/issues/349) [#344](https://github.com/quantinuum/guppylang/issues/344) [#321](https://github.com/quantinuum/guppylang/issues/321) [#331](https://github.com/quantinuum/guppylang/issues/331) [#350](https://github.com/quantinuum/guppylang/issues/350) [#340](https://github.com/quantinuum/guppylang/issues/340) [#351](https://github.com/quantinuum/guppylang/issues/351)
* range() with single-argument ([#452](https://github.com/quantinuum/guppylang/issues/452)) ([d05f369](https://github.com/quantinuum/guppylang/commit/d05f369041edbb10772117161d3a74414769361d))
* Skip checking of redefined functions ([#457](https://github.com/quantinuum/guppylang/issues/457)) ([7f9ad32](https://github.com/quantinuum/guppylang/commit/7f9ad32906e909c552025063c062d8b79d43325a))
* Support `nat`/`int` ↔ `bool` cast operations ([#459](https://github.com/quantinuum/guppylang/issues/459)) ([3b778c3](https://github.com/quantinuum/guppylang/commit/3b778c3649b8c54b29faa907e3fd95e9ae87e5bd))
* Use `hugr-cli` for validation ([#455](https://github.com/quantinuum/guppylang/issues/455)) ([1d0667b](https://github.com/quantinuum/guppylang/commit/1d0667bc06998a6682352b46758f5465ef4ae22c))
* Use cell name instead of file for notebook errors ([#382](https://github.com/quantinuum/guppylang/issues/382)) ([d542601](https://github.com/quantinuum/guppylang/commit/d5426017320efba8ed8cf2024c37a0b64b0cdce9))
* Use the hugr builder ([536abf9](https://github.com/quantinuum/guppylang/commit/536abf9ff82899332c960695da9e620bbdbf3d8b))


### Bug Fixes

* Fix and update demo notebook ([#376](https://github.com/quantinuum/guppylang/issues/376)) ([23b2a15](https://github.com/quantinuum/guppylang/commit/23b2a1559271ce36a348384616603bef67c73992))
* Fix linearity checking bug ([#441](https://github.com/quantinuum/guppylang/issues/441)) ([0b8ea21](https://github.com/quantinuum/guppylang/commit/0b8ea21763fd3611a2b5ec2a978b14954d5a9582))
* Fix struct definitions in notebooks ([#374](https://github.com/quantinuum/guppylang/issues/374)) ([b009465](https://github.com/quantinuum/guppylang/commit/b009465d8221bb22576bfb079d05b01e1872d500))


### Documentation

* Update readme, `cargo build` instead of  `--extra validation` ([#471](https://github.com/quantinuum/guppylang/issues/471)) ([c2a4c86](https://github.com/quantinuum/guppylang/commit/c2a4c86a81378447ecaa64ba5090da22971d7303))


### Miscellaneous Chores

* Update hugr to `0.8.0` ([#454](https://github.com/quantinuum/guppylang/issues/454)) ([b02e0d0](https://github.com/quantinuum/guppylang/commit/b02e0d017e60469051ddfc84c8cd28003a40286d))

## [0.9.0](https://github.com/quantinuum/guppylang/compare/v0.8.1...v0.9.0) (2024-08-12)


### ⚠ BREAKING CHANGES

*

### Bug Fixes

* Use latest results extension spec ([#370](https://github.com/quantinuum/guppylang/issues/370)) ([d9cc8d2](https://github.com/quantinuum/guppylang/commit/d9cc8d29cce4178c44d00e444d29f7c30fafb7a3))

## [0.8.1](https://github.com/quantinuum/guppylang/compare/v0.8.0...v0.8.1) (2024-08-08)


### Bug Fixes

* Fix invalid result operation name ([#367](https://github.com/quantinuum/guppylang/issues/367)) ([568624d](https://github.com/quantinuum/guppylang/commit/568624d1ccd70dc78c16f4ca2170dc167791ea64))
* Linearity checking bug ([#355](https://github.com/quantinuum/guppylang/issues/355)) ([e14660f](https://github.com/quantinuum/guppylang/commit/e14660f2b31d104c7fb0b5cb8806c3656098afbb))

## [0.8.0](https://github.com/quantinuum/guppylang/compare/v0.7.0...v0.8.0) (2024-07-30)


### Features

* Parse docstrings for functions ([#334](https://github.com/quantinuum/guppylang/issues/334)) ([a7cc97a](https://github.com/quantinuum/guppylang/commit/a7cc97a6c1af674972c3a37e28ef7e33ddf6fa3d))


### Bug Fixes

* Use places in BB signatures for Hugr generation ([#342](https://github.com/quantinuum/guppylang/issues/342)) ([48b0e35](https://github.com/quantinuum/guppylang/commit/48b0e352d835298b66ea90ff12528391c1c0e2a3))

## [0.7.0](https://github.com/quantinuum/guppylang/compare/v0.6.2...v0.7.0) (2024-07-25)


### ⚠ BREAKING CHANGES

* `qubit`s are now reset on allocation

### Features

* `qubit`s are now reset on allocation, and `dirty_qubit` added ([#325](https://github.com/quantinuum/guppylang/issues/325)) ([4a9e205](https://github.com/quantinuum/guppylang/commit/4a9e20529a4d0859f010fad62ba06f62ca1c98ce))
* Allow access to struct fields and mutation of linear ones ([#295](https://github.com/quantinuum/guppylang/issues/295)) ([6698b75](https://github.com/quantinuum/guppylang/commit/6698b75b01421cd1fa545219786266fb0c1da05b)), closes [#293](https://github.com/quantinuum/guppylang/issues/293)
* Allow redefinition of names in guppy modules ([#326](https://github.com/quantinuum/guppylang/issues/326)) ([314409c](https://github.com/quantinuum/guppylang/commit/314409cd63b544d0fdbf16db66201b08dead81fe)), closes [#307](https://github.com/quantinuum/guppylang/issues/307)


### Bug Fixes

* Use correct hook for error printing inside jupyter notebooks ([#324](https://github.com/quantinuum/guppylang/issues/324)) ([bfdb003](https://github.com/quantinuum/guppylang/commit/bfdb003d454d3d8fb6385c2c758dab56ab622496)), closes [#323](https://github.com/quantinuum/guppylang/issues/323)

## [0.6.2](https://github.com/quantinuum/guppylang/compare/v0.6.1...v0.6.2) (2024-07-10)


### Features

* update to hugr-python 0.4  ([af770c3](https://github.com/quantinuum/guppylang/commit/af770c31536a59c32fd8229579455a309e90058e))

## [0.6.1](https://github.com/quantinuum/guppylang/compare/v0.6.0...v0.6.1) (2024-07-09)


### Features

* update to `hugr-py 0.3` ([3da3936](https://github.com/quantinuum/guppylang/commit/3da393674de7d03dd0d5d5b8239dd8968d16c4c4))

## [0.6.0](https://github.com/quantinuum/guppylang/compare/v0.5.2...v0.6.0) (2024-07-02)


### Features

* Add array type ([#258](https://github.com/quantinuum/guppylang/issues/258)) ([041c621](https://github.com/quantinuum/guppylang/commit/041c621a0481f14ee517b0356e0ebb9cae6ddc2e))
* Add nat type ([#254](https://github.com/quantinuum/guppylang/issues/254)) ([a461a9d](https://github.com/quantinuum/guppylang/commit/a461a9d5556d7ed68da5a722100c8b3fb449b25e))
* Add result function ([#271](https://github.com/quantinuum/guppylang/issues/271)) ([792fb87](https://github.com/quantinuum/guppylang/commit/792fb871cac5b19905e87dd485e11d7488f2fb87)), closes [#270](https://github.com/quantinuum/guppylang/issues/270)
* Allow constant nats as type args ([#255](https://github.com/quantinuum/guppylang/issues/255)) ([d706735](https://github.com/quantinuum/guppylang/commit/d7067356c71cbcc5352e69ea4eed6bdc1d0c1ec8))
* Generate constructor methods for structs ([#262](https://github.com/quantinuum/guppylang/issues/262)) ([f68d0af](https://github.com/quantinuum/guppylang/commit/f68d0afe74c75e40b49babe26091a24d822218f7)), closes [#261](https://github.com/quantinuum/guppylang/issues/261)
* Return already-compiled hugrs from `GuppyModule.compile` ([#247](https://github.com/quantinuum/guppylang/issues/247)) ([9d01eae](https://github.com/quantinuum/guppylang/commit/9d01eae8e4db21a95ad3e97d4e78fea7b4b32c08))
* Turn int and float into core types ([#225](https://github.com/quantinuum/guppylang/issues/225)) ([99217dc](https://github.com/quantinuum/guppylang/commit/99217dcddb16fa7c713b7e5c5d356715a0fc9496))


### Bug Fixes

* Add missing test file ([#266](https://github.com/quantinuum/guppylang/issues/266)) ([75231fe](https://github.com/quantinuum/guppylang/commit/75231fe509c52945d44eadb2aa238d1eecf01b0c))
* Loading custom polymorphic function defs as values ([#260](https://github.com/quantinuum/guppylang/issues/260)) ([d15b2f5](https://github.com/quantinuum/guppylang/commit/d15b2f5a2c012924436ecd3ab482099654a1752e)), closes [#259](https://github.com/quantinuum/guppylang/issues/259)

## [0.5.2](https://github.com/quantinuum/guppylang/compare/v0.5.1...v0.5.2) (2024-06-13)


### Bug Fixes

* Don't reorder inputs of entry BB ([#243](https://github.com/quantinuum/guppylang/issues/243)) ([ad56b99](https://github.com/quantinuum/guppylang/commit/ad56b991c03e1bc52690e41450521e7fe9100268))

## [0.5.1](https://github.com/quantinuum/guppylang/compare/v0.5.0...v0.5.1) (2024-06-12)


### Bug Fixes

* Serialisation of bool values ([#239](https://github.com/quantinuum/guppylang/issues/239)) ([16a77db](https://github.com/quantinuum/guppylang/commit/16a77dbd4c5905eff6c4ddabe66b5ef1b8a7e15b))

## [0.5.0](https://github.com/quantinuum/guppylang/compare/v0.4.0...v0.5.0) (2024-06-10)


### Features

* Add extern symbols ([#236](https://github.com/quantinuum/guppylang/issues/236)) ([977ccd8](https://github.com/quantinuum/guppylang/commit/977ccd831a3df1bdf49582309bce065a865d3e31))

## [0.4.0](https://github.com/quantinuum/guppylang/compare/v0.3.0...v0.4.0) (2024-05-30)


### Features

* Export py function ([6dca95d](https://github.com/quantinuum/guppylang/commit/6dca95deda3cc5bd103df104e33991c9adce2be2))

## [0.3.0](https://github.com/quantinuum/guppylang/compare/v0.2.0...v0.3.0) (2024-05-22)


### Features

* Add a unified definition system ([#179](https://github.com/quantinuum/guppylang/issues/179)) ([ae71932](https://github.com/quantinuum/guppylang/commit/ae71932a608ed5034c060972eb70265ae2dec88c))
* Add struct types ([#207](https://github.com/quantinuum/guppylang/issues/207)) ([f7adb85](https://github.com/quantinuum/guppylang/commit/f7adb85bfbc7498047471cdf6b232c6b5056e19e))
* Allow calling a tensor of functions ([#196](https://github.com/quantinuum/guppylang/issues/196)) ([af4fb07](https://github.com/quantinuum/guppylang/commit/af4fb07e4613c8ab5948a681ba336f1f49a49495))
* Upgrade Hugr and start using the shared Pydantic model ([#201](https://github.com/quantinuum/guppylang/issues/201)) ([bd7e67a](https://github.com/quantinuum/guppylang/commit/bd7e67a59df3c6a8eede15c8a62f4f555d539c9a))


### Bug Fixes

* Consider type when deciding whether to pack up returns ([#212](https://github.com/quantinuum/guppylang/issues/212)) ([4f24a07](https://github.com/quantinuum/guppylang/commit/4f24a071d3c0b475920141fc5847474f0621b703))
* Mypy tket2 error ([#220](https://github.com/quantinuum/guppylang/issues/220)) ([7ad3908](https://github.com/quantinuum/guppylang/commit/7ad3908e2bb2672028df3eaa2cd78883020e144f))
* Only use path when determining equality of implicit modules ([#216](https://github.com/quantinuum/guppylang/issues/216)) ([6f47d4b](https://github.com/quantinuum/guppylang/commit/6f47d4bce55115c6b82d86007f75f40d46796b24))
* Serialisation of float values ([#219](https://github.com/quantinuum/guppylang/issues/219)) ([937260a](https://github.com/quantinuum/guppylang/commit/937260af694fbbd5bd217f23d20f13ee4759757c)), closes [#218](https://github.com/quantinuum/guppylang/issues/218)


### Documentation

* Add compiler API docs ([#194](https://github.com/quantinuum/guppylang/issues/194)) ([c3dd9bd](https://github.com/quantinuum/guppylang/commit/c3dd9bdf19cbfeb23b792376f2fedf8f4f4dbeaf))
* Add pypi and python version badges to the README ([#192](https://github.com/quantinuum/guppylang/issues/192)) ([7fecc45](https://github.com/quantinuum/guppylang/commit/7fecc45f3fce8489872dbe65c6012f7cd0b8dc61))

## 0.2.0 (2024-04-11)


### ⚠ BREAKING CHANGES

* Make `qubit` type lower case ([#165](https://github.com/quantinuum/guppylang/issues/165))

### Features

* Local implicit modules for `@guppy` ([#105](https://github.com/quantinuum/guppylang/issues/105)) ([f52a5de](https://github.com/quantinuum/guppylang/commit/f52a5de95972d028167f5800d16573c178c9e2be))
* New type representation with parameters ([#174](https://github.com/quantinuum/guppylang/issues/174)) ([73e29f2](https://github.com/quantinuum/guppylang/commit/73e29f25ec90b8dfcc6517b961d6d1d13f694cb6))


### Bug Fixes

* Make ZZMax a dyadic operation ([#168](https://github.com/quantinuum/guppylang/issues/168)) ([152485f](https://github.com/quantinuum/guppylang/commit/152485f08ef61c3450da1e8b03eee883558a6871)), closes [#154](https://github.com/quantinuum/guppylang/issues/154)
* Stop exiting interpreter on error ([#140](https://github.com/quantinuum/guppylang/issues/140)) ([728e449](https://github.com/quantinuum/guppylang/commit/728e44921f20b227ed92f89daae513798701ef62))
* Use correct TK2 gate names ([#190](https://github.com/quantinuum/guppylang/issues/190)) ([df92642](https://github.com/quantinuum/guppylang/commit/df92642c35b977c0d318747ac1d4011061d6e171))


### Documentation

* add reference to runner to readme ([#129](https://github.com/quantinuum/guppylang/issues/129)) ([45c2bf0](https://github.com/quantinuum/guppylang/commit/45c2bf010a719785527e1c5cc2ac650975e84d4d))
* Add short description and simplify readme for pypi ([#136](https://github.com/quantinuum/guppylang/issues/136)) ([667bba3](https://github.com/quantinuum/guppylang/commit/667bba380e7bd38d2e1c66e8e6b67dfbba4efa05))


### Code Refactoring

* Make `qubit` type lower case ([#165](https://github.com/quantinuum/guppylang/issues/165)) ([0a42097](https://github.com/quantinuum/guppylang/commit/0a42097f617a231a7c6a3096b5d12bda6b19e0aa))


### Continuous Integration

* Use `release-please bootstrap`'s default config ([#187](https://github.com/quantinuum/guppylang/issues/187)) ([72e666a](https://github.com/quantinuum/guppylang/commit/72e666af5a52c44a4094080a665342422a242d2b))

## [0.1.0](https://github.com/quantinuum/guppy/releases/tag/v0.1.0)

First release of Guppy! 🐟

This is an alpha release that implements basic language features and compilation to hugr v0.1.
