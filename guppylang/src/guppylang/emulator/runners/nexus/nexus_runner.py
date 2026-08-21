"""NexusRunner for running programs on Nexus."""

import logging
import sys
import time
from typing import cast

import qnexus as qnx
import qnexus.exceptions as qnx_exc
from hugr.package import Package
from hugr.qsystem.result import QsysResult
from qnexus.models.job_status import WAITING_STATUS, JobStatus, JobStatusEnum
from qnexus.models.references import (
    CompilationResultRef,
    ExecutionResultRef,
    HUGRRef,
    IncompleteJobItemRef,
    JobRef,
)

from guppylang.defs import GuppyFunctionDefinition
from guppylang.emulator.runners.base.runner_base import (
    BuilderBase,
    CompilerBase,
    RunnerBase,
    RunResult,
)

from .config import NexusRunnerConfig


def _set_active_project(config: NexusRunnerConfig) -> None:
    project = qnx.projects.get_or_create(config.project_name)
    qnx.context.set_active_project(project)


class NexusBuilder(BuilderBase[NexusRunnerConfig, HUGRRef]):
    """Builder for building a Hugr package into a Nexus HUGR reference."""

    @staticmethod
    def build(*, config: NexusRunnerConfig, package: Package) -> HUGRRef:
        """Upload the given Hugr package to the Nexus and return a reference."""
        _set_active_project(config)
        hugr_ref = qnx.hugr.upload(
            package,
            name=f"{config.backend_config.__class__.__name__}"
            f"-{config.job_name_suffix}"
            f"-{config.program_name}",
        )
        return hugr_ref


class NexusRunner(RunnerBase[NexusRunnerConfig, HUGRRef]):
    """Runner for running algorithms on Nexus."""

    def __init__(
        self,
        *,
        compiler: CompilerBase[NexusRunnerConfig] | None = None,
        builder: BuilderBase[NexusRunnerConfig, HUGRRef] | None = None,
    ):
        """Initialize the runner with the given compiler and builder."""
        compiler = compiler if compiler else CompilerBase()
        builder = builder if builder else NexusBuilder()
        super().__init__(compiler=compiler, builder=builder)

    def submit_job(
        self,
        *,
        build_artifact: HUGRRef,
        config: NexusRunnerConfig,
    ) -> JobRef:
        """Submit the given build artifact on the Nexus.

        Submits a job to the Nexus waits for the job to complete, and returns a result.
        If the job fails, raises an exception with the error details.
        If the job times out while waiting, raises a TimeoutError. Then, the caller can
        use the job reference to retrieve the job result later when the job is complete
        using the `result_of_completed_job` method.
        """
        n_shots = config.n_shots

        job_ref = qnx.start_execute_job(
            programs=build_artifact,
            n_shots=n_shots,
            backend_config=config.backend_config,
            name=f"{config.backend_config.__class__.__name__}-{config.job_name_suffix}",
        )
        return job_ref

    def run(
        self, *, config: NexusRunnerConfig, program: GuppyFunctionDefinition
    ) -> RunResult:
        """Run the program on the Nexus using the given configuration."""
        self._compile_and_build(config=config, program=program)
        assert self._build_artifact is not None, (
            "Build artifact must be available to run."
        )
        job_ref = self.submit_job(build_artifact=self._build_artifact, config=config)
        response = self.wait_for_job_completion(job_ref=job_ref)
        if response.status != JobStatusEnum.COMPLETED:
            raise qnx_exc.JobError(
                f"JobStatus is not {JobStatusEnum.COMPLETED}.\n"
                f"The status is reported as {response.status}.\n"
                f"Job status message: {response.message}.\n"
                f"Full job status: {response}"
            )
        return RunResult(
            results=self.result_of_completed_job(job_ref=job_ref), event_hook=None
        )

    def wait_for_job_completion(self, *, job_ref: JobRef) -> JobStatus:
        """Wait for the given job to complete and return the final job status."""
        # HACK qnexus wait_for function does not work properly in Python 3.14,
        # so we implement a custom wait_for function here.
        if sys.version_info[:2] == (3, 14):

            def wait_for(
                job: JobRef,
                wait_for_status: JobStatusEnum = JobStatusEnum.COMPLETED,
                timeout: float | None = 900.0,
            ) -> JobStatus:
                """Check job status until the job is complete."""
                start = time.time()
                while True:
                    job_status = qnx.jobs.status(job)
                    if (
                        job_status.status not in WAITING_STATUS
                        or job_status.status == wait_for_status
                    ):
                        break
                    if timeout is not None and (time.time() - start) > timeout:
                        raise TimeoutError("Timed out waiting for job status")
                    time.sleep(1.0)

                if (
                    job_status.status == JobStatusEnum.ERROR
                    and wait_for_status != JobStatusEnum.ERROR
                ):
                    raise qnx_exc.JobError(
                        f"Job errored with detail: {job_status.error_detail}"
                    )
                if (
                    job_status.status == JobStatusEnum.CANCELLED
                    and wait_for_status != JobStatusEnum.CANCELLED
                ):
                    raise qnx_exc.JobError("Job was cancelled")
                if (
                    job_status.status == JobStatusEnum.DEPLETED
                    and wait_for_status != JobStatusEnum.DEPLETED
                ):
                    raise qnx_exc.JobError("Job has run out of account credits")
                if (
                    job_status.status == JobStatusEnum.TERMINATED
                    and wait_for_status != JobStatusEnum.TERMINATED
                ):
                    raise qnx_exc.JobError("Job has been terminated")

                return job_status

        else:
            wait_for = qnx.jobs.wait_for
        wait_for(job_ref)
        return qnx.jobs.status(job_ref)

    def get_execution_info(
        self, *, job_ref: JobRef
    ) -> ExecutionResultRef | IncompleteJobItemRef | CompilationResultRef:
        """Retrieve the execution information of a job using the job reference."""
        job_info = qnx.jobs.results(job_ref)[0]
        return job_info

    def get_job_cost(self, *, job_ref: JobRef) -> float:
        """Retrieve the cost of a completed job using the job reference."""
        job_info = self.get_execution_info(job_ref=job_ref)
        assert isinstance(job_info, ExecutionResultRef), "Job is not completed yet."
        if job_info.cost is None:
            raise ValueError("Job cost information is not available.")
        return job_info.cost

    def result_of_completed_job(self, *, job_ref: JobRef) -> QsysResult:
        """Retrieve the result of a completed job using the job reference."""
        job_info = self.get_execution_info(job_ref=job_ref)
        assert isinstance(job_info, ExecutionResultRef), "Job is not completed yet."
        logger = logging.getLogger("qnexus")
        prev_level = logger.level
        logger.setLevel(logging.CRITICAL + 1)
        try:
            results = cast("QsysResult", job_info.download_result())
        finally:
            logger.setLevel(prev_level)
        return results
