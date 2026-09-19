"""Stable native table-column identities for structural reference migration."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property


@dataclass(frozen=True)
class GridTableColumn:
    identity: int
    name: str

    def __post_init__(self) -> None:
        if not 1 <= self.identity <= 4_294_967_295 or not self.name:
            raise ValueError("Invalid native table column identity or name")


@dataclass(frozen=True)
class GridTableChange:
    name: str
    before: tuple[GridTableColumn, ...]
    after: tuple[GridTableColumn, ...] | None

    def __post_init__(self) -> None:
        if not self.name or not self.before or self.after == ():
            raise ValueError("A native table needs a name and at least one column")
        for columns in (self.before, self.after or ()):
            if len({col.identity for col in columns}) != len(columns) or len(
                {col.name.casefold() for col in columns}
            ) != len(columns):
                raise ValueError("Duplicate table column IDs or names are ambiguous")
        previous = {col.identity for col in self.before}
        surviving = {col.identity for col in self.after or ()} & previous
        if [col.identity for col in self.before if col.identity in surviving] != [
            col.identity for col in self.after or () if col.identity in previous
        ]:
            raise ValueError(
                "Column reordering requires a separate correspondence operation"
            )

    @cached_property
    def by_name(self) -> dict[str, GridTableColumn]:
        return {col.name.casefold(): col for col in self.before}

    @cached_property
    def remaining(self) -> dict[int, GridTableColumn]:
        return {col.identity: col for col in self.after or ()}

    @cached_property
    def positions(self) -> dict[int, int]:
        return {col.identity: index for index, col in enumerate(self.before)}

    def column(self, name: str) -> GridTableColumn:
        try:
            return self.by_name[name.casefold()]
        except KeyError as exc:
            raise ValueError(
                "Structured reference names an unknown source column"
            ) from exc

    def renamed(self, name: str) -> str | None:
        old = self.column(name)
        new = self.remaining.get(old.identity)
        return new.name if new else None

    def interval(self, first: str, last: str) -> tuple[str, str] | None:
        left, right = (
            self.positions[self.column(first).identity],
            self.positions[self.column(last).identity],
        )
        survivors = [
            self.remaining[col.identity].name
            for col in self.before[min(left, right) : max(left, right) + 1]
            if col.identity in self.remaining
        ]
        if not survivors:
            return None
        return (
            (survivors[0], survivors[-1])
            if left <= right
            else (survivors[-1], survivors[0])
        )
