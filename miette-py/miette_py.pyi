class PyDiagnostic:
    def __init__(
        self,
        message: str,
        code: str | None,
        severity: str,
        source: str | None,
        spans: list[tuple[int, int, str | None]],
        help_text: str | None,
    ) -> None: ...

def render_report(diagnostic: PyDiagnostic) -> str: ...
def guppy_to_miette(
    title: str,
    level: str,
    source_text: str | None,
    spans: list[tuple[int, int, str | None]],
    message: str | None,
    help_text: str | None,
) -> PyDiagnostic: ...
