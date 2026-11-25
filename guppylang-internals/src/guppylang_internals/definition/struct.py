import ast
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from hugr import Wire

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Globals
from guppylang_internals.checker.errors.generic import (
    ExpectedError,
    UnexpectedError,
    UnsupportedError,
)
from guppylang_internals.compiler.builder.ops import make_tuple
from guppylang_internals.compiler.core import GlobalConstId
from guppylang_internals.definition.common import (
    CheckableDef,
    CompiledDef,
    DefId,
    ParsableDef,
    UserProvidedLinkName,
)
from guppylang_internals.definition.custom import (
    CustomCallCompiler,
    CustomFunctionDef,
    OwnedArgumentsCallChecker,
)
from guppylang_internals.definition.parameter import ParamDef
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.util import (
    CheckedField,
    DuplicateFieldError,
    NonGuppyMethodError,
    ProtocolHint,
    UncheckedField,
    check_not_recursive,
    extract_generic_params,
    is_guppy_unitary,
    parse_py_class,
)
from guppylang_internals.diagnostic import Error, Help
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.span import (
    SourceMap,
    class_header_span,
    extract_header_span,
    function_header_span,
)
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter, check_all_args
from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast
from guppylang_internals.tys.protocol import ProtocolInst
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    StructType,
    Type,
    UnitaryFlags,
)


@dataclass(frozen=True)
class FieldFormHint(Help):
    message: ClassVar[str] = (
        "Struct can contain only fields of the form `name: Type`, "
        "`@guppy` annotated methods or `@guppy.unitary` classes"
    )


@dataclass(frozen=True)
class StructBaseHint(Help):
    message: ClassVar[str] = "Structs can only use protocols as their base classes"


@dataclass(frozen=True)
class StructRequiredHint(Help):
    message: ClassVar[str] = (
        "Structs can't require methods, only protocols require methods. "
        "Maybe you meant `@guppy.declare`"
    )


@dataclass(frozen=True)
class RawStructDef(TypeDef, ParsableDef, UserProvidedLinkName):
    """A raw struct type definition that has not been parsed yet."""

    python_class: type
    frozen: bool
    params: None = field(default=None, init=False)  # Params not known yet

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedStructDef":
        """Parses the raw class object into an AST and checks that it is well-formed."""
        frame = DEF_STORE.frames[self.id]
        cls_def = parse_py_class(self.python_class, frame, sources)
        if cls_def.keywords:
            raise GuppyError(UnexpectedError(cls_def.keywords[0], "keyword"))

        params, bases = extract_generic_params(cls_def, self.name, globals)

        from guppylang.defs import GuppyDefinition

        from guppylang_internals.tys.parsing import parse_bound

        param_var_mapping = {param.name: param for param in params}
        must_implement: list[ProtocolInst] = []
        for p in bases:
            if try_parse_generic_base(p, "Protocol"):
                err = UnsupportedError(p, "Protocol base", singular=True)
                err.add_sub_diagnostic(ProtocolHint(None))
                raise GuppyError(err)
            proto = parse_bound(p, globals, param_var_mapping, False)
            if proto is None:
                err = UnsupportedError(p, "Bases of this kind")
                err.add_sub_diagnostic(StructBaseHint(None))
                raise GuppyError(err)
            must_implement.append(proto)

        fields: list[UncheckedField] = []
        used_field_names: set[str] = set()
        used_func_names: dict[str, ast.FunctionDef | ast.ClassDef] = {}
        for i, node in enumerate(cls_def.body):
            match i, node:
                # We allow `pass` statements to define empty structs
                case _, ast.Pass():
                    pass
                # Docstrings are also fine if they occur at the start
                case 0, ast.Expr(value=ast.Constant(value=v)) if isinstance(v, str):
                    pass
                # Ensure that function definitions are valid
                case _, ast.FunctionDef(name=name) as node:
                    v = getattr(self.python_class, name)
                    # Function definitions must be Guppy functions
                    if not isinstance(v, GuppyDefinition):
                        raise GuppyError(
                            NonGuppyMethodError(
                                node, self.name, name, "struct", "@guppy"
                            )
                        )
                    # Structs can't require functions
                    from guppylang_internals.definition.declaration import (
                        RawRequiredFunction,
                    )

                    if isinstance(v.wrapped, RawRequiredFunction):
                        err = UnexpectedError(
                            node, "required function", unexpected_in="a struct"
                        )
                        err.add_sub_diagnostic(StructRequiredHint(None))
                        raise GuppyError(err)
                    # Prevent duplicate names
                    used_func_names[name] = node
                    if name in used_field_names:
                        raise GuppyError(
                            DuplicateFieldError(
                                function_header_span(node), self.name, name, "struct"
                            )
                        )
                # A `@guppy.unitary` method is written as a class, but the decorator
                # replaces it with its `__call__` Guppy function definition.
                case _, ast.ClassDef(name=name) as node:
                    v = getattr(self.python_class, name)
                    if not is_guppy_unitary(v):
                        err = UnexpectedError(
                            node,
                            "statement",
                            unexpected_in="struct definition",
                        )
                        err.add_sub_diagnostic(FieldFormHint(None))
                        raise GuppyError(err)
                    used_func_names[name] = node
                    if name in used_field_names:
                        raise GuppyError(
                            DuplicateFieldError(
                                class_header_span(node), self.name, name, "struct"
                            )
                        )
                # Struct fields are declared via annotated assignments without value
                case _, ast.AnnAssign(target=ast.Name(id=field_name)) as node:
                    if node.value:
                        raise GuppyError(
                            UnsupportedError(node.value, "Default struct values")
                        )
                    if field_name in used_field_names:
                        raise GuppyError(
                            DuplicateFieldError(
                                node.target, self.name, field_name, "struct"
                            )
                        )
                    fields.append(UncheckedField(field_name, node.annotation))
                    used_field_names.add(field_name)
                case _, node:
                    err = UnexpectedError(
                        node,
                        "statement",
                        unexpected_in="struct definition",
                    )
                    err.add_sub_diagnostic(FieldFormHint(None))
                    raise GuppyError(err)

        # Ensure that functions don't override struct fields
        if overridden := used_field_names.intersection(used_func_names.keys()):
            x = overridden.pop()
            error_ast = used_func_names[x]
            error_span = extract_header_span(error_ast)
            raise GuppyError(DuplicateFieldError(error_span, self.name, x, "struct"))

        link_name_prefix = (
            self._user_set_link_name
            or f"{self.python_class.__module__}.{self.python_class.__qualname__}"
        )

        return ParsedStructDef(
            self.id,
            self.name,
            cls_def,
            params,
            must_implement,
            fields,
            self.frozen,
            link_name_prefix,
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        raise InternalGuppyError("Tried to instantiate raw struct definition")


@dataclass(frozen=True)
class ParsedStructDef(TypeDef, CheckableDef):
    """A struct definition whose fields have not been checked yet."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    must_implement: Sequence[ProtocolInst]
    fields: Sequence[UncheckedField]
    frozen: bool
    link_name_prefix: str

    def check(self, globals: Globals) -> "CheckedStructDef":
        """Checks that all struct fields have valid types."""
        param_var_mapping = {p.name: p for p in self.params}
        ctx = TypeParsingCtx(
            globals,
            param_var_mapping,
            is_signature=self.id,
            disallow_protocol_types=True,
        )

        # Before checking the fields, make sure that this definition is not recursive,
        # otherwise the code below would not terminate.
        check_not_recursive(self, ctx)

        fields = [
            CheckedField(f.name, type_from_ast(f.type_ast, ctx)) for f in self.fields
        ]
        return CheckedStructDef(
            self.id,
            self.name,
            self.defined_at,
            self.params,
            self.must_implement,
            fields,
            self.frozen,
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        """Checks if the struct can be instantiated with the given arguments."""
        check_all_args(self.params, args, self.name, loc)
        # Obtain a checked version of this struct definition so we can construct a
        # `StructType` instance
        globals = Globals(DEF_STORE.frames[self.id])
        # TODO: This is quite bad: If we have a cyclic definition this will not
        #  terminate, so we have to check for cycles in every call to `check`. The
        #  proper way to deal with this is changing `StructType` such that it only
        #  takes a `DefId` instead of a `CheckedStructDef`. But this will be a bigger
        #  refactor...
        checked_def = self.check(globals)
        return StructType(args, checked_def)


@dataclass(frozen=True)
class CheckedStructDef(TypeDef, CompiledDef):
    """A struct definition that has been fully checked."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    must_implement: Sequence[ProtocolInst]
    fields: Sequence[CheckedField]
    frozen: bool

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        """Checks if the struct can be instantiated with the given arguments."""
        check_all_args(self.params, args, self.name, loc)
        return StructType(args, self)

    def generated_methods(self) -> list[CustomFunctionDef]:
        """Auto-generated methods for this struct."""

        class ConstructorCompiler(CustomCallCompiler):
            """Compiler for the `__new__` constructor method of a struct."""

            def compile(self, args: list[Wire]) -> list[Wire]:
                return list(self.builder.add_op(make_tuple(), *args))

        constructor_sig = FunctionType(
            inputs=[
                FuncInput(
                    f.ty,
                    InputFlags.Owned if f.ty.linear else InputFlags.NoFlags,
                    f.name,
                )
                for f in self.fields
            ],
            output=StructType(
                defn=self, args=[p.to_bound(i) for i, p in enumerate(self.params)]
            ),
            params=self.params,
            unitary_flags=UnitaryFlags.Dagger,
        )
        constructor_def = CustomFunctionDef(
            id=DefId.fresh(),
            name="__new__",
            defined_at=self.defined_at,
            ty=constructor_sig,
            is_static=True,
            call_checker=OwnedArgumentsCallChecker(),
            call_compiler=ConstructorCompiler(),
            higher_order_value=True,
            higher_order_func_id=GlobalConstId.fresh(f"{self.name}.__new__"),
            has_signature=True,
            has_var_args=False,
            effects=(),  # TODO revisit once the generated constructor invokes others
        )
        return [constructor_def]

    def post_validate(self) -> None:
        """Validation checks which can only be done after the def is registered.

        Any check which isn't necessary for the definition to make computational
        sense can go here. Any sanity check, adherence to contracts, etc…
        """
        # Checking that the struct implements its declared protocols. This needs
        # to be in the post-validate phase because `check_protocol` will call
        # back into `get_checked`. Now that the struct is registered,
        # `get_checked` will return immediately. An earlier check (_e.g._ in the
        # `check` method of `ParsedStructDef`) would result in an infinite
        # recursion.

        # We can only check protocols with fully instantiated type. So we create
        # an instantiated type by instantiating the parameters with bound
        # variables.
        symbolic_args = [p.to_bound(i) for i, p in enumerate(self.params)]
        symbolic = StructType(symbolic_args, self)

        for proto in self.must_implement:
            proto.check_implemented_by(symbolic, class_header_span(self.defined_at))


def try_parse_generic_base(node: ast.expr, base_name: str) -> list[ast.expr] | None:
    """Checks if an AST node corresponds to a `base_name[T1, ..., Tn]` base class.

    Returns the generic parameters or `None` if the AST has a different shape
    """
    match node:
        case ast.Subscript(value=ast.Name(id=name), slice=elem) if base_name == name:
            return elem.elts if isinstance(elem, ast.Tuple) else [elem]
        case _:
            return None


@dataclass(frozen=True)
class RepeatedTypeParamError(Error):
    title: ClassVar[str] = "Duplicate type parameter"
    span_label: ClassVar[str] = "Type parameter `{name}` cannot be used multiple times"
    name: str


def params_from_ast(nodes: Sequence[ast.expr], globals: Globals) -> list[Parameter]:
    """Parses a list of AST nodes into unique type parameters.

    Raises user errors if the AST nodes don't correspond to parameters or parameters
    occur multiple times.
    """
    params: list[Parameter] = []
    params_set: set[DefId] = set()
    for node in nodes:
        if isinstance(node, ast.Name) and node.id in globals:
            defn = globals[node.id]
            if isinstance(defn, ParamDef):
                if defn.id in params_set:
                    raise GuppyError(RepeatedTypeParamError(node, node.id))
                params.append(defn.to_param(len(params)))
                params_set.add(defn.id)
                continue
        raise GuppyError(ExpectedError(node, "a type parameter"))
    return params
