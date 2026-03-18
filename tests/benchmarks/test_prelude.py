def test_import_guppy(benchmark):
    def setup_guppy():
        import guppylang.std.quantum.functional as qf  # noqa: F401
        from guppylang.decorator import guppy
        from guppylang.module import GuppyModule  # noqa: F401
        from guppylang.std.angles import angle, pi  # noqa: F401
        from guppylang.std.builtins import array, py  # noqa: F401

        from guppylang.std import quantum  # noqa: F401
        from guppylang.std.quantum import cx, discard_array, h, qubit  # noqa: F401

        @guppy
        def main() -> None:
            return

    benchmark(setup_guppy)
