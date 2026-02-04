"""A hugr extension with guppy-specific operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import hugr.ext as he
import hugr.tys as ht
from hugr import ops

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

EXTENSION: he.Extension = he.Extension("guppylang", he.Version(0, 1, 0))


PARTIAL_OP_DEF: he.OpDef = EXTENSION.add_op_def(
    he.OpDef(
        "partial",
        signature=he.OpDefSig(
            poly_func=ht.PolyFuncType(
                params=[
                    # Captured input types
                    ht.ListParam(ht.TypeTypeParam(ht.TypeBound.Linear)),
                    # Non-captured input types
                    ht.ListParam(ht.TypeTypeParam(ht.TypeBound.Linear)),
                    # Output types
                    ht.ListParam(ht.TypeTypeParam(ht.TypeBound.Linear)),
                ],
                body=ht.FunctionType(
                    input=[
                        ht.FunctionType(
                            input=[
                                ht.RowVariable(0, ht.TypeBound.Linear),
                                ht.RowVariable(1, ht.TypeBound.Linear),
                            ],
                            output=[ht.RowVariable(2, ht.TypeBound.Linear)],
                        ),
                        ht.RowVariable(0, ht.TypeBound.Linear),
                    ],
                    output=[
                        ht.FunctionType(
                            input=[ht.RowVariable(1, ht.TypeBound.Linear)],
                            output=[ht.RowVariable(2, ht.TypeBound.Linear)],
                        ),
                    ],
                ),
            )
        ),
        description="A partial application of a function."
        " Given arguments [*a],[*b],[*c], represents an operation with type"
        " `(*c, *a -> *b), *c -> (*a -> *b)`",
    )
)


@dataclass
class PartialOp(ops.AsExtOp):
    """An operation that partially evaluates a function.

    args:
        captured_inputs: A list of input types `c_0, ..., c_k` to partially apply.
        other_inputs: A list of input types `a_0, ..., a_n` not partially applied.
        outputs: The output types `b_0, ..., b_m` of the partially applied function.

    returns:
        An operation with type
            ` (c_0, ..., c_k, a_0, ..., a_n -> b_0, ..., b_m ), c_0, ..., c_k`
            `-> (a_0, ..., a_n -> b_0, ..., b_m)`
    """

    captured_inputs: list[ht.Type]
    other_inputs: list[ht.Type]
    outputs: list[ht.Type]

    @classmethod
    def from_closure(
        cls, closure_ty: ht.FunctionType, captured_tys: Sequence[ht.Type]
    ) -> PartialOp:
        """An operation that partially evaluates a function.

        args:
            closure_ty: A function `(c_0, ..., c_k, a_0, ..., a_n) -> b_0, ..., b_m`
            captured_tys: A list `c_0, ..., c_k` of types captured by the function

        returns:
            An operation with type
                ` (c_0, ..., c_k, a_0, ..., a_n -> b_0, ..., b_m ), c_0, ..., c_k`
                `-> (a_0, ..., a_n -> b_0, ..., b_m)`
        """
        assert len(closure_ty.input) >= len(captured_tys)
        assert captured_tys == closure_ty.input[: len(captured_tys)]

        other_inputs = closure_ty.input[len(captured_tys) :]
        return cls(
            captured_inputs=list(captured_tys),
            other_inputs=list(other_inputs),
            outputs=list(closure_ty.output),
        )

    def op_def(self) -> he.OpDef:
        return PARTIAL_OP_DEF

    def type_args(self) -> list[ht.TypeArg]:
        captured_args: list[ht.TypeArg] = [
            ht.TypeTypeArg(ty) for ty in self.captured_inputs
        ]
        other_args: list[ht.TypeArg] = [ht.TypeTypeArg(ty) for ty in self.other_inputs]
        output_args: list[ht.TypeArg] = [ht.TypeTypeArg(ty) for ty in self.outputs]
        return [
            ht.ListArg(captured_args),
            ht.ListArg(other_args),
            ht.ListArg(output_args),
        ]

    def cached_signature(self) -> ht.FunctionType | None:
        closure_ty = ht.FunctionType(
            [*self.captured_inputs, *self.other_inputs],
            self.outputs,
        )
        partial_fn_ty = ht.FunctionType(self.other_inputs, closure_ty.output)
        return ht.FunctionType([closure_ty, *self.captured_inputs], [partial_fn_ty])

    @classmethod
    def from_ext(cls, custom: ops.ExtOp) -> PartialOp:
        match custom:
            case ops.ExtOp(
                _op_def=op_def, args=[captured_args, other_args, output_args]
            ):
                if op_def.qualified_name() == PARTIAL_OP_DEF.qualified_name():
                    return cls(
                        captured_inputs=[*_arg_seq_to_types(captured_args)],
                        other_inputs=[*_arg_seq_to_types(other_args)],
                        outputs=[*_arg_seq_to_types(output_args)],
                    )
        msg = f"Invalid custom op: {custom}"
        raise ops.AsExtOp.InvalidExtOp(msg)

    @property
    def num_out(self) -> int:
        return 1


UNSUPPORTED_OP_DEF: he.OpDef = EXTENSION.add_op_def(
    he.OpDef(
        "unsupported",
        signature=he.OpDefSig(
            poly_func=ht.PolyFuncType(
                params=[
                    # Name of the operation
                    ht.StringParam(),
                    # Input types
                    ht.ListParam(ht.TypeTypeParam(ht.TypeBound.Linear)),
                    # Output types
                    ht.ListParam(ht.TypeTypeParam(ht.TypeBound.Linear)),
                ],
                body=ht.FunctionType(
                    input=[ht.RowVariable(1, ht.TypeBound.Linear)],
                    output=[ht.RowVariable(2, ht.TypeBound.Linear)],
                ),
            )
        ),
        description="An unsupported operation stub emitted by Guppy.",
    )
)


@dataclass
class UnsupportedOp(ops.AsExtOp):
    """An unsupported operation stub emitted by Guppy.

    args:
        op_name: The name of the unsupported operation.
        inputs: The input types of the operation.
        outputs: The output types of the operation.
    """

    op_name: str
    inputs: list[ht.Type]
    outputs: list[ht.Type]

    def op_def(self) -> he.OpDef:
        return UNSUPPORTED_OP_DEF

    def type_args(self) -> list[ht.TypeArg]:
        op_name = ht.StringArg(self.op_name)
        input_args = ht.ListArg([ht.TypeTypeArg(ty) for ty in self.inputs])
        output_args = ht.ListArg([ht.TypeTypeArg(ty) for ty in self.outputs])
        return [op_name, input_args, output_args]

    def cached_signature(self) -> ht.FunctionType | None:
        return ht.FunctionType(self.inputs, self.outputs)

    @classmethod
    def from_ext(cls, custom: ops.ExtOp) -> UnsupportedOp:
        match custom:
            case ops.ExtOp(_op_def=op_def, args=args):
                if op_def.qualified_name() == UNSUPPORTED_OP_DEF.qualified_name():
                    [op_name, input_args, output_args] = args
                    assert isinstance(op_name, ht.StringArg), (
                        "The first argument to a guppylang.unsupported op "
                        "must be the operation name"
                    )
                    op_name = op_name.value
                    return cls(
                        op_name=op_name,
                        inputs=[*_arg_seq_to_types(input_args)],
                        outputs=[*_arg_seq_to_types(output_args)],
                    )
        msg = f"Invalid custom op: {custom}"
        raise ops.AsExtOp.InvalidExtOp(msg)

    @property
    def num_out(self) -> int:
        return len(self.outputs)


def _arg_seq_to_types(args: ht.TypeArg) -> Iterator[ht.Type]:
    """Converts a ListArg of type arguments into a sequence of types."""
    assert isinstance(args, ht.ListArg)
    for arg in args.elems:
        assert isinstance(arg, ht.TypeTypeArg)
        yield arg.ty
