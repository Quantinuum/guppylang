from collections.abc import Sequence
from dataclasses import dataclass

from guppylang_internals.definition.common import DefId
from guppylang_internals.tys.arg import Argument


@dataclass(frozen=True)
class ProtocolInst:
    type_args: Sequence[Argument]
    def_id: DefId
