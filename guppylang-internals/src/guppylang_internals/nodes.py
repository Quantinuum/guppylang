"""Custom AST nodes used by Guppy"""

import ast
from collections.abc import Mapping
from enum import Enum
from typing import TYPE_CHECKING, Any

from guppylang_internals.ast_util import AstNode
from guppylang_internals.span import Span, to_span
from guppylang_internals.tys.const import Const
from guppylang_internals.tys.subst import Inst
from guppylang_internals.tys.ty import (
    FunctionType,
    StructType,
    TupleType,
    Type,
    UnitaryFlags,
)

if TYPE_CHECKING:
    from guppylang_internals.cfg.cfg import CFG
    from guppylang_internals.checker.cfg_checker import CheckedCFG
    from guppylang_internals.checker.core import Place, Variable
    from guppylang_internals.definition.common import DefId
    from guppylang_internals.definition.struct import StructField
    from guppylang_internals.tys.param import ConstParam


class PlaceNode(ast.expr):
    place: "Place"

    _fields = ("place",)


class GlobalName(ast.Name):
    id: str
    def_id: "DefId"

    _fields = (
        "id",
        "def_id",
    )


class GenericParamValue(ast.Name):
    id: str
    param: "ConstParam"

    _fields = (
        "id",
        "param",
    )


class LocalCall(ast.expr):
    func: ast.expr
    args: list[ast.expr]

    _fields = (
        "func",
        "args",
    )


class GlobalCall(ast.expr):
    def_id: "DefId"
    args: list[ast.expr]
    type_args: Inst  # Inferred type arguments

    _fields = (
        "def_id",
        "args",
        "type_args",
    )


class TensorCall(ast.expr):
    """A call to a tuple of functions. Behaves like a local call, but more
    unpacking of tuples is required at compilation"""

    func: ast.expr
    args: list[ast.expr]
    tensor_ty: FunctionType

    _fields = (
        "func",
        "args",
        "tensor_ty",
    )


class TypeApply(ast.expr):
    value: ast.expr
    inst: Inst

    _fields = (
        "value",
        "inst",
    )


class PartialApply(ast.expr):
    """A partial function application.

    This node is emitted when methods are loaded as values, since this requires
    partially applying the `self` argument.
    """

    func: ast.expr
    args: list[ast.expr]

    _fields = (
        "func",
        "args",
    )


class FieldAccessAndDrop(ast.expr):
    """A field access on a struct, dropping all the remaining other fields."""

    value: ast.expr
    struct_ty: "StructType"
    field: "StructField"

    _fields = (
        "value",
        "struct_ty",
        "field",
    )


class SubscriptAccessAndDrop(ast.expr):
    """A subscript element access on an object, dropping all the remaining items."""

    item: "Variable"
    item_expr: ast.expr
    getitem_expr: ast.expr
    original_expr: ast.Subscript

    _fields = ("item", "item_expr", "getitem_expr", "original_expr")


class TupleAccessAndDrop(ast.expr):
    """A subscript element access on a tuple, dropping all the remaining items."""

    value: ast.expr
    tuple_ty: TupleType
    index: int

    _fields = ("value", "tuple_ty", "index")


class MakeIter(ast.expr):
    """Creates an iterator using the `__iter__` magic method.

    This node is inserted in `for` loops and list comprehensions.
    """

    value: ast.expr
    unwrap_size_hint: bool

    # Node that triggered the creation of this iterator. For example, a for loop stmt.
    # It is not mentioned in `_fields` so that it is not visible to AST visitors
    origin_node: ast.AST

    _fields = ("value",)

    def __init__(
        self, value: ast.expr, origin_node: ast.AST, unwrap_size_hint: bool = True
    ) -> None:
        super().__init__(value)
        self.origin_node = origin_node
        self.unwrap_size_hint = unwrap_size_hint

    # Needed for the deepcopy to work correctly, ast.AST's deepcopy logic
    # reconstructs nodes using _fields only.
    # If you store extra attributes or rely overwriting the __init__,
    # deepcopy will crash with a constructor mismatch.
    # Overriding __reduce__ forces deepcopy to copy the instance dictionary instead
    __reduce_ex__ = object.__reduce_ex__
    __reduce__ = object.__reduce__


class IterNext(ast.expr):
    """Obtains the next element of an iterator using the `__next__` magic method.

    This node is inserted in `for` loops and list comprehensions.
    """

    value: ast.expr

    _fields = ("value",)


class DesugaredGenerator(ast.expr):
    """A single desugared generator in a list comprehension.

    Stores assignments of the original generator targets as well as dummy variables for
    the iterator and hasnext test.
    """

    iter_assign: ast.Assign
    next_call: ast.expr
    iter: ast.expr
    target: ast.expr
    ifs: list[ast.expr]

    used_outer_places: "list[Place]"

    _fields = (
        "iter_assign",
        "next_call",
        "iter",
        "target",
        "ifs",
    )


class DesugaredGeneratorExpr(ast.expr):
    """A desugared generator expression."""

    elt: ast.expr
    generators: list[DesugaredGenerator]

    _fields = (
        "elt",
        "generators",
    )


class DesugaredListComp(ast.expr):
    """A desugared list comprehension."""

    elt: ast.expr
    generators: list[DesugaredGenerator]

    _fields = (
        "elt",
        "generators",
    )


class DesugaredArrayComp(ast.expr):
    """A desugared array comprehension."""

    elt: ast.expr
    generator: DesugaredGenerator
    length: Const
    elt_ty: Type

    _fields = (
        "elt",
        "generator",
        "length",
        "elt_ty",
    )


class ComptimeExpr(ast.expr):
    """A compile-time evaluated `py(...)` expression."""

    value: ast.expr

    _fields = ("value",)


class ExitKind(Enum):
    ExitShot = 0  # Exit the current shot
    Panic = 1  # Panic the program ending all shots


class PanicExpr(ast.expr):
    """A `panic(msg, *args)` or `exit(msg, *args)` expression ."""

    kind: ExitKind
    signal: ast.expr
    msg: ast.expr
    values: list[ast.expr]

    _fields = ("kind", "signal", "msg", "values")


class BarrierExpr(ast.expr):
    """A `barrier(*args)` expression."""

    args: list[ast.expr]
    func_ty: FunctionType
    _fields = ("args", "func_ty")


class StateResultExpr(ast.expr):
    """A `state_result(tag, *args)` expression."""

    tag_value: Const
    tag_expr: ast.expr
    args: list[ast.expr]
    func_ty: FunctionType
    #: Array length in case this is an array result, otherwise `None`
    array_len: Const | None
    _fields = ("tag_value", "tag_expr", "args", "func_ty", "has_array_input")


AnyCall = LocalCall | GlobalCall | TensorCall | BarrierExpr | StateResultExpr


class InoutReturnSentinel(ast.expr):
    """An invisible expression corresponding to an implicit use of borrowed vars
    whenever a function returns."""

    var: "Place | str"

    _fields = ("var",)


class UnpackPattern(ast.expr):
    """The LHS of an unpacking assignment like `a, *bs, c = ...` or
    `[a, *bs, c] = ...`."""

    #: Patterns occurring on the left of the starred target
    left: list[ast.expr]

    #: The starred target or `None` if there is none
    starred: ast.expr | None

    #: Patterns occurring on the right of the starred target. This will be an empty list
    #: if there is no starred target
    right: list[ast.expr]

    _fields = ("left", "starred", "right")


class TupleUnpack(ast.expr):
    """The LHS of an unpacking assignment of a tuple."""

    #: The (possibly starred) unpacking pattern
    pattern: UnpackPattern

    _fields = ("pattern",)


class ArrayUnpack(ast.expr):
    """The LHS of an unpacking assignment of an array."""

    #: The (possibly starred) unpacking pattern
    pattern: UnpackPattern

    #: Length of the array
    length: int

    #: Element type of the array
    elt_type: Type

    _fields = ("pattern",)

    def __init__(self, pattern: UnpackPattern, length: int, elt_type: Type) -> None:
        super().__init__(pattern)
        self.length = length
        self.elt_type = elt_type

    # See MakeIter for explanation
    __reduce__ = object.__reduce__
    __reduce_ex__ = object.__reduce_ex__


class IterableUnpack(ast.expr):
    """The LHS of an unpacking assignment of an iterable type."""

    #: The (possibly starred) unpacking pattern
    pattern: UnpackPattern

    #: Comprehension that collects the RHS iterable into an array
    compr: DesugaredArrayComp

    #: Dummy variable that the RHS should be bound to. This variable is referenced in
    #: `compr`
    rhs_var: PlaceNode

    # Don't mention the comprehension in _fields to avoid visitors recursing it
    _fields = ("pattern",)

    def __init__(
        self, pattern: UnpackPattern, compr: DesugaredArrayComp, rhs_var: PlaceNode
    ) -> None:
        super().__init__(pattern)
        self.compr = compr
        self.rhs_var = rhs_var

    # See MakeIter for explanation
    __reduce__ = object.__reduce__
    __reduce_ex__ = object.__reduce_ex__


#: Any unpacking operation.
AnyUnpack = TupleUnpack | ArrayUnpack | IterableUnpack


class NestedFunctionDef(ast.FunctionDef):
    cfg: "CFG"
    ty: FunctionType
    docstring: str | None

    def __init__(self, cfg: "CFG", ty: FunctionType, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cfg = cfg
        self.ty = ty


class CheckedNestedFunctionDef(ast.FunctionDef):
    def_id: "DefId"
    cfg: "CheckedCFG[Place]"
    ty: FunctionType

    #: Mapping from names to variables captured by this function, together with an AST
    #: node witnessing a use of the captured variable in the function body.
    captured: Mapping[str, tuple["Variable", AstNode]]

    def __init__(
        self,
        def_id: "DefId",
        cfg: "CheckedCFG[Place]",
        ty: FunctionType,
        captured: Mapping[str, tuple["Variable", AstNode]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.def_id = def_id
        self.cfg = cfg
        self.ty = ty
        self.captured = captured


class Dagger(ast.expr):
    """The dagger modifier"""

    def __init__(self, node: ast.expr) -> None:
        super().__init__(**node.__dict__)

    # See MakeIter for explanation
    __reduce__ = object.__reduce__
    __reduce_ex__ = object.__reduce_ex__


class Control(ast.Call):
    """The control modifier"""

    ctrl: list[ast.expr]
    qubit_num: int | Const | None

    _fields = ("ctrl",)

    def __init__(self, node: ast.Call, ctrl: list[ast.expr]) -> None:
        super().__init__(**node.__dict__)
        self.ctrl = ctrl
        self.qubit_num = None

    # See MakeIter for explanation
    __reduce__ = object.__reduce__
    __reduce_ex__ = object.__reduce_ex__


class Power(ast.expr):
    """The power modifier"""

    iter: ast.expr

    _fields = ("iter",)

    def __init__(self, node: ast.expr, iter: ast.expr) -> None:
        super().__init__(**node.__dict__)
        self.iter = iter

    # See MakeIter for explanation
    __reduce__ = object.__reduce__
    __reduce_ex__ = object.__reduce_ex__


Modifier = Dagger | Control | Power


class ModifiedBlock(ast.With):
    cfg: "CFG"
    dagger: list[Dagger]
    control: list[Control]
    power: list[Power]

    def __init__(self, cfg: "CFG", *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cfg = cfg
        self.dagger = []
        self.control = []
        self.power = []

    def is_dagger(self) -> bool:
        return len(self.dagger) % 2 == 1

    def is_control(self) -> bool:
        return len(self.control) > 0

    def is_power(self) -> bool:
        return len(self.power) > 0

    def span_ctxt_manager(self) -> Span:
        return Span(
            to_span(self.items[0].context_expr).start,
            to_span(self.items[-1].context_expr).end,
        )

    def push_modifier(self, modifier: Modifier) -> None:
        """Pushes a modifier kind onto the modifier."""
        if isinstance(modifier, Dagger):
            self.dagger.append(modifier)
        elif isinstance(modifier, Control):
            self.control.append(modifier)
        elif isinstance(modifier, Power):
            self.power.append(modifier)
        else:
            raise TypeError(f"Unknown modifier: {modifier}")

    def flags(self) -> UnitaryFlags:
        flags = UnitaryFlags.NoFlags
        if self.is_dagger():
            flags |= UnitaryFlags.Dagger
        if self.is_control():
            flags |= UnitaryFlags.Control
        if self.is_power():
            flags |= UnitaryFlags.Power
        return flags


class CheckedModifiedBlock(ast.With):
    def_id: "DefId"
    cfg: "CheckedCFG[Place]"
    dagger: list[Dagger]
    control: list[Control]
    power: list[Power]

    #: The type of the body of With block.
    ty: FunctionType
    #: Mapping from names to variables captured in the body.
    captured: Mapping[str, tuple["Variable", AstNode]]

    def __init__(
        self,
        def_id: "DefId",
        cfg: "CheckedCFG[Place]",
        ty: FunctionType,
        captured: Mapping[str, tuple["Variable", AstNode]],
        dagger: list[Dagger],
        control: list[Control],
        power: list[Power],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.def_id = def_id
        self.cfg = cfg
        self.ty = ty
        self.captured = captured
        self.dagger = dagger
        self.control = control
        self.power = power

    # See MakeIter for explanation
    __reduce__ = object.__reduce__
    __reduce_ex__ = object.__reduce_ex__

    def __str__(self) -> str:
        # generate a function name from the def_id
        return f"__WithBlock__({self.def_id})"

    def has_dagger(self) -> bool:
        return len(self.dagger) % 2 == 1

    def has_control(self) -> bool:
        return any(len(c.ctrl) > 0 for c in self.control)

    def has_power(self) -> bool:
        return len(self.power) > 0
