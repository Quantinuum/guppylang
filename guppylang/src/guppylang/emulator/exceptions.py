from hugr.qsystem.result import QsysShot

from .result import EmulatorResult


class EmulatorError(Exception):
    completed_shots: EmulatorResult
    failing_shot: QsysShot
    underlying_exception: Exception | None

    def __init__(
        self,
        completed_shots: EmulatorResult,
        failing_shot: QsysShot,
        underlying_exception: Exception | None = None,
    ):
        super().__init__(self._render_message(underlying_exception))
        self.completed_shots = completed_shots
        self.failing_shot = failing_shot
        self.underlying_exception = underlying_exception

    @staticmethod
    def _render_message(underlying_exception: Exception | None) -> str:
        if underlying_exception is None:
            return ""
        stack_trace = getattr(underlying_exception, "stack_trace", None)
        if stack_trace is not None:
            from .stack_trace import render_stack_trace

            message = getattr(
                underlying_exception, "message", str(underlying_exception)
            )
            rendered = render_stack_trace(stack_trace, message)
            if rendered is not None:
                header = EmulatorError._panic_header(underlying_exception)
                return f"{header}\n{rendered}"
        return str(underlying_exception)

    @staticmethod
    def _panic_header(underlying_exception: Exception) -> str:
        code = getattr(underlying_exception, "code", None)
        message = getattr(underlying_exception, "message", str(underlying_exception))
        if isinstance(code, int):
            return f"Panic (#{code}): {message}"
        return str(underlying_exception)

    @property
    def failed_shot_index(self) -> int:
        """The index of the shot that failed."""
        return len(self.completed_shots.results)


class EmulatorBuildError(Exception):
    underlying_exception: Exception | None

    def __init__(self, underlying_exception: Exception | None = None):
        super().__init__(
            "Building the emulator failed with the following exception: "
            + str(underlying_exception)
        )
        self.underlying_exception = underlying_exception
