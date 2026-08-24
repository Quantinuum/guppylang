"""Contains different backends for running Guppy programs."""

from .base import RunnerConfig, RunResult
from .local import LocalRunner, LocalRunnerConfig
from .nexus import NexusRunner, NexusRunnerConfig
