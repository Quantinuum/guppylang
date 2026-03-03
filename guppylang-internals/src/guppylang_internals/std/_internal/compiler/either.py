from abc import ABC
from collections.abc import Sequence

from hugr import Wire, ops
from hugr import tys as ht

from guppylang_internals.ast_util import get_type
from guppylang_internals.compiler.expr_compiler import pack_returns, unpack_wire
from guppylang_internals.definition.custom import (
    CustomCallCompiler,
    CustomInoutCallCompiler,
)
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.std._internal.compiler.prelude import (
    build_unwrap_left,
    build_unwrap_right,
)
from guppylang_internals.std._internal.compiler.tket_bool import (
    OPAQUE_FALSE,
    OPAQUE_TRUE,
)
from guppylang_internals.tys.arg import Argument, TypeArg
from guppylang_internals.tys.common import ToHugrContext
from guppylang_internals.tys.ty import type_to_row


def either_to_hugr(type_args: Sequence[Argument], ctx: ToHugrContext) -> ht.Either:
    match type_args:
        case [TypeArg(left_ty), TypeArg(right_ty)]:
            left_tys = [ty.to_hugr(ctx) for ty in type_to_row(left_ty)]
            right_tys = [ty.to_hugr(ctx) for ty in type_to_row(right_ty)]
            return ht.Either(left_tys, right_tys)
        case _:
            raise InternalGuppyError("Invalid type args for Either type")


class EitherCompiler(CustomInoutCallCompiler, ABC):
    """Abstract base class for compilers for `Either` methods."""

    @property
    def left_tys(self) -> list[ht.Type]:
        match self.type_args:
            case [TypeArg(left_ty), TypeArg()]:
                return [ty.to_hugr(self.ctx) for ty in type_to_row(left_ty)]
            case _:
                raise InternalGuppyError("Invalid type args for Either op")

    @property
    def right_tys(self) -> list[ht.Type]:
        match self.type_args:
            case [TypeArg(), TypeArg(right_ty)]:
                return [ty.to_hugr(self.ctx) for ty in type_to_row(right_ty)]
            case _:
                raise InternalGuppyError("Invalid type args for Either op")

    @property
    def either_ty(self) -> ht.Either:
        return either_to_hugr(self.type_args, self.ctx)


class EitherConstructor(EitherCompiler, CustomCallCompiler):
    """Compiler for the `Option` constructors `nothing` and `some`."""

    def __init__(self, tag: int):
        self.tag = tag

    def compile(self, args: list[Wire]) -> list[Wire]:
        ty = self.either_ty
        if self.tag == 1:
            # In the `right` case, the type args are swapped around since `R` occurs
            # first in the signature :(
            ty.variant_rows = [ty.variant_rows[1], ty.variant_rows[0]]
        # For the same reason, the type of the input corresponds to the first type
        # variable
        inp_arg = self.type_args[0]
        assert isinstance(inp_arg, TypeArg)
        [inp] = args
        # Unpack the single input into a row
        inp_row = unpack_wire(inp, inp_arg.ty, self.builder, self.ctx)
        return [self.builder.add_op(ops.Tag(self.tag, ty), *inp_row)]


class EitherTestCompiler(EitherCompiler):
    """Compiler for the `Either.is_left` and `Either.is_right` methods."""

    def __init__(self, tag: int):
        self.tag = tag

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [either] = args
        cond = self.builder.add_conditional(either)
        for i in [0, 1]:
            with cond.add_case(i) as case:
                val = OPAQUE_TRUE if i == self.tag else OPAQUE_FALSE
                either = case.add_op(ops.Tag(i, self.either_ty), *case.inputs())
                case.set_outputs(case.load(val), either)
        [res, either] = cond.outputs()
        return CallReturnWires(regular_returns=[res], inout_returns=[either])


class EitherToOptionCompiler(EitherCompiler, CustomCallCompiler):
    """Compiler for the `Either.left` and `Either.right` methods."""

    def __init__(self, tag: int):
        self.tag = tag

    def compile(self, args: list[Wire]) -> list[Wire]:
        [either] = args
        cond = self.builder.add_conditional(either)
        target_tys = self.left_tys if self.tag == 0 else self.right_tys
        for i in [0, 1]:
            with cond.add_case(i) as case:
                if i == self.tag:
                    out = case.add_op(
                        ops.Tag(1, ht.Option(*target_tys)), *case.inputs()
                    )
                else:
                    out = case.add_op(ops.Tag(0, ht.Option(*target_tys)))
                case.set_outputs(out)
        return list(cond.outputs())


class EitherUnwrapCompiler(EitherCompiler, CustomCallCompiler):
    """Compiler for the `Either.unwrap_left` and `Either.unwrap_right` methods."""

    def __init__(self, tag: int):
        self.tag = tag

    def compile(self, args: list[Wire]) -> list[Wire]:
        [either] = args
        if self.tag == 0:
            out = build_unwrap_left(
                self.builder, either, "Either.unwrap_left: value is `right`"
            )
        else:
            out = build_unwrap_right(
                self.builder, either, "Either.unwrap_right: value is `left`"
            )
        # Pack outputs into a single wire. We're not allowed to return a row since the
        # signature has a generic return type (also see `TupleType.preserve`)
        return_ty = get_type(self.node)
        return [pack_returns(list(out), return_ty, self.builder, self.ctx)]
