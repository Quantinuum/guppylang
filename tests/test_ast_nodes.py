import ast
import warnings
from typing import Any, cast

from guppylang_internals.ast_util import annotate_location
from guppylang_internals.nodes import (
    Control,
    Dagger,
    DummyGenericParamValue,
    GlobalName,
    NestedFunctionDef,
    Power,
)


def test_name_subclasses_do_not_emit_python_315_constructor_warnings() -> None:
    def_id = cast("Any", object())
    var = cast("Any", object())

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        global_name = GlobalName("foo", def_id)
        generic_param = DummyGenericParamValue("bar", var)

    assert global_name.def_id is def_id
    assert generic_param.var is var
    assert not [w for w in caught if issubclass(w.category, DeprecationWarning)]


def test_modifier_nodes_do_not_emit_python_315_constructor_warnings() -> None:
    dagger_stmt = cast("ast.Expr", ast.parse("dagger").body[0])
    control_stmt = cast("ast.Expr", ast.parse("control(q1, q2)").body[0])
    power_stmt = cast("ast.Expr", ast.parse("power(n)").body[0])
    dagger_expr = dagger_stmt.value
    control_expr = control_stmt.value
    power_expr = power_stmt.value
    assert isinstance(dagger_expr, ast.expr)
    assert isinstance(control_expr, ast.Call)
    assert isinstance(power_expr, ast.Call)

    for node, source in [
        (dagger_expr, "dagger"),
        (control_expr, "control(q1, q2)"),
        (power_expr, "power(n)"),
    ]:
        annotate_location(node, source, "test.py", 0, recurse=False)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        dagger = Dagger(dagger_expr)
        control = Control(control_expr, control_expr.args)
        power = Power(power_expr, power_expr.args[0])

    assert control.func is control_expr.func
    assert control.args == control_expr.args
    assert control.ctrl == control_expr.args
    assert power.iter is power_expr.args[0]
    assert dagger.lineno == dagger_expr.lineno
    assert not [w for w in caught if issubclass(w.category, DeprecationWarning)]


def test_nested_function_def_does_not_emit_python_315_constructor_warnings() -> None:
    func_stmt = cast(
        "ast.FunctionDef",
        ast.parse("def inner() -> None:\n    pass\n").body[0],
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        nested = NestedFunctionDef(
            cast("Any", object()),
            cast("Any", object()),
            docstring=None,
            **dict(ast.iter_fields(func_stmt)),
        )

    assert nested.name == func_stmt.name
    assert nested.args == func_stmt.args
    assert nested.body == func_stmt.body
    assert not [w for w in caught if issubclass(w.category, DeprecationWarning)]
