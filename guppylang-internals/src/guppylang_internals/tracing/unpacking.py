from typing import Any, TypeVar

from hugr import ops
from hugr.build.dfg import DfBase

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.errors.comptime_errors import (
    IllegalComptimeExpressionError,
)
from guppylang_internals.checker.expr_checker import python_value_to_guppy_type
from guppylang_internals.compiler.core import CompilerContext
from guppylang_internals.compiler.expr_compiler import python_value_to_hugr
from guppylang_internals.error import GuppyComptimeError, GuppyError
from guppylang_internals.std._internal.compiler.array import array_new, unpack_array
from guppylang_internals.tracing.frozenlist import frozenlist
from guppylang_internals.tracing.object import (
    GuppyObject,
    GuppyStructObject,
    TracingDefMixin,
)
from guppylang_internals.tracing.state import get_tracing_state
from guppylang_internals.tys.builtin import (
    array_type,
    get_array_length,
    get_element_type,
    is_array_type,
)
from guppylang_internals.tys.const import ConstValue
from guppylang_internals.tys.ty import NoneType, StructType, TupleType

P = TypeVar("P", bound=ops.DfParentOp)


def unpack_guppy_object(
    obj: GuppyObject, builder: DfBase[P], frozen: bool = False
) -> Any:
    """Tries to turn as much of the structure of a GuppyObject into Python objects.

    For example, Guppy tuples are turned into Python tuples and Guppy arrays are turned
    into Python lists. This is achieved by inserting unpacking operations into the Hugr
    to get individual wires to be used in those Python objects.

    Setting `frozen=True` ensures that the resulting Python objects are not mutable in-
    place. This should be set for objects that originate from function inputs that are
    not borrowed.
    """
    match obj._ty:
        case NoneType():
            return None
        case TupleType(element_types=tys):
            unpack = builder.add_op(ops.UnpackTuple(), obj._use_wire(None))
            return tuple(
                unpack_guppy_object(GuppyObject(ty, wire), builder, frozen)
                for ty, wire in zip(tys, unpack.outputs(), strict=True)
            )
        case StructType() as ty:
            unpack = builder.add_op(ops.UnpackTuple(), obj._use_wire(None))
            field_values = [
                unpack_guppy_object(GuppyObject(field.ty, wire), builder, frozen)
                for field, wire in zip(ty.fields, unpack.outputs(), strict=True)
            ]
            return GuppyStructObject(ty, field_values, frozen)
        case ty if is_array_type(ty):
            length = get_array_length(ty)
            if isinstance(length, ConstValue):
                if length.value == 0:
                    # Zero-length lists cannot be turned back ito Guppy objects since
                    # there is no way to infer the type. Therefore, we should leave
                    # them as Guppy objects here
                    return obj
                elem_ty = get_element_type(ty)
                elems = unpack_array(builder, obj._use_wire(None))
                obj_list = [
                    unpack_guppy_object(GuppyObject(elem_ty, wire), builder, frozen)
                    for wire in elems
                ]
                return frozenlist(obj_list) if frozen else obj_list
            else:
                # Cannot handle generic sizes
                return obj
        case _:
            return obj


def guppy_object_from_py(
    v: Any, builder: DfBase[P], node: AstNode, ctx: CompilerContext
) -> GuppyObject:
    """Constructs a Guppy object from a Python value.

    Essentially undoes the `unpack_guppy_object` operation.
    """
    match v:
        case GuppyObject() as obj:
            return obj
        case TracingDefMixin() as defn:
            return defn.to_guppy_object()
        case None:
            return GuppyObject(NoneType(), builder.add_op(ops.MakeTuple()))
        case tuple(vs):
            objs = [guppy_object_from_py(v, builder, node, ctx) for v in vs]
            return GuppyObject(
                TupleType([obj._ty for obj in objs]),
                builder.add_op(ops.MakeTuple(), *(obj._use_wire(None) for obj in objs)),
            )
        case GuppyStructObject(_ty=struct_ty, _field_values=values):
            wires = []
            for f in struct_ty.fields:
                obj = guppy_object_from_py(values[f.name], builder, node, ctx)
                # Check that the field still has the correct type. Since we allow users
                # to mutate structs unchecked, this needs to be checked here
                if obj._ty != f.ty:
                    raise GuppyComptimeError(
                        f"Field `{f.name}` of object with type `{struct_ty}` has an "
                        f"unexpected type. Expected `{f.ty}`, got `{obj._ty}`."
                    )
                wires.append(obj._use_wire(None))
            return GuppyObject(struct_ty, builder.add_op(ops.MakeTuple(), *wires))
        case list(vs) if len(vs) > 0:
            objs = [guppy_object_from_py(v, builder, node, ctx) for v in vs]
            elem_ty = objs[0]._ty
            for i, obj in enumerate(objs[1:]):
                if obj._ty != elem_ty:
                    raise GuppyComptimeError(
                        f"Element at index {i + 1} does not match the type of "
                        f"previous elements. Expected `{elem_ty}`, got `{obj._ty}`."
                    )
            hugr_elem_ty = elem_ty.to_hugr(ctx)
            wires = [obj._use_wire(None) for obj in objs]
            return GuppyObject(
                array_type(elem_ty, len(vs)),
                builder.add_op(array_new(hugr_elem_ty, len(vs)), *wires),
            )
        case []:
            # Empty lists are tricky since we can't infer the element type here
            # TODO: Propagate type information?
            raise GuppyComptimeError("Cannot infer the type of empty list")
        case v:
            ty = python_value_to_guppy_type(v, node, get_tracing_state().globals)
            if ty is None:
                raise GuppyError(IllegalComptimeExpressionError(node, type(v)))
            hugr_val = python_value_to_hugr(v, ty, ctx)
            assert hugr_val is not None
            return GuppyObject(ty, builder.load(hugr_val))


def update_packed_value(v: Any, obj: "GuppyObject", builder: DfBase[P]) -> bool:
    """Given a Python value `v` and a `GuppyObject` `obj` that was constructed from `v`
    using `guppy_object_from_py`, tries to update the wires of any `GuppyObjects`
    contained in `v` to the new wires specified by `obj`.

    Also resets the used flag on any of those updated wires. This corresponds to making
    the object available again since it now corresponds to a fresh wire.

    Returns `True` if all wires could be updated, otherwise `False`.
    """
    match v:
        case GuppyObject() as v_obj:
            assert v_obj._ty == obj._ty
            v_obj._wire = obj._use_wire(None)
            if not v_obj._ty.droppable and v_obj._used:
                state = get_tracing_state()
                state.unused_undroppable_objs[v_obj._id] = v_obj
            v_obj._used = None
        case None:
            assert isinstance(obj._ty, NoneType)
        case tuple(vs):
            assert isinstance(obj._ty, TupleType)
            wire_iterator = builder.add_op(
                ops.UnpackTuple(), obj._use_wire(None)
            ).outputs()
            for v, ty, out_wire in zip(
                vs, obj._ty.element_types, wire_iterator, strict=True
            ):
                success = update_packed_value(v, GuppyObject(ty, out_wire), builder)
                if not success:
                    return False
        case GuppyStructObject(_ty=ty, _field_values=values):
            assert obj._ty == ty
            wire_iterator = builder.add_op(
                ops.UnpackTuple(), obj._use_wire(None)
            ).outputs()
            for field, out_wire in zip(ty.fields, wire_iterator, strict=True):
                v = values[field.name]
                success = update_packed_value(
                    v, GuppyObject(field.ty, out_wire), builder
                )
                if not success:
                    values[field.name] = obj
        case list(vs) if len(vs) > 0:
            assert is_array_type(obj._ty)
            elem_ty = get_element_type(obj._ty)
            wires = unpack_array(builder, obj._use_wire(None))
            for i, (v, wire) in enumerate(zip(vs, wires, strict=True)):
                success = update_packed_value(v, GuppyObject(elem_ty, wire), builder)
                if not success:
                    vs[i] = obj
        case _:
            return False
    return True
