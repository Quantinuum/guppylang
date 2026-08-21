"""Defines the Runner interface for running programs on different backends."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from hugr.package import Package

from guppylang.defs import GuppyFunctionDefinition

from .backend_config import RunnerConfig
from .result import RunResult

CONFIG_TYPE = TypeVar("CONFIG_TYPE", bound=RunnerConfig)
PROG_TYPE = TypeVar("PROG_TYPE")
BUILD_TYPE = TypeVar("BUILD_TYPE")


class CompilerBase(Generic[CONFIG_TYPE]):
    """Compiler to compile a given Guppy program into a Hugr package."""

    @staticmethod
    def compile(*, config: CONFIG_TYPE, program: GuppyFunctionDefinition) -> Package:
        """Compile the given program into a Hugr package."""
        return program.compile()


class BuilderBase(ABC, Generic[CONFIG_TYPE, BUILD_TYPE]):
    """Builder to build a Hugr package into a runnable object."""

    @staticmethod
    @abstractmethod
    def build(*, config: CONFIG_TYPE, package: Package) -> BUILD_TYPE:
        """Build the given Hugr package into a runnable object."""


class RunnerBase(Generic[CONFIG_TYPE, BUILD_TYPE]):
    """Runner to run given guppy programs with a given configuration.

    The interface consists of three steps:

        (i) compiling the program into a Hugr package through the `compile`
        method,
        (ii) building the hugr package into a runnable object through the `build`
        method, e.g. uploading to Nexus or building a Selene instance,
        (iii) running the program using the runnable object and returning a result
        (through the `run` method in the Runner).
    """

    compiler: CompilerBase[CONFIG_TYPE]
    builder: BuilderBase[CONFIG_TYPE, BUILD_TYPE]

    _program: GuppyFunctionDefinition
    _hugr_package: Package
    _build_artifact: BUILD_TYPE
    _latest_config: CONFIG_TYPE

    def __init__(
        self,
        *,
        compiler: CompilerBase[CONFIG_TYPE],
        builder: BuilderBase[CONFIG_TYPE, BUILD_TYPE],
    ):
        """Initialize the runner with the given compiler and builder."""
        self.compiler = compiler
        self.builder = builder

    def _compile_and_build(
        self, *, config: CONFIG_TYPE, program: GuppyFunctionDefinition
    ) -> None:
        """Compile the program and build the resulting Hugr package."""
        self._program = program
        self._latest_config = config
        self._hugr_package = self.compiler.compile(config=config, program=self._program)
        self._build_artifact = self.builder.build(
            config=config, package=self._hugr_package
        )

    @abstractmethod
    def run(
        self, *, config: CONFIG_TYPE, program: GuppyFunctionDefinition
    ) -> RunResult:
        """Run the given build artifact and return the result."""
