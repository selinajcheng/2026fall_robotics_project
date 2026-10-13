"""Four rectangular city blocks around one unpainted intersection.

Each block holds a hand-placed cluster of stepped rooftop volumes
(see `docs/reference/generated_city_blocks.png` for the target style).
"""

from dataclasses import dataclass
from typing import Literal

from .world import Cell, GridWorld


CellRect = tuple[int, int, int, int]  # left, top, width, height in cells
StripeDirection = Literal["vertical", "horizontal"]
Terrain = Literal["sidewalk", "crosswalk", "building", "lot", "road"]

SIDEWALK_WIDTH = 2
ROAD_WIDTH = 4
BLOCK_WIDTH = 16
BLOCK_HEIGHT = 10
TILE_SIZE = 28


def cells_in(rect: CellRect) -> frozenset[Cell]:
    left, top, width, height = rect
    return frozenset(
        (column, row)
        for column in range(left, left + width)
        for row in range(top, top + height)
    )


@dataclass(frozen=True)
class Crosswalk:
    rect: CellRect
    stripe_direction: StripeDirection


@dataclass(frozen=True)
class Building:
    """One rooftop volume. `level` (1-3) sets its height."""

    rect: CellRect
    level: int


# Per block (same order as `CityScene.blocks`: top-left, top-right, bottom-left,
# bottom-right): (column, row, width, height, level), relative to the
# block's 12-by-6 lot.
BLOCK_LAYOUTS: tuple[tuple[tuple[int, int, int, int, int], ...], ...] = (
    (
        (0, 0, 6, 4, 2),
        (0, 4, 4, 2, 1),
        (6, 0, 3, 3, 1),
        (9, 0, 3, 3, 3),
        (4, 4, 3, 2, 2),
        (7, 3, 5, 3, 1),
    ),
    (
        (7, 0, 5, 3, 2),
        (9, 3, 3, 3, 1),
        (0, 0, 4, 3, 3),
        (4, 0, 3, 2, 1),
        (0, 3, 5, 3, 1),
        (5, 3, 4, 3, 2),
    ),
    (
        (4, 1, 4, 4, 3),
        (8, 2, 3, 2, 1),
        (0, 0, 4, 3, 1),
        (0, 3, 4, 3, 2),
        (8, 0, 4, 2, 2),
        (8, 4, 4, 2, 1),
        (4, 5, 4, 1, 1),
    ),
    (
        (0, 2, 4, 4, 2),
        (4, 3, 3, 3, 1),
        (0, 0, 5, 2, 1),
        (5, 0, 3, 3, 3),
        (8, 0, 4, 3, 1),
        (7, 3, 5, 3, 2),
    ),
)


@dataclass(frozen=True)
class CityScene:
    world: GridWorld
    blocks: tuple[CellRect, ...]
    lots: tuple[CellRect, ...]
    buildings: tuple[Building, ...]
    crosswalks: tuple[Crosswalk, ...]
    sidewalk_cells: frozenset[Cell]
    crosswalk_cells: frozenset[Cell]
    building_cells: frozenset[Cell]
    lot_cells: frozenset[Cell]
    start_cell: Cell

    def terrain_at(self, cell: Cell) -> Terrain:
        if not self.world.in_bounds(cell):
            raise ValueError("Cell is outside the scene")
        if cell in self.sidewalk_cells:
            return "sidewalk"
        if cell in self.crosswalk_cells:
            return "crosswalk"
        if cell in self.building_cells:
            return "building"
        if cell in self.lot_cells:
            return "lot"
        return "road"


def place_buildings(lots: tuple[CellRect, ...]) -> tuple[Building, ...]:
    """Turn `BLOCK_LAYOUTS` into buildings, rejecting any that leave their lot or overlap."""
    buildings: list[Building] = []
    for lot, layout in zip(lots, BLOCK_LAYOUTS, strict=True):
        lot_left, lot_top, _, _ = lot
        lot_cells = cells_in(lot)
        block_cells: set[Cell] = set()
        for column, row, width, height, level in layout:
            rect = (lot_left + column, lot_top + row, width, height)
            cells = cells_in(rect)
            if not cells <= lot_cells:
                raise ValueError(f"Building {rect} leaves its lot")
            if cells & block_cells:
                raise ValueError(f"Building {rect} overlaps another building")
            if level not in (1, 2, 3):
                raise ValueError("Building level must be 1, 2, or 3")
            block_cells |= cells
            buildings.append(Building(rect, level))
    return tuple(buildings)


def create_city_scene() -> CityScene:
    """Place four long blocks, rooftop volumes in each lot, and crossings at the intersection and at each road end."""
    left_positions = (0, BLOCK_WIDTH + ROAD_WIDTH)
    top_positions = (0, BLOCK_HEIGHT + ROAD_WIDTH)
    blocks = tuple(
        (left, top, BLOCK_WIDTH, BLOCK_HEIGHT)
        for top in top_positions
        for left in left_positions
    )
    lots = tuple(
        (
            left + SIDEWALK_WIDTH,
            top + SIDEWALK_WIDTH,
            BLOCK_WIDTH - 2 * SIDEWALK_WIDTH,
            BLOCK_HEIGHT - 2 * SIDEWALK_WIDTH,
        )
        for left, top, _, _ in blocks
    )
    buildings = place_buildings(lots)
    crosswalks = (
        Crosswalk(
            (BLOCK_WIDTH, BLOCK_HEIGHT - SIDEWALK_WIDTH, ROAD_WIDTH, SIDEWALK_WIDTH),
            "vertical",
        ),
        Crosswalk(
            (BLOCK_WIDTH, top_positions[1], ROAD_WIDTH, SIDEWALK_WIDTH),
            "vertical",
        ),
        Crosswalk(
            (BLOCK_WIDTH - SIDEWALK_WIDTH, BLOCK_HEIGHT, SIDEWALK_WIDTH, ROAD_WIDTH),
            "horizontal",
        ),
        Crosswalk(
            (left_positions[1], BLOCK_HEIGHT, SIDEWALK_WIDTH, ROAD_WIDTH),
            "horizontal",
        ),
        # Where each road leaves the map, a crossing joins the two curbs that end there.
        Crosswalk((BLOCK_WIDTH, 0, ROAD_WIDTH, SIDEWALK_WIDTH), "vertical"),
        Crosswalk((BLOCK_WIDTH, top_positions[1] + BLOCK_HEIGHT - SIDEWALK_WIDTH, ROAD_WIDTH, SIDEWALK_WIDTH), "vertical"),
        Crosswalk((0, BLOCK_HEIGHT, SIDEWALK_WIDTH, ROAD_WIDTH), "horizontal"),
        Crosswalk((left_positions[1] + BLOCK_WIDTH - SIDEWALK_WIDTH, BLOCK_HEIGHT, SIDEWALK_WIDTH, ROAD_WIDTH), "horizontal"),
    )

    lot_area = frozenset().union(*(cells_in(rect) for rect in lots))
    building_cells = frozenset().union(*(cells_in(building.rect) for building in buildings))
    sidewalk_cells = frozenset().union(*(cells_in(rect) for rect in blocks)) - lot_area
    crosswalk_cells = frozenset().union(*(cells_in(crossing.rect) for crossing in crosswalks))
    world = GridWorld(
        columns=2 * BLOCK_WIDTH + ROAD_WIDTH,
        rows=2 * BLOCK_HEIGHT + ROAD_WIDTH,
        tile_size=TILE_SIZE,
        walkable_cells=sidewalk_cells | crosswalk_cells,
    )
    return CityScene(
        world=world,
        blocks=blocks,
        lots=lots,
        buildings=buildings,
        crosswalks=crosswalks,
        sidewalk_cells=sidewalk_cells,
        crosswalk_cells=crosswalk_cells,
        building_cells=building_cells,
        lot_cells=lot_area - building_cells,
        start_cell=(SIDEWALK_WIDTH - 1, SIDEWALK_WIDTH - 1),
    )
