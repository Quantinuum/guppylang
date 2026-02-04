"""Collection of error messages emitted during linearity checking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from guppylang_internals.diagnostic import Error, Help, Note

if TYPE_CHECKING:
    from guppylang_internals.checker.core import (
        Place,
        Variable,
    )
    from guppylang_internals.checker.linearity_checker import UseKind
    from guppylang_internals.definition.struct import StructField
    from guppylang_internals.tys.ty import (
        StructType,
        TupleType,
        Type,
    )


@dataclass(frozen=True)
class AlreadyUsedError(Error):
    title: ClassVar[str] = "Copy violation"
    span_label: ClassVar[str] = (
        "{place.describe} with non-copyable type `{place.ty}` cannot be "
        "{kind.subjunctive} ..."
    )
    place: Place
    kind: UseKind

    @dataclass(frozen=True)
    class PrevUse(Note):
        span_label: ClassVar[str] = (
            "{place.describe} already {prev_kind.subjunctive} here"
        )
        prev_kind: UseKind

    @dataclass(frozen=True)
    class MakeCopy(Help):
        message: ClassVar[str] = (
            "Consider copying `{place}` instead of moving it: `{place}.copy()`"
        )


@dataclass(frozen=True)
class ComprAlreadyUsedError(Error):
    title: ClassVar[str] = "Copy violation"
    span_label: ClassVar[str] = (
        "{place.describe} with non-copyable type `{place.ty}` would be "
        "{kind.subjunctive} multiple times when evaluating this comprehension"
    )
    place: Place
    kind: UseKind

    @dataclass(frozen=True)
    class PrevUse(Note):
        span_label: ClassVar[str] = (
            "{place.describe} already {prev_kind.subjunctive} here"
        )
        prev_kind: UseKind


@dataclass(frozen=True)
class PlaceNotUsedError(Error):
    title: ClassVar[str] = "Drop violation"
    place: Place

    @property
    def rendered_span_label(self) -> str:
        s = f"{self.place.describe} with non-droppable type `{self.place.ty}` "
        match self.children:
            case [PlaceNotUsedError.Branch(), *_]:
                return s + "may be leaked ..."
            case _:
                return s + "is leaked"

    @dataclass(frozen=True)
    class Branch(Note):
        span_label: ClassVar[str] = "if this expression is `{truth_value}`"
        truth_value: bool

    @dataclass(frozen=True)
    class Fix(Help):
        message: ClassVar[str] = (
            "Make sure that `{place}` is consumed or returned to avoid the leak"
        )


@dataclass(frozen=True)
class UnnamedExprNotUsedError(Error):
    title: ClassVar[str] = "Drop violation"
    span_label: ClassVar[str] = "Expression with non-droppable type `{ty}` is leaked"
    ty: Type

    @dataclass(frozen=True)
    class Fix(Help):
        message: ClassVar[str] = "Consider assigning this value to a local variable"


@dataclass(frozen=True)
class UnnamedFieldNotUsedError(Error):
    title: ClassVar[str] = "Drop violation"
    span_label: ClassVar[str] = (
        "Non-droppable field `{field.name}` of expression with type `{struct_ty}` is "
        "leaked"
    )
    field: StructField
    struct_ty: StructType

    @dataclass(frozen=True)
    class Fix(Help):
        message: ClassVar[str] = (
            "Consider assigning this value to a local variable before accessing the "
            "field `{used_field.name}`"
        )
        used_field: StructField


@dataclass(frozen=True)
class UnnamedSubscriptNotUsedError(Error):
    title: ClassVar[str] = "Drop violation"
    span_label: ClassVar[str] = (
        "Non-droppable items of expression with type `{container_ty}` are leaked ..."
    )
    container_ty: Type

    @dataclass(frozen=True)
    class SubscriptHint(Note):
        span_label: ClassVar[str] = "since only this subscript is used"

    @dataclass(frozen=True)
    class Fix(Help):
        message: ClassVar[str] = (
            "Consider assigning this value to a local variable before subscripting it"
        )


@dataclass(frozen=True)
class UnnamedTupleNotUsedError(Error):
    title: ClassVar[str] = "Drop violation"
    span_label: ClassVar[str] = (
        "Non-droppable items inside expression of type `{tuple_ty}` are leaked"
    )
    tuple_ty: TupleType

    @dataclass(frozen=True)
    class Fix(Help):
        message: ClassVar[str] = (
            "Consider assigning this value to a local variable before subscripting it"
        )


@dataclass(frozen=True)
class NotOwnedError(Error):
    title: ClassVar[str] = "Not owned"
    place: Place
    kind: UseKind
    is_call_arg: bool
    func_name: str | None
    calling_func_name: str

    @property
    def rendered_span_label(self) -> str:
        if self.is_call_arg:
            f = f"Function `{self.func_name}`" if self.func_name else "Function"
            return (
                f"{f} wants to take ownership of this argument, but "
                f"`{self.calling_func_name}` doesn't own `{self.place}`"
            )
        return (
            f"Cannot {self.kind.indicative} `{self.place}` since "
            f"`{self.calling_func_name}` doesn't own it"
        )

    @dataclass(frozen=True)
    class MakeOwned(Help):
        span_label: ClassVar[str] = (
            "Argument `{place.root.name}` is only borrowed. Consider taking ownership: "
            "`{place.root.name}: {place.root.ty} @owned`"
        )

    @dataclass(frozen=True)
    class MakeCopy(Help):
        span_label: ClassVar[str] = (
            "Or consider copying this argument: `{place}.copy()`"
        )


@dataclass(frozen=True)
class MoveOutOfSubscriptError(Error):
    title: ClassVar[str] = "Subscript {kind.subjunctive}"
    span_label: ClassVar[str] = (
        "Cannot {kind.indicative} a subscript of `{parent}` with non-copyable type "
        "`{parent.ty}`"
    )
    kind: UseKind
    parent: Place

    @dataclass(frozen=True)
    class Explanation(Note):
        message: ClassVar[str] = (
            "Subscripts on non-copyable types are only allowed to be borrowed, not "
            "{kind.subjunctive}"
        )


@dataclass(frozen=True)
class BorrowShadowedError(Error):
    title: ClassVar[str] = "Borrow shadowed"
    span_label: ClassVar[str] = "Assignment shadows borrowed argument `{place}`"
    place: Place

    @dataclass(frozen=True)
    class Rename(Help):
        message: ClassVar[str] = "Consider assigning to a different name"


@dataclass(frozen=True)
class BorrowSubPlaceUsedError(Error):
    title: ClassVar[str] = "Copy violation"
    span_label: ClassVar[str] = (
        "Borrowed argument {borrowed_var} cannot be returned to the caller ..."
    )
    borrowed_var: Variable
    sub_place: Place

    @dataclass(frozen=True)
    class PrevUse(Note):
        span_label: ClassVar[str] = (
            "since `{sub_place}` with non-copyable type `{sub_place.ty}` was already "
            "{kind.subjunctive} here"
        )
        kind: UseKind

    @dataclass(frozen=True)
    class Fix(Help):
        message: ClassVar[str] = (
            "Consider writing a value back into `{sub_place}` before returning"
        )


@dataclass(frozen=True)
class DropAfterCallError(Error):
    title: ClassVar[str] = "Drop violation"
    span_label: ClassVar[str] = (
        "Value with non-droppable type `{ty}` would be leaked after {func} returns"
    )
    ty: Type
    func_name: str | None

    @property
    def func(self) -> str:
        return f"`{self.func_name}`" if self.func_name else "the function"

    @dataclass(frozen=True)
    class Assign(Help):
        message: ClassVar[str] = (
            "Consider assigning the value to a local variable before passing it to "
            "{func}"
        )


@dataclass(frozen=True)
class NonCopyableCaptureError(Error):
    title: ClassVar[str] = "Copy violation"
    span_label: ClassVar[str] = (
        "{var.describe} with non-copyable type {var.ty} cannot be used here since "
        "`{var}` is captured from an outer scope"
    )
    var: Variable

    @dataclass(frozen=True)
    class DefinedHere(Note):
        span_label: ClassVar[str] = "`{var}` defined here"


@dataclass(frozen=True)
class NonCopyablePartialApplyError(Error):
    title: ClassVar[str] = "Copy violation"
    span_label: ClassVar[str] = (
        "This expression implicitly constructs a closure that captures a non-copyable "
        "value"
    )

    @dataclass(frozen=True)
    class Captured(Note):
        span_label: ClassVar[str] = (
            "This expression with non-copyable type `{ty}` is implicitly captured"
        )
        ty: Type


@dataclass(frozen=True)
class NonDroppableForBreakError(Error):
    title: ClassVar[str] = "Break in non-droppable loop"
    span_label: ClassVar[str] = "Early exit in non-droppable loops is not allowed"

    @dataclass(frozen=True)
    class NonDroppableIteratorType(Note):
        span_label: ClassVar[str] = "Iterator has non-droppable type `{ty}`"
        ty: Type
