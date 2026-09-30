from pathlib import Path

from auto_hugr_ext import generate_new_hugr_ext

generate_new_hugr_ext(Path(__file__).parent / "linear_container.py", "dummy.container")
