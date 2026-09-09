import ast
import builtins
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from guppylang_internals.ast_util import branching_in_ast, get_type, loop_in_ast
from guppylang_internals.cfg.bb import BBStatement
from guppylang_internals.checker.cfg_checker import CheckedCFG
from guppylang_internals.checker.core import Place
from guppylang_internals.checker.errors.generic import (
    InvalidUnderDagger,
    UnexpectedError,
)
from guppylang_internals.checker.modifier import CustomModifierKind
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.diagnostic import Error, Help
from guppylang_internals.error import GuppyError, GuppyTypeError, pretty_errors
from guppylang_internals.nodes import (
    AbortExpr,
    AnyCall,
    BarrierExpr,
    CheckedModifiedBlock,
    GlobalCall,
    LocalCall,
    ModifiedBlock,
    StateOutputExpr,
    TensorCall,
)
from guppylang_internals.span import ToSpan, function_header_span
from guppylang_internals.tys.errors import UnitaryCallError
from guppylang_internals.tys.qubit import contain_qubit_ty
from guppylang_internals.tys.ty import (
    CALL_CONTROLLED_METHOD,
    CALL_CTRL_DAGGERED_METHOD,
    CALL_DAGGERED_METHOD,
    FunctionType,
    UnitaryFlags,
)

if TYPE_CHECKING:
    from guppylang_internals.definition.function import RawFunctionDef

type CustomModifiedDefinitions = dict[CustomModifierKind, RawFunctionDef]


@dataclass(frozen=True)
class InvalidUnitaryError(Error):
    title: ClassVar[str] = "Invalid `@guppy.unitary` implementation"
    implementations: tuple[str, ...]
    required_implementations: tuple[str, ...]
    flag_on_call: UnitaryFlags
    required_flag_on_call: UnitaryFlags

    @property
    def rendered_message(self) -> str:
        implementations = " and ".join(f"`{name}`" for name in self.implementations)
        required = " and ".join(f"`{name}`" for name in self.required_implementations)
        required = (
            f"a {required} implementation"
            if len(self.required_implementations) == 1
            else f"{required} implementations"
        )
        declaration = (
            ""
            if self.flag_on_call == UnitaryFlags.NoFlags
            else f" with `__call__` declared as `{self.flag_on_call.hint_rendering()}`"
        )

        return (
            f"A `@guppy.unitary` class implementing {implementations}{declaration} "
            f"requires either {required} or "
            f"`{self.required_flag_on_call.hint_rendering()}` on `__call__`"
        )


def check_invalid_under_dagger(
    def_node: ast.FunctionDef | ModifiedBlock, unitary_flags: UnitaryFlags
) -> None:
    """Check that there are no invalid constructs in a daggered CFG."""
    if UnitaryFlags.Dagger not in unitary_flags:
        return

    if isinstance(def_node, ast.FunctionDef):
        stmt_list = def_node.body
    else:
        # When analyzing a `ModifiedBlock` we need the original AST before
        # the builder transforms it
        stmt_list = def_node.original_ast_body
        assert stmt_list is not None, (
            "original_ast_body should not be None for a daggered block"
        )

    for stmt in stmt_list:
        # we do not want to recursively check inside nested `with` blocks
        if isinstance(stmt, ast.With):
            continue
        for loop in loop_in_ast(stmt):
            err = InvalidUnderDagger(loop, things="Loop")
            raise _annotate_diagnostics(err, def_node, unitary_flags)
        for branch in branching_in_ast(stmt):
            err = InvalidUnderDagger(branch, things="Branch")
            raise _annotate_diagnostics(err, def_node, unitary_flags)


def _annotate_diagnostics(
    err: InvalidUnderDagger,
    node: ast.FunctionDef | ModifiedBlock,
    unitary_flags: UnitaryFlags,
) -> GuppyError:
    if isinstance(node, ModifiedBlock):
        err.add_sub_diagnostic(InvalidUnderDagger.Dagger(node.span_ctxt_manager()))
    elif isinstance(node, ast.FunctionDef):
        err.add_sub_diagnostic(
            InvalidUnderDagger.FunctionHelp(None, node.name, unitary_flags)
        )
    err.add_sub_diagnostic(InvalidUnderDagger.ControlFlowHelp(None))

    return GuppyError(err)


class BBUnitaryChecker(ast.NodeVisitor):
    """AST visitor that checks whether the modifiers (dagger, control, power)
    are applicable."""

    flags: UnitaryFlags

    def check(
        self,
        statements: list[BBStatement] | list[ast.expr],
        unitary_flags: UnitaryFlags,
    ) -> None:
        self.flags = unitary_flags
        for stmt in statements:
            self.visit(stmt)

    def _check_args(self, args: list[ast.expr]) -> bool:
        """Recursively checks the arguments of a call.
        Returns True if the call is classical"""
        for arg in args:
            self.visit(arg)
        return all(not contain_qubit_ty(get_type(arg)) for arg in args)

    def _check_call(
        self, node: AnyCall, call_ty: FunctionType, func: CallableDef | None = None
    ) -> None:
        """
        `func`: it's only used for a better error message when the call is a GlobalCall.
        Is None for LocalCall and TensorCall.
        """

        # If we are under any modifier, we cannot allocate qubits
        if contain_qubit_ty(call_ty.output) and self.flags != UnitaryFlags.NoFlags:
            err = UnitaryCallError(node, self.flags, missing_keyword_hint=False)
            err.add_sub_diagnostic(UnitaryCallError.QubitAllocationNote(None))
            raise GuppyError(err)

        # If the function has quantum i/o, the flags must be compatible with the
        # function's unitary flags. Otherwise, if the function is classical, we only
        # need to check that if we are in dagger (or unitary) context, the function
        # is daggerable.
        is_classic_fun = self._check_args(node.args)
        if is_classic_fun:
            if UnitaryFlags.Dagger not in self.flags:
                is_a_valid_call = True
            else:
                is_a_valid_call = UnitaryFlags.Dagger in call_ty.unitary_flags
        else:
            is_a_valid_call = self.flags in call_ty.unitary_flags

        if not is_a_valid_call:
            from guppylang_internals.definition.custom import CustomFunctionDef

            # We want the hint only for non-custom functions, since custom
            # functions are usually quantum operations (e.g. gates or measurement)
            if isinstance(func, CustomFunctionDef):
                err = UnitaryCallError(
                    node,
                    self.flags & (~call_ty.unitary_flags),
                    missing_keyword_hint=True,
                )
            else:
                if func is not None:
                    err = UnitaryCallError(
                        node,
                        self.flags & (~call_ty.unitary_flags),
                        missing_keyword_hint=False,
                    )
                    from guppylang_internals.definition.pytket_circuits import (
                        ParsedPytketDef,
                    )

                    if isinstance(func, ParsedPytketDef):
                        err.add_sub_diagnostic(
                            UnitaryCallError.PytketHint(None, func.name)
                        )
                    else:
                        err.add_sub_diagnostic(
                            UnitaryCallError.MissingFlagHint(None, func.name)
                        )
                else:
                    # If func is None, we are checking a higher-order call
                    missing_flags = self.flags & (~call_ty.unitary_flags)
                    err = UnitaryCallError(
                        node,
                        missing_flags,
                        missing_keyword_hint=False,
                    )
                    err.add_sub_diagnostic(
                        UnitaryCallError.HigherOrderHint(
                            None,
                            missing_flags.callable_name(),
                            "higher-order"
                            if call_ty.unitary_flags == UnitaryFlags.NoFlags
                            else call_ty.unitary_flags.callable_name(),
                        )
                    )
            raise GuppyTypeError(err)

    def visit_GlobalCall(self, node: GlobalCall) -> None:
        func: CallableDef = node.defn
        self._check_call(node, func.ty, func)

    def visit_LocalCall(self, node: LocalCall) -> None:
        func = get_type(node.func)
        assert isinstance(func, FunctionType)
        self._check_call(node, func)

    def visit_TensorCall(self, node: TensorCall) -> None:
        self._check_call(node, node.tensor_ty)

    def visit_BarrierExpr(self, node: BarrierExpr) -> None:
        # Barrier is always allowed
        pass

    def visit_StateOutputExpr(self, node: StateOutputExpr) -> None:
        # State output is not allowed under dagger, since the execution order
        # is not guaranteed
        if UnitaryFlags.Dagger in self.flags:
            raise GuppyTypeError(
                UnitaryCallError(
                    node,
                    self.flags,
                    missing_keyword_hint=True,
                )
            )

    def visit_AbortExpr(self, node: AbortExpr) -> None:
        # panics and exits are not allowed under dagger, since the execution order
        # is not guaranteed
        if UnitaryFlags.Dagger in self.flags:
            raise GuppyTypeError(
                UnitaryCallError(
                    node,
                    self.flags,
                    missing_keyword_hint=True,
                )
            )
        self.visit(node.signal)
        self.visit(node.msg)
        for value in node.values:
            self.visit(value)

    def visit_CheckedModifiedBlock(self, node: CheckedModifiedBlock) -> None:
        # Nested modified blocks are checked separately by the CFG checker
        pass

    def _check_assign(self, node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> None:
        if node.value is not None:
            self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_assign(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._check_assign(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._check_assign(node)


def check_cfg_unitary(
    cfg: CheckedCFG[Place],
    unitary_flags: UnitaryFlags,
) -> None:
    """Checks that the given unitary flags are valid for a CFG."""
    # If no UnitaryFlags are present, we do no need to check unitarity
    if unitary_flags == UnitaryFlags.NoFlags:
        return

    bb_checker = BBUnitaryChecker()
    for bb in cfg.bbs:
        bb_checker.check(bb.statements, unitary_flags)


def check_modified_def_combinations(
    unitary_flags: UnitaryFlags,
    *,
    definition_span: ToSpan,
    has_daggered: bool,
    has_controlled: bool,
    has_ctrl_daggered: bool,
) -> None:
    """Check that custom unitary modifier implementations form a valid set.

    We require:
    - If a `@guppy.unitary` class has both `daggered` and `controlled` implementations,
      it must also have a `ctrl_daggered` implementation, unless `__call__` is marked
      as `unitary=True`.
    - If `__call__` is marked as `controllable=True` and the function has a
      `daggered` implementation, it must also have a `ctrl_daggered` implementation
      or `__call__` is marked as `unitary=True`.
    - If `__call__` is marked as `daggerable=True` and the function has a
      `controlled` implementation, it must also have a `ctrl_daggered` implementation
      or `__call__` is marked as `unitary=True`.
    - If a `@guppy.unitary` class has a `ctrl_daggered` implementation and `__call__`
      has no unitary flags, it must also have `controlled` and `daggered`
      implementations.
    - If a `@guppy.unitary` class has a `ctrl_daggered` implementation and is marked as
      `controllable=True`, it must also have a `daggered` implementation, unless
      `__call__` is marked as `daggerable=True`.
    - If a `@guppy.unitary` class has a `ctrl_daggered` implementation and is marked as
      `daggerable=True`, it must also have a `controlled` implementation, unless
      `__call__` is marked as `controllable=True`.
    """
    implementations = tuple(
        name
        for name, present in (
            ("daggered", has_daggered),
            ("controlled", has_controlled),
            ("ctrl_daggered", has_ctrl_daggered),
        )
        if present
    )

    # Custom daggered and controlled implementations require ctrl_daggered support.
    if (
        has_daggered
        and has_controlled
        and not has_ctrl_daggered
        and unitary_flags != UnitaryFlags.Unitary
    ):
        raise GuppyError(
            InvalidUnitaryError(
                definition_span,
                implementations,
                ("ctrl_daggered",),
                unitary_flags,
                UnitaryFlags.Unitary,
            )
        )
    if not has_ctrl_daggered and unitary_flags != UnitaryFlags.Unitary:
        # Controllable plus a custom daggered implementation requires ctrl_daggered.
        if has_daggered and UnitaryFlags.Control in unitary_flags:
            raise GuppyError(
                InvalidUnitaryError(
                    definition_span,
                    implementations,
                    ("ctrl_daggered",),
                    unitary_flags,
                    UnitaryFlags.Unitary,
                )
            )
        # Daggerable plus a custom controlled implementation requires ctrl_daggered.
        if has_controlled and UnitaryFlags.Dagger in unitary_flags:
            raise GuppyError(
                InvalidUnitaryError(
                    definition_span,
                    implementations,
                    ("ctrl_daggered",),
                    unitary_flags,
                    UnitaryFlags.Unitary,
                )
            )

    # A custom ctrl_daggered implementation needs both modifier capabilities. Each
    # capability may be provided by a custom implementation or declared on __call__.
    if has_ctrl_daggered:
        missing_implementations = [
            name
            for name, supported in (
                (
                    "controlled",
                    has_controlled or UnitaryFlags.Control in unitary_flags,
                ),
                ("daggered", has_daggered or UnitaryFlags.Dagger in unitary_flags),
            )
            if not supported
        ]
        if missing_implementations:
            required_flag = UnitaryFlags.NoFlags
            if "controlled" in missing_implementations:
                required_flag |= UnitaryFlags.Control
            if "daggered" in missing_implementations:
                required_flag |= UnitaryFlags.Dagger
            raise GuppyError(
                InvalidUnitaryError(
                    definition_span,
                    implementations,
                    tuple(missing_implementations),
                    unitary_flags,
                    required_flag,
                )
            )


@dataclass(frozen=True)
class InvalidUnitaryMethodError(Error):
    title: ClassVar[str] = "Invalid `@guppy.unitary` method"
    node_name: str
    class_name: str
    span_label: ClassVar[str] = (
        "{node_name}` in the `@guppy.unitary` class `{class_name}`"
        " must be a guppy function"
    )


@dataclass(frozen=True)
class InvalidUnitaryMetadataHelp(Help):
    message: ClassVar[str] = (
        "This method cannot set unitary flags. To set unitary flag "
        "to the unitary class, use the decorator on top of `__call__`."
    )


@dataclass(frozen=True)
class InvalidExpectedQubit(Help):
    message: ClassVar[str] = (
        "This method cannot cannot use `@expected_qubits`; Use the decorator on top of "
        "`__call__` to set the expected qubits."
    )


@dataclass(frozen=True)
class InvalidUnitaryMethodHelp(Help):
    message: ClassVar[str] = (
        f"Only guppy functions named: '__call__', '{CALL_CONTROLLED_METHOD}', "
        f"'{CALL_CTRL_DAGGERED_METHOD}' or '{CALL_DAGGERED_METHOD}' are "
        "allowed as methods in a `@guppy.unitary` class. "
    )


@pretty_errors
def check_unitary_method[T](
    cls: builtins.type[T],
    class_ast: ast.ClassDef,
) -> CustomModifiedDefinitions:
    """Validate a unitary class body and return its custom modifier methods.

    ``methods`` contains the class's own Guppy-decorated raw function definitions.
    The caller must already have validated ``__call__``.
    """
    from guppylang.defs import GuppyDefinition

    from guppylang_internals.definition.function import RawFunctionDef

    custom_methods: dict[CustomModifierKind, RawFunctionDef] = {}
    valid_method_names = [kind.value for kind in CustomModifierKind] + ["__call__"]
    for node in class_ast.body:
        if not isinstance(node, ast.FunctionDef) or node.name not in valid_method_names:
            raise GuppyError(
                UnexpectedError(
                    node, "statement", unexpected_in="in a `@guppy.unitary` class"
                ).add_sub_diagnostic(InvalidUnitaryMethodHelp(None))
            )
        method_name = node.name
        # `__call__` has already been checked in `decorator._get_unitary_call_def`
        if method_name == "__call__":
            continue
        method = cls.__dict__.get(method_name)

        if not (
            isinstance(method, GuppyDefinition)
            and isinstance(method.wrapped, RawFunctionDef)
        ):
            raise GuppyError(InvalidUnitaryMethodError(node, node.name, class_ast.name))

        # Check that no invalid metadata are present
        method_raw_def = method.wrapped
        if method_raw_def.unitary_flags != UnitaryFlags.NoFlags:
            raise GuppyError(
                UnexpectedError(
                    function_header_span(node),
                    "unitary flags",
                    unexpected_in="in the method `@guppy` decorator",
                ).add_sub_diagnostic(InvalidUnitaryMetadataHelp(None))
            )

        if (
            method_raw_def.metadata is not None
            and method_raw_def.metadata.get_expected_qubits() is not None
        ):
            raise GuppyError(
                UnexpectedError(
                    function_header_span(node), "`@expected_qubits` decorator"
                ).add_sub_diagnostic(InvalidExpectedQubit(None))
            )
        custom_methods[CustomModifierKind(node.name)] = method_raw_def
    return custom_methods
