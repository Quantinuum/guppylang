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
        super().__init__(str(underlying_exception))
        self.completed_shots = completed_shots
        self.failing_shot = failing_shot
        self.underlying_exception = underlying_exception

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
