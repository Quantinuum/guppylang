from functools import singledispatchmethod

from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tys.arg import ConstArg, TypeArg
from guppylang_internals.tys.const import Const, ConstValue
from guppylang_internals.tys.param import ConstParam, TypeParam
from guppylang_internals.tys.ty import (
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    OpaqueType,
    StructType,
    TupleType,
    Type,
)
from guppylang_internals.tys.var import BoundVar, ExistentialVar, UniqueId


class TypePrinter:
    """Visitor that pretty prints types.

    Takes care of inserting minimal parentheses and renaming variables to make them
    unique.
    """

    # Store how often each user-picked display name is used to stand for different
    # variables
    used: dict[str, int]

    # Already chosen names for bound and existential variables
    bound_names: list[str]
    existential_names: dict[UniqueId, str]

    # Count how often the user has picked the same name to stand for different variables
    counter: dict[str, int]

    def __init__(self) -> None:
        self.used = {}
        self.bound_names = []
        self.existential_names = {}
        self.counter = {}

    def _fresh_name(self, display_name: str) -> str:
        if display_name not in self.counter:
            self.counter[display_name] = 1
            return display_name

        # If the display name `T` has already been used, we start adding indices: `T`,
        # `T'1`, `T'2`, ...
        indexed = f"{display_name}'{self.counter[display_name]}"
        self.counter[display_name] += 1
        return indexed

    def visit(self, ty: Type | Const) -> str:
        return self._visit(ty, False)

    @singledispatchmethod
    def _visit(self, ty: Type, inside_row: bool) -> str:
        raise InternalGuppyError(f"Tried to pretty-print unknown type: {ty!r}")

    @_visit.register
    def _visit_BoundVar(self, var: BoundVar, inside_row: bool) -> str:
        if var.idx < len(self.bound_names):
            return self.bound_names[var.idx]
        return var.display_name

    @_visit.register
    def _visit_ExistentialVar(self, var: ExistentialVar, inside_row: bool) -> str:
        if var.id not in self.existential_names:
            self.existential_names[var.id] = self._fresh_name(var.display_name)
        return f"?{self.existential_names[var.id]}"

    @staticmethod
    def _print_flags(flags: InputFlags) -> str:
        s = ""
        if InputFlags.Owned in flags:
            s += " @owned"
        if InputFlags.Comptime in flags:
            s += " @comptime"
        return s

    @_visit.register
    def _visit_FunctionType(self, ty: FunctionType, inside_row: bool) -> str:
        if ty.parametrized:
            for p in ty.params:
                self.bound_names.append(self._fresh_name(p.name))
        inputs = ", ".join(
            [
                self._visit(inp.ty, True) + self._print_flags(inp.flags)
                for inp in ty.inputs
            ]
        )
        if len(ty.inputs) != 1:
            inputs = f"({inputs})"
        output = self._visit(ty.output, True)
        if ty.parametrized:
            params = [
                self._visit(param, False)
                for param in ty.params
                # Don't print out implicit parameters generated for comptime arguments
                if not isinstance(param, ConstParam) or not param.from_comptime_arg
            ]
            quantified = ", ".join(params)
            del self.bound_names[: -len(ty.params)]
            return _wrap(f"forall {quantified}. {inputs} -> {output}", inside_row)
        return _wrap(f"{inputs} -> {output}", inside_row)

    @_visit.register(OpaqueType)
    @_visit.register(StructType)
    def _visit_OpaqueType_StructType(
        self, ty: OpaqueType | StructType, inside_row: bool
    ) -> str:
        if ty.args:
            args = ", ".join(self._visit(arg, True) for arg in ty.args)
            return f"{ty.defn.name}[{args}]"
        return ty.defn.name

    @_visit.register
    def _visit_TupleType(self, ty: TupleType, inside_row: bool) -> str:
        args = ", ".join(self._visit(arg, True) for arg in ty.args)
        return f"({args})"

    @_visit.register
    def _visit_NoneType(self, ty: NoneType, inside_row: bool) -> str:
        return "None"

    @_visit.register
    def _visit_NumericType(self, ty: NumericType, inside_row: bool) -> str:
        return ty.kind.name.lower()

    @_visit.register
    def _visit_TypeParam(self, param: TypeParam, inside_row: bool) -> str:
        # TODO: Print linearity?
        return self.bound_names[param.idx]

    @_visit.register
    def _visit_ConstParam(self, param: ConstParam, inside_row: bool) -> str:
        kind = self._visit(param.ty, True)
        name = self.bound_names[param.idx]
        return f"{name}: {kind}"

    @_visit.register
    def _visit_TypeArg(self, arg: TypeArg, inside_row: bool) -> str:
        return self._visit(arg.ty, inside_row)

    @_visit.register
    def _visit_ConstArg(self, arg: ConstArg, inside_row: bool) -> str:
        return self._visit(arg.const, inside_row)

    @_visit.register
    def _visit_ConstValue(self, c: ConstValue, inside_row: bool) -> str:
        return str(c.value)


def _wrap(s: str, inside_row: bool) -> str:
    return f"({s})" if inside_row else s


def signature_to_str(name: str, sig: FunctionType, has_var_args: bool = False) -> str:
    """Displays a function signature in Python syntax including the function name."""
    assert sig.input_names is not None
    s = f"def {name}("
    s += ", ".join(
        f"{inp.name}: {inp.ty}{TypePrinter._print_flags(inp.flags)}"
        for inp in sig.inputs
    )
    s += ", ..." if has_var_args else ""
    return s + ") -> " + str(sig.output)
