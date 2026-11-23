import tests.error.alias_errors.modules.cycle_a as cycle_a
from guppylang import guppy

Alias2 = guppy.type_alias("Alias2", "cycle_a.Alias1")
