import ast
import builtins
import inspect
from collections.abc import Callable, Sequence
from types import FrameType
from typing import Any, ParamSpec, TypedDict, TypeVar, cast, overload

from guppylang_internals.ast_util import annotate_location
from guppylang_internals.compiler.core import (
    CompilerContext,
)
from guppylang_internals.decorator import (
    custom_function,
    custom_type,
    hugr_op,
)
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.const import RawConstDef
from guppylang_internals.definition.custom import (
    CustomCallChecker,
    CustomInoutCallCompiler,
    RawCustomFunctionDef,
)
from guppylang_internals.definition.declaration import RawFunctionDecl
from guppylang_internals.definition.extern import RawExternDef
from guppylang_internals.definition.function import (
    RawFunctionDef,
)
from guppylang_internals.definition.metadata import GuppyMetadata
from guppylang_internals.definition.overloaded import OverloadedFunctionDef
from guppylang_internals.definition.parameter import (
    ConstVarDef,
    RawConstVarDef,
    TypeVarDef,
)
from guppylang_internals.definition.pytket_circuits import (
    RawLoadPytketDef,
    RawPytketDef,
)
from guppylang_internals.definition.struct import RawStructDef
from guppylang_internals.definition.traced import RawTracedFunctionDef
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.dummy_decorator import _DummyGuppy, sphinx_running
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.span import Loc, SourceMap, Span
from guppylang_internals.tracing.util import hide_trace
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.subst import Inst
from guppylang_internals.tys.ty import (
    FunctionType,
    NoneType,
    NumericType,
    UnitaryFlags,
)
from hugr import ops
from hugr import tys as ht
from hugr import val as hv
from hugr.package import ModulePointer
from typing_extensions import Unpack, dataclass_transform, deprecated

from guppylang.defs import (
    GuppyDefinition,
    GuppyFunctionDefinition,
    GuppyTypeVarDefinition,
)

S = TypeVar("S")
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])
P = ParamSpec("P")
Decorator = Callable[[S], T]

AnyRawFunctionDef = (
    RawFunctionDef,
    RawCustomFunctionDef,
    RawFunctionDecl,
    RawPytketDef,
    RawLoadPytketDef,
    OverloadedFunctionDef,
)

__all__ = ("guppy", "custom_guppy_decorator", "GuppyKwargs")


class GuppyKwargs(TypedDict, total=False):
    """Typed dictionary specifying the optional keyword arguments for the `@guppy`
    decorator.
    """

    unitary: bool
    control: bool
    dagger: bool
    power: bool
    max_qubits: int


class _Guppy:
    """Class for the `@guppy` decorator."""

    @overload
    def __call__(
        self, /, **kwargs: Unpack[GuppyKwargs]
    ) -> Decorator[Callable[P, T], GuppyFunctionDefinition[P, T]]: ...

    @overload
    def __call__(self, f: Callable[P, T], /) -> GuppyFunctionDefinition[P, T]: ...

    def __call__(
        self, *args: Any, **kwargs: Unpack[GuppyKwargs]
    ) -> (
        GuppyFunctionDefinition[P, T]
        | Decorator[Callable[P, T], GuppyFunctionDefinition[P, T]]
    ):
        def dec(
            f: Callable[P, T], kwargs: GuppyKwargs
        ) -> GuppyFunctionDefinition[P, T]:
            flags, metadata = _parse_kwargs(kwargs)
            defn = RawFunctionDef(
                DefId.fresh(),
                f.__name__,
                None,
                f,
                unitary_flags=flags,
                metadata=metadata,
            )
            DEF_STORE.register_def(defn, get_calling_frame())
            return GuppyFunctionDefinition(defn)

        return _with_optional_kwargs(dec, args, kwargs)

    @overload
    def comptime(
        self, /, **kwargs: Unpack[GuppyKwargs]
    ) -> Decorator[Callable[P, T], GuppyFunctionDefinition[P, T]]: ...

    @overload
    def comptime(self, f: Callable[P, T], /) -> GuppyFunctionDefinition[P, T]: ...

    def comptime(
        self, *args: Any, **kwargs: Unpack[GuppyKwargs]
    ) -> (
        GuppyFunctionDefinition[P, T]
        | Decorator[Callable[P, T], GuppyFunctionDefinition[P, T]]
    ):
        """Registers a function to be executed at compile-time during Guppy compilation,
        enabling the use of arbitrary Python features as long as they don't depend on
        runtime values.

        .. code-block:: python
            from guppylang import guppy
            from guppylang.std.builtins import array

            @guppy.comptime
            def print_arrays(arr1: array[str, 10], arr2: array[str, 10]) -> None:
                for s1, s2 in zip(arr1, arr2):
                    print(f"({s1}, {s2})")
        """

        def dec(
            f: Callable[P, T], kwargs: GuppyKwargs
        ) -> GuppyFunctionDefinition[P, T]:
            _ = _parse_kwargs(kwargs)  # TODO: Pass flags to RawTracedFunctionDef
            defn = RawTracedFunctionDef(DefId.fresh(), f.__name__, None, f)
            DEF_STORE.register_def(defn, get_calling_frame())
            return GuppyFunctionDefinition(defn)

        return _with_optional_kwargs(dec, args, kwargs)

    @deprecated("Use @guppylang_internal.decorator.extend_type instead.")
    def extend_type(self, defn: TypeDef) -> Callable[[type], type]:
        # Set `return_class=True` to match the old behaviour until this deprecated
        # method is removed
        import guppylang_internals.decorator

        return guppylang_internals.decorator.extend_type(defn, return_class=True)

    @deprecated("Use @guppylang_internal.decorator.custom_type instead.")
    def type(
        self,
        hugr_ty: ht.Type | Callable[[Sequence[Argument], CompilerContext], ht.Type],
        name: str = "",
        copyable: bool = True,
        droppable: bool = True,
        bound: ht.TypeBound | None = None,
        params: Sequence[Parameter] | None = None,
    ) -> Callable[[type[T]], type[T]]:
        return custom_type(hugr_ty, name, copyable, droppable, bound, params)

    @dataclass_transform()
    def struct(self, cls: builtins.type[T]) -> builtins.type[T]:
        """Registers a class as a Guppy struct.

        .. code-block:: python
            from guppylang import guppy

            @guppy.struct
            class MyStruct:
                field1: int
                field2: int

            @guppy
            def add_fields(self: "MyStruct") -> int:
                return self.field2 + self.field2
        """
        defn = RawStructDef(DefId.fresh(), cls.__name__, None, cls)
        frame = get_calling_frame()
        DEF_STORE.register_def(defn, frame)
        for val in cls.__dict__.values():
            if isinstance(val, GuppyDefinition):
                DEF_STORE.register_impl(defn.id, val.wrapped.name, val.id)
        # Prior to Python 3.13, the `__firstlineno__` attribute on classes is not set.
        # However, we need this information to precisely look up the source for the
        # class later. If it's not there, we can set it from the calling frame:
        if not hasattr(cls, "__firstlineno__"):
            cls.__firstlineno__ = frame.f_lineno  # type: ignore[attr-defined]
        # We're pretending to return the class unchanged, but in fact we return
        # a `GuppyDefinition` that handles the comptime logic
        return GuppyDefinition(defn)  # type: ignore[return-value]

    def type_var(
        self,
        name: str,
        copyable: bool = True,
        droppable: bool = True,
    ) -> TypeVar:
        """Creates a new type variable.

        .. code-block:: python
            from guppylang import guppy

            T = guppy.type_var("T")

            @guppy
            def identity(x: T) -> T:
                return x
        """
        defn = TypeVarDef(DefId.fresh(), name, None, copyable, droppable)
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return a `typing.TypeVar`, but in fact we return a special
        # `GuppyDefinition` that pretends to be a TypeVar at runtime
        return GuppyTypeVarDefinition(defn, TypeVar(name))  # type: ignore[return-value]

    def nat_var(self, name: str) -> TypeVar:
        """Creates a new nat variable."""
        defn = ConstVarDef(DefId.fresh(), name, None, NumericType(NumericType.Kind.Nat))
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return a `typing.TypeVar`, but in fact we return a special
        # `GuppyDefinition` that pretends to be a TypeVar at runtime
        return GuppyTypeVarDefinition(defn, TypeVar(name))  # type: ignore[return-value]

    def const_var(self, name: str, ty: str) -> TypeVar:
        """Creates a new const type variable."""
        type_ast = _parse_expr_string(
            ty, f"Not a valid Guppy type: `{ty}`", DEF_STORE.sources
        )
        defn = RawConstVarDef(DefId.fresh(), name, None, type_ast)
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return a `typing.TypeVar`, but in fact we return a special
        # `GuppyDefinition` that pretends to be a TypeVar at runtime
        return GuppyTypeVarDefinition(defn, TypeVar(name))  # type: ignore[return-value]

    @deprecated("Use @guppylang_internal.decorator.custom_function instead.")
    def custom(
        self,
        compiler: CustomInoutCallCompiler | None = None,
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
        signature: FunctionType | None = None,
    ) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
        return custom_function(compiler, checker, higher_order_value, name, signature)

    @deprecated("Use @guppylang_internal.decorator.hugr_op instead.")
    def hugr_op(
        self,
        op: Callable[[ht.FunctionType, Inst, CompilerContext], ops.DataflowOp],
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
        signature: FunctionType | None = None,
    ) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
        return hugr_op(op, checker, higher_order_value, name, signature)

    @overload
    def declare(
        self, /, **kwargs: Unpack[GuppyKwargs]
    ) -> Decorator[Callable[P, T], GuppyFunctionDefinition[P, T]]: ...

    @overload
    def declare(self, f: Callable[P, T], /) -> GuppyFunctionDefinition[P, T]: ...

    def declare(
        self, *args: Any, **kwargs: Unpack[GuppyKwargs]
    ) -> (
        GuppyFunctionDefinition[P, T]
        | Decorator[Callable[P, T], GuppyFunctionDefinition[P, T]]
    ):
        """Declares a Guppy function without defining it."""

        def dec(
            f: Callable[P, T], kwargs: GuppyKwargs
        ) -> GuppyFunctionDefinition[P, T]:
            flags, _ = _parse_kwargs(kwargs)
            defn = RawFunctionDecl(
                DefId.fresh(), f.__name__, None, f, unitary_flags=flags
            )
            DEF_STORE.register_def(defn, get_calling_frame())
            return GuppyFunctionDefinition(defn)

        return _with_optional_kwargs(dec, args, kwargs)

    def overload(
        self, *funcs: Any
    ) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
        """Collects multiple function definitions into one overloaded function.

        Consider the following example:

        .. code-block:: python

            @guppy.declare
            def variant1(x: int, y: int) -> int: ...

            @guppy.declare
            def variant2(x: float) -> int: ...

            @guppy.overload(variant1, variant2)
            def combined(): ...


        Now, `combined` may be called with either one `float` or two `int` arguments,
        delegating to the implementation with the matching signature:

        .. code-block:: python

            combined(4.2)  # Calls `variant1`
            combined(42, 43)  # Calls `variant2`


        Note that the compiler will pick the *first* implementation with matching
        signature and ignore all following ones, even if they would also match. For
        example, if we added a third variant

        .. code-block:: python

            @guppy.declare
            def variant3(x: int) -> int: ...

            @guppy.overload(variant1, variant2, variant3)
            def combined_new(): ...

        then a call `combined_new(42)` will still select the `variant1` implementation
        `42` is a valid argument for `variant1` and `variant1` comes before `variant3`
        in the `@guppy.overload` annotation.
        """
        funcs = list(funcs)
        if len(funcs) < 2:
            raise ValueError("Overload requires at least two functions")
        func_ids = []
        for func in funcs:
            if not isinstance(func, GuppyDefinition):
                raise TypeError(f"Not a Guppy definition: {func}")
            if not isinstance(func.wrapped, AnyRawFunctionDef):
                raise TypeError(
                    f"Not a Guppy function definition: {func.wrapped.description} "
                    f"`{func.wrapped.name}`"
                )
            func_ids.append(func.id)

        def dec(f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
            dummy_sig = FunctionType([], NoneType())
            defn = OverloadedFunctionDef(
                DefId.fresh(), f.__name__, None, dummy_sig, func_ids
            )
            DEF_STORE.register_def(defn, get_calling_frame())
            return GuppyFunctionDefinition(defn)

        return dec

    def constant(self, name: str, ty: str, value: hv.Value) -> T:  # type: ignore[type-var]  # Since we're returning a free type variable
        """Adds a constant to a module, backed by a `hugr.val.Value`."""
        type_ast = _parse_expr_string(
            ty, f"Not a valid Guppy type: `{ty}`", DEF_STORE.sources
        )
        defn = RawConstDef(DefId.fresh(), name, None, type_ast, value)
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return a free type variable, but in fact we return
        # a `GuppyDefinition` that handles the comptime logic
        return GuppyDefinition(defn)  # type: ignore[return-value]

    def _extern(
        self,
        name: str,
        ty: str,
        symbol: str | None = None,
        constant: bool = True,
    ) -> T:  # type: ignore[type-var]  # Since we're returning a free type variable
        """Adds an extern symbol to a module."""
        type_ast = _parse_expr_string(
            ty, f"Not a valid Guppy type: `{ty}`", DEF_STORE.sources
        )
        defn = RawExternDef(
            DefId.fresh(), name, None, symbol or name, constant, type_ast
        )
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return a free type variable, but in fact we return
        # a `GuppyDefinition` that handles the comptime logic
        return GuppyDefinition(defn)  # type: ignore[return-value]

    @deprecated(
        "guppy.compile(foo) is deprecated and will be removed in a future version:"
        " use foo.compile() instead."
    )
    def compile(self, obj: Any) -> ModulePointer:
        """Compiles a Guppy definition to Hugr."""

        if not isinstance(obj, GuppyDefinition):
            raise TypeError(f"Object is not a Guppy definition: {obj}")
        return ModulePointer(obj.compile(), 0)

    def pytket(
        self, input_circuit: Any
    ) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
        """Backs a function declaration by the given pytket circuit. The declaration
        signature needs to match the circuit definition in terms of number of qubit
        inputs and measurement outputs.

        There is no linearity checking inside pytket circuit functions. Any measurements
        inside the circuit get returned as bools, but the qubits do not get consumed and
        the  pytket circuit function does not require ownership. You should either make
        sure you discard all qubits you know are measured during the circuit, or avoid
        measurements in the circuit and measure in Guppy afterwards.

        Note this decorator doesn't support passing inputs as arrays (use `load_pytket`
        instead).

        .. code-block:: python
            from pytket import Circuit
            from guppylang import guppy

            circ = Circuit(1)
            circ.H(0)
            circ.measure_all()

            @guppy.pytket(circ)
            def guppy_circ(q: qubit) -> bool: ...

            @guppy
            def foo(q: qubit) -> bool:
                return guppy_circ(q)"""

        err_msg = "Only pytket circuits can be passed to guppy.pytket"
        try:
            import pytket

            if not isinstance(input_circuit, pytket.circuit.Circuit):
                raise TypeError(err_msg) from None

        except ImportError:
            raise TypeError(err_msg) from None

        def func(f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
            defn = RawPytketDef(DefId.fresh(), f.__name__, None, f, input_circuit)
            DEF_STORE.register_def(defn, get_calling_frame())
            return GuppyFunctionDefinition(defn)

        return func

    def load_pytket(
        self,
        name: str,
        input_circuit: Any,
        *,
        use_arrays: bool = True,
    ) -> GuppyFunctionDefinition[..., Any]:
        """Load a pytket :py:class:`~pytket.circuit.Circuit` as a Guppy function. By
        default, each qubit register is represented by an array input (and each bit
        register as an array output), with the order being determined lexicographically.
        The default registers are 'q' and 'c' respectively. You can disable array usage
        and pass individual qubits by passing `use_arrays=False`.

        .. code-block:: python

            from pytket import Circuit
            from guppylang import guppy

            circ = Circuit(2)
            reg = circ.add_q_register("extra_reg", 3)
            circ.measure_register(reg, "extra_bits")

            guppy_circ = guppy.load_pytket("guppy_circ", circ)

            @guppy
            def foo(default_reg: array[qubit, 2],
                    extra_reg: array[qubit, 3]) -> array[bool, 3]:
                # Note that the default_reg name is 'q' so it has to come after 'e...'
                # lexicographically.
                return guppy_circ(extra_reg, default_reg)

        Any symbolic parameters in the circuit need to be passed as a lexicographically
        sorted array (if arrays are enabled, else individually in that order) as values
        of type `angle`.

        The function name is determined by the function variable you bind the `
        load_pytket`method call to, however the name string passed to the method should
        match this variable for error reporting purposes.

        There is no linearity checking inside pytket circuit functions. Any measurements
        inside the circuit get returned as bools, but the qubits do not get consumed and
        the  pytket circuit function does not require ownership. You should either make
        sure you discard all qubits you know are measured during the circuit, or avoid
        measurements in the circuit and measure in Guppy afterwards.
        """

        err_msg = "Only pytket circuits can be passed to guppy.load_pytket"
        try:
            import pytket

            if not isinstance(input_circuit, pytket.circuit.Circuit):
                raise TypeError(err_msg) from None

        except ImportError:
            raise TypeError(err_msg) from None

        span = _find_load_call(DEF_STORE.sources)
        defn = RawLoadPytketDef(
            DefId.fresh(), name, None, span, input_circuit, use_arrays
        )
        DEF_STORE.register_def(defn, get_calling_frame())
        return GuppyFunctionDefinition(defn)


def _parse_expr_string(ty_str: str, parse_err: str, sources: SourceMap) -> ast.expr:
    """Helper function to parse expressions that are provided as strings.

    Tries to infer the source location were the given string was defined by inspecting
    the call stack.
    """
    try:
        expr_ast = ast.parse(ty_str, mode="eval").body
    except SyntaxError:
        raise SyntaxError(parse_err) from None

    # Try to annotate the type AST with source information. This requires us to
    # inspect the stack frame of the caller
    if caller_frame := get_calling_frame():
        info = inspect.getframeinfo(caller_frame)
        if caller_module := inspect.getmodule(caller_frame):
            sources.add_file(info.filename)
            source_lines, _ = inspect.getsourcelines(caller_module)
            source = "".join(source_lines)
            annotate_location(expr_ast, source, info.filename, 1)
            # Modify the AST so that all sub-nodes span the entire line. We
            # can't give a better location since we don't know the column
            # offset of the `ty` argument
            for node in [expr_ast, *ast.walk(expr_ast)]:
                node.lineno = node.end_lineno = info.lineno
                node.col_offset = 0
                node.end_col_offset = len(source_lines[info.lineno - 1]) - 1
    return expr_ast


def _find_load_call(sources: SourceMap) -> Span | None:
    """Helper function to find location where pytket circuit was loaded.

    Tries to define a source code span by inspecting the call stack.
    """
    # Go back as first frame outside of compiler modules is 'pretty_errors_wrapped'.
    if load_frame := get_calling_frame():
        info = inspect.getframeinfo(load_frame)
        filename = info.filename
        lineno = info.lineno
        sources.add_file(filename)
        # If we don't support python <= 3.10, this can be done better with
        # info.positions which gives you exact offsets.
        # For now over approximate and make the span cover the entire line.
        if load_module := inspect.getmodule(load_frame):
            source_lines, _ = inspect.getsourcelines(load_module)
            max_offset = len(source_lines[lineno - 1]) - 1

            start = Loc(filename, lineno, 0)
            end = Loc(filename, lineno, max_offset)
            return Span(start, end)
    return None


def custom_guppy_decorator(f: F) -> F:
    """Decorator to mark user-defined decorators that wrap builtin `guppy` decorators.

    Example:

    .. code-block:: python

        @custom_guppy_decorator
        def my_guppy(f):
            # Some custom logic here ...
            return guppy(f)

        @my_guppy
        def main() -> int: ...

    If the `custom_guppy_decorator` were missing, then the `@my_guppy` annotation would
    not produce a valid guppy definition.
    """
    f.__code__ = f.__code__.replace(co_name="__custom_guppy_decorator__")
    return f


def get_calling_frame() -> FrameType:
    """Finds the first frame that called this function outside the compiler modules."""
    frame = inspect.currentframe()
    while frame:
        # Skip frame if we're inside a user-defined decorator that wraps the `guppy`
        # decorator. Those are functions with a special `__code__.co_name` of
        # "__custom_guppy_decorator__".
        if frame.f_code.co_name == "__custom_guppy_decorator__":
            frame = frame.f_back
            continue
        module = inspect.getmodule(frame)
        if module is None:
            return frame
        if module.__file__ != __file__:
            return frame
        frame = frame.f_back
    raise RuntimeError("Couldn't obtain stack frame for definition")


def _with_optional_kwargs(
    decorator: Callable[[S, GuppyKwargs], T], args: tuple[Any, ...], kwargs: GuppyKwargs
) -> T | Callable[[S], T]:
    """Helper function to define decorators that may be used directly (`@decorator`) but
    also with optional keyword arguments (`@decorator(kwarg=value)`).
    """
    match args:
        case ():
            return lambda f: decorator(f, kwargs)
        case (f,):
            if kwargs:
                err = "Unexpected keyword arguments"
                raise TypeError(err)
            return decorator(f, kwargs)
        case _:
            err = "Unexpected positional arguments"
            raise TypeError(err)


@hide_trace
def _parse_kwargs(kwargs: GuppyKwargs) -> tuple[UnitaryFlags, GuppyMetadata]:
    """Parses the kwargs dict specified in the `@guppy` decorator into `UnitaryFlags`
    and other metadata that will be passed onto the compiled function as is.
    """
    flags = UnitaryFlags.NoFlags
    if kwargs.pop("unitary", False):
        flags |= UnitaryFlags.Unitary
    if kwargs.pop("control", False):
        flags |= UnitaryFlags.Control
    if kwargs.pop("dagger", False):
        flags |= UnitaryFlags.Dagger
    if kwargs.pop("power", False):
        flags |= UnitaryFlags.Power

    metadata = GuppyMetadata()
    metadata.max_qubits.value = kwargs.pop("max_qubits", None)

    if remaining := next(iter(kwargs), None):
        err = f"Unknown keyword argument: `{remaining}`"
        raise TypeError(err)
    return flags, metadata


guppy = cast(_Guppy, _DummyGuppy()) if sphinx_running() else _Guppy()
