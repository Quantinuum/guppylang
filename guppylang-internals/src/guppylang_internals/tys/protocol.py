from dataclasses import dataclass, replace

from guppylang_internals.definition.common import DefId
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.common import Transformer


@dataclass(frozen=True)
class ProtocolInst:
    type_args: tuple[Argument, ...]
    def_id: DefId

    def transform(self, transformer: Transformer) -> "ProtocolInst":
        new_type_args = tuple(arg.transform(transformer) for arg in self.type_args)
        return replace(self, type_args=new_type_args)
