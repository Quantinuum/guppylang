import json
from pathlib import Path

from auto_hugr_ext import generate_new_hugr_ext, register_extension
from auto_hugr_ext.harvest import load_module
from guppylang import guppy
from guppylang_internals.engine import ENGINE
from hugr.ext import Extension

SOURCE = Path(__file__).parent / "dummy_container" / "linear_container.py"


def test_generate_hugr_extension(tmp_path: Path) -> None:
    out = tmp_path / "dummy.json"
    extension = generate_new_hugr_ext(SOURCE, "dummy.container", out)

    assert isinstance(extension, Extension)
    assert extension.name == "dummy.container"
    assert set(extension.types) == {"LinearContainer"}
    assert set(extension.operations) == {
        "consume",
        "make_container",
        "make_dummy_action",
    }
    assert json.loads(out.read_text(encoding="utf-8")) == json.loads(
        extension.to_json()
    )
    assert Extension.from_json(out.read_text(encoding="utf-8")).name == extension.name


def test_register_extension_with_guppy() -> None:
    extension = generate_new_hugr_ext(SOURCE, "dummy.container")
    module = load_module(SOURCE)
    make_container = module.make_container
    try:
        register_extension(extension)
        register_extension(extension)
        assert extension in ENGINE.additional_extensions
        assert (
            sum(
                ext.name == extension.name and ext.version == extension.version
                for ext in ENGINE.additional_extensions
            )
            == 1
        )

        @guppy
        def consume_container(value: int) -> int:
            return make_container(value).consume()

        consume_container.compile_function()
    finally:
        ENGINE.additional_extensions[:] = [
            ext for ext in ENGINE.additional_extensions if ext is not extension
        ]
