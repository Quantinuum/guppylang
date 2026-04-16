import warnings
from typing import Any, cast

from guppylang_internals.nodes import DummyGenericParamValue, GlobalName


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
