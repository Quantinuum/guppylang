## MATCH SPEC


```java

MatchCasePattern(pattern: pattern, subject: expr)

```java
pattern =
    MatchValue(value: expr)
    | MatchClass(cls: expr, patterns: pattern*, kwd_attrs: identifier*, kwd_patterns: pattern*)
    | MatchAs(pattern: pattern?, name: identifier?)

    | MatchSingleton(value: constant)
    | MatchSequence(patterns: pattern*)
    | MatchMapping(keys: expr*, patterns: pattern*, rest: identifier?)
    | MatchStar(name: identifier?)
    // The optional "rest" MatchMapping parameter handles capturing extra mapping keys
    | MatchOr(patterns: pattern*)
```


### Pattern Examples

```python
# MatchAs - MatchAs()
    case _:                # OK (B, C)

# MatchValue - MatchValue(expr value)
    case 42:               # OK (B, C)
    case True:             # OK (B, C)
    case "hello":          # NO FOR NOW: we do not have .eq for strings
    case EnumName.Variant: # FORBIDDEN: Match bindings cannot shadow class variants


# MatchClass - MatchClass(expr cls, pattern* patterns)
    case Point.Variant(_, _)      # OK (B,C)
    case Point.Variant(3, 4): # OK (B, C)
    case Struct(1, 2) # OK (B, C)
    case Struct(True, _) # OK (B, C)
    case Struct("x", "y") # NO FOR NOW: we do not have .eq for strings

# MatchClass - MatchClass(expr cls, pattern* patterns, identifier* kwd_attrs, pattern* kwd_patterns)
    case EnumName.Point(x, y): # NO FOR NOW
    case Point(x=3, y=4): # NO FOR NOW
    case Point(x=A, y=B) # NO FOR NOW

# MatchSingleton
    case None: # NO FOR NOW

# MatchSequence
    case [a, b, c]: # NO FOR NOW

# MatchMapping
    case {"key1": v1, "key2": v2, **rest}: # NO FOR NOW


# MatchStar
    case [*rest]:          # NO FOR NOW

# MatchAs with binding
    case x:                # NO FOR NOW
    case ClassName() as var: # NO FOR NOW
    case Class:            # FORBIDDEN: Match bindings cannot shadow class variants -> check that the name is not a class variant


# MatchOr OK
    case Direction.North | Direction.South:  # No FOR NOW

# Match with guard
    case Direction.North(A=steps) if steps > 10: # NO FOR NOW

```


## WORKING FEATURE


### Enum

Only checking
```python


match north:
    case Direction.North(): # THIS
        body1
    case Direction.South:
        body2
    case Direction.North(A=steps):  #TODO var definition
        body2
    case Direction.North(A=steps) if steps > 10:
        body1
    case Direction.South as south:
        body3
    case Direction.East | Direction.West:
        body4
    case x:
        body5
    case _:                 # THIS
        body5

```


## TODO TO DISCUSS


Which types are allowed?

How should match work with generics?

Making match work with generics

How do we treat `as` statements with linear variables?


## DONE CHECK

```python
@guppy.enum
class Direction:
    North = {"A": int}
    South = {"B": int}

    @guppy
    def str_(self) -> str:
        return "Direction"

@guppy
def g() -> Direction:
    return Direction.North(5)

@guppy.struct
class Point:
    x: int
    y: int

    @guppy
    def method(self) -> int:
        return self.x + self.y

@guppy
def main(north: Direction, x:int) -> None:
    p = Point(3, 4)
    match north:
        case g():  # ERROR: match on a function
            x = 99
        case Direction.str_(): # ERROR: match on a method enum
            x = 88
        case p.method(): # ERROR: match on a struct method
            x = 77
        case x: # ERROR: match-as not supported
            x = 66
        case Class() as var: # ERROR: match-as not supported
            x = 55
        case Point(...). # ERROR: wrong type/wrong number of args
            x = 44


@guppy
def main(north: Enum[int], x:int) -> None:
    match north:
        case Point(): # ERROR: different type
            z = 66

    match i:
        case _: # Error: python do not allow this, good!
            return "One"
        case 1 | x: # Same here, python do not allow this, good!
            return "1 or x"
        case 2:
            return f"Two"

```

## TODO CHECK

```python
        case Point(x, y): # Error: value must be constants
            z = 44
```


```python

# Example: linear variable used in multiple match arms (should error if not allowed)
from guppylang import guppy

@guppy.struct
class Point:
    x: qubit

@guppy
def main(p: Point) -> None:
    match p:   # Got ERROR from p, it seems that p.x has been consumed here
        case Point():
            a = p.x
        case Point():
            b = p.x

main.check()

```

### Unreachable patterns
What do we do for unreachable patterns?
In Python, from this:

```python

```

we have:
```
Cell In[10], line 8
    case x:
         ^
SyntaxError: name capture 'x' makes remaining patterns unreachable
```

In Rust, from this:
```rust
match i {
    0 => "Zero",
    1 => "One",
    x => format!("No match for {x}"),
    3 => "Three",
}
```

we have:
```
Standard Error
    Compiling playground v0.0.1 (/playground)
warning: unreachable pattern
 --> src/main.rs:7:9
  |
6 |         x => format!("No match for {x}"),
  |         - matches any value
7 |         3 => "Three".to_string(),
  |         ^ no value can reach this
```


### ...

and other stuff


```python

    match x:
        case _ if a > 0: # Is this fine?
            ...
        case ClassName() as x:
            ...
```
