from guppylang import guppy

@guppy.enum
class Enum:
    VariantA = {"x": int}

Enum.VariantA(1)
