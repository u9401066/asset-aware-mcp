"""Sparse native drawing-axis metrics and explicit move/resize policies."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from src.domain.native_grid import GridTransform


@dataclass(frozen=True)
class GridPoint:
    index: int  # Drawing anchors use zero-based cells, unlike grid edit requests.
    offset: int  # EMUs from that cell's leading edge.


@dataclass(frozen=True)
class GridAxisMetrics:
    limit: int
    default_size: int
    overrides: tuple[tuple[int, int], ...] = ()

    def __post_init__(self) -> None:
        if self.limit not in {16_384, 1_048_576} or self.default_size < 0:
            raise ValueError("Invalid drawing axis metrics")
        if len({index for index, _ in self.overrides}) != len(self.overrides) or any(
            not 0 <= index < self.limit or size < 0 for index, size in self.overrides
        ):
            raise ValueError("Invalid or duplicate drawing dimension overrides")

    @cached_property
    def ordered(self) -> tuple[tuple[int, int], ...]:
        return tuple(sorted(self.overrides))

    @cached_property
    def indices(self) -> tuple[int, ...]:
        return tuple(index for index, _ in self.ordered)

    @cached_property
    def deltas(self) -> tuple[int, ...]:
        values = [0]
        for _, size in self.ordered:
            values.append(values[-1] + size - self.default_size)
        return tuple(values)

    def prefix(self, index: int) -> int:
        if not 0 <= index <= self.limit:
            raise ValueError("Drawing index exceeds worksheet bounds")
        return index * self.default_size + self.deltas[bisect_left(self.indices, index)]

    def absolute(self, point: GridPoint) -> int:
        if not 0 <= point.index < self.limit:
            raise ValueError("Drawing anchor exceeds worksheet bounds")
        position = self.prefix(point.index) + point.offset
        if not 0 <= position <= self.prefix(self.limit):
            raise ValueError("Drawing offset places content outside the worksheet")
        return position

    def locate(self, position: int) -> GridPoint:
        if not 0 <= position <= self.prefix(self.limit):
            raise ValueError("Drawing extent exceeds worksheet bounds")
        left, right = 0, self.limit - 1
        while left < right:
            middle = (left + right + 1) // 2
            if self.prefix(middle) <= position:
                left = middle
            else:
                right = middle - 1
        return GridPoint(left, position - self.prefix(left))


@dataclass(frozen=True)
class GridPlacement:
    start: GridPoint
    end: GridPoint
    old_position: int
    new_position: int
    old_extent: int
    new_extent: int
    collapse_preserved: bool


def relocate_axis(
    start: GridPoint,
    end: GridPoint,
    before: GridAxisMetrics,
    after: GridAxisMetrics,
    transform: GridTransform,
    *,
    mode: Literal["twoCell", "oneCell", "absolute"],
) -> GridPlacement:
    if before.limit != after.limit or before.limit != transform.edit.limit:
        raise ValueError("Drawing metrics and grid edit axes disagree")
    old_start, old_end = before.absolute(start), before.absolute(end)
    if old_end < old_start:
        raise ValueError("Drawing anchor endpoints are reversed")

    def moved(point: GridPoint) -> int:
        index = transform.point(point.index + 1)
        if index is None:
            # The deleted cell has no remaining offset origin.
            index, offset = transform.edit.at, 0
        else:
            offset = point.offset
        return after.absolute(GridPoint(index - 1, offset))

    if mode == "absolute":
        new_start, new_end = old_start, old_end
    elif mode == "oneCell":
        new_start = moved(start)
        new_end = new_start + old_end - old_start
    elif mode == "twoCell":
        new_start, new_end = moved(start), moved(end)
    else:
        raise ValueError("Unknown native drawing anchoring mode")
    collapsed = old_end > old_start and new_end <= new_start
    if collapsed:
        if (transform.edit.collapsed_objects or "preserve_size") == "reject":
            raise ValueError("Grid deletion would collapse a drawing object")
        new_end = new_start + old_end - old_start
    return GridPlacement(
        after.locate(new_start),
        after.locate(new_end),
        old_start,
        new_start,
        old_end - old_start,
        new_end - new_start,
        collapsed,
    )
