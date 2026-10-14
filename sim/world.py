"""Grid boundaries and walkability for the sidewalk simulation."""

from collections.abc import Iterable


Cell = tuple[int, int]


class GridWorld:
    """A bounded grid; coordinates are (column, row), starting at (0, 0)."""

    def __init__(
        self,
        columns: int,
        rows: int,
        tile_size: int = 40,
        blocked_cells: Iterable[Cell] = (),
        walkable_cells: Iterable[Cell] | None = None,
    ) -> None:
        if columns <= 0 or rows <= 0 or tile_size <= 0:
            raise ValueError("Grid dimensions and tile size must be positive")

        self.columns = columns
        self.rows = rows
        self.tile_size = tile_size
        self.blocked_cells = frozenset(blocked_cells)
        if any(not self.in_bounds(cell) for cell in self.blocked_cells):
            raise ValueError("Blocked cells must be inside the grid")
        self.walkable_cells = None if walkable_cells is None else frozenset(walkable_cells)
        if self.walkable_cells is not None and any(
            not self.in_bounds(cell) for cell in self.walkable_cells
        ):
            raise ValueError("Walkable cells must be inside the grid")

    @property
    def pixel_size(self) -> tuple[int, int]:
        return self.columns * self.tile_size, self.rows * self.tile_size

    def in_bounds(self, cell: Cell) -> bool:
        column, row = cell
        return 0 <= column < self.columns and 0 <= row < self.rows

    def is_walkable(self, cell: Cell) -> bool:
        return (
            self.in_bounds(cell)
            and (self.walkable_cells is None or cell in self.walkable_cells)
            and cell not in self.blocked_cells
        )

    def can_move(self, start: Cell, destination: Cell) -> bool:
        """Allow one orthogonal step between walkable cells."""
        distance = abs(start[0] - destination[0]) + abs(start[1] - destination[1])
        return distance == 1 and self.is_walkable(start) and self.is_walkable(destination)

    def neighbors(self, cell: Cell) -> tuple[Cell, ...]:
        """Return legal next cells for path planning."""
        if not self.is_walkable(cell):
            return ()
        column, row = cell
        candidates = (
            (column + 1, row),
            (column, row + 1),
            (column - 1, row),
            (column, row - 1),
        )
        return tuple(next_cell for next_cell in candidates if self.can_move(cell, next_cell))
