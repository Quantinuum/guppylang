from abc import ABC

from hugr import Wire, ops
from hugr import tys as ht

from guppylang_internals.definition.custom import (
    CustomCallCompiler,
    CustomInoutCallCompiler,
)
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.std._internal.compiler.prelude import (
    build_expect_none,
    build_unwrap,
)
from guppylang_internals.std._internal.compiler.tket_bool import (
    OPAQUE_FALSE,
    OPAQUE_TRUE,
)
from guppylang_internals.tys.arg import TypeArg


class OptionCompiler(CustomInoutCallCompiler, ABC):
    """Abstract base class for compilers for `Option` methods."""

    @property
    def option_ty(self) -> ht.Option:
        match self.type_args:
            case [TypeArg(ty)]:
                return ht.Option(ty.to_hugr(self.ctx))
            case _:
                raise InternalGuppyError("Invalid type args for Option op")


class OptionConstructor(OptionCompiler, CustomCallCompiler):
    """Compiler for the `Option` constructors `nothing` and `some`."""

    def __init__(self, tag: int):
        self.tag = tag

    def compile(self, args: list[Wire]) -> list[Wire]:
        return [self.builder.add_op(ops.Tag(self.tag, self.option_ty), *args)]


class OptionTestCompiler(OptionCompiler):
    """Compiler for the `Option.is_nothing` and `Option.is_some` methods."""

    def __init__(self, tag: int):
        self.tag = tag

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [opt] = args
        cond = self.builder.add_conditional(opt)
        for i in [0, 1]:
            with cond.add_case(i) as case:
                val = OPAQUE_TRUE if i == self.tag else OPAQUE_FALSE
                opt = case.add_op(ops.Tag(i, self.option_ty), *case.inputs())
                case.set_outputs(case.load(val), opt)
        [res, opt] = cond.outputs()
        return CallReturnWires(regular_returns=[res], inout_returns=[opt])


class OptionUnwrapCompiler(OptionCompiler, CustomCallCompiler):
    """Compiler for the `Option.unwrap` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        [opt] = args
        err = "Option.unwrap: value is `Nothing`"
        return list(build_unwrap(self.builder, opt, err).outputs())


class OptionUnwrapNothingCompiler(OptionCompiler, CustomCallCompiler):
    """Compiler for the `Option.unwrap_nothing` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        [opt] = args
        err = "Option.unwrap: value is `Some`"
        return list(build_expect_none(self.builder, opt, err).outputs())
