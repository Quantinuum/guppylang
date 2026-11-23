import tests.error.alias_errors.modules.cycle_b as cycle_b
from guppylang import guppy

Alias1 = guppy.type_alias("Alias1", "cycle_b.Alias2")
