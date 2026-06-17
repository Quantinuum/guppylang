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

    @property
    def copyable(self) -> bool:
        return True

    @property
    def droppable(self) -> bool:
        return True

    @property
    def linear(self) -> bool:
        return False

    def __str__(self) -> str:
        from guppylang_internals.engine import ENGINE

        defn = ENGINE.get_parsed(self.def_id)
        if self.type_args:
            args = ", ".join(str(arg) for arg in self.type_args)
            return f"{defn.name}[{args}]"
        else:
            return str(defn.name)
