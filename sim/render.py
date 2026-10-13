"""Drawing for the four-block aerial view, styled after docs/reference/generated_city_blocks.png.

The static background (roads, sidewalks, buildings, crosswalks) is rendered once
and cached; `draw_world` blits it each frame and draws anything that moves on top.
"""

import random
from functools import lru_cache

import pygame

from .scene import BLOCK_HEIGHT, BLOCK_WIDTH, ROAD_WIDTH, Building, CellRect, CityScene

# The static background is drawn once at this multiple of the screen size and
# scaled down, which smooths the rounded corners and bevels.
SUPERSAMPLE = 3
BASE_TILE = 28  # all pixel sizes below are written for 28-pixel tiles and scale with the tile

ROAD_COLOR = (47, 50, 54)
ROAD_SHADOW_COLOR = (31, 33, 37)
MARKING_COLOR = (240, 240, 235)
CURB_COLOR = (201, 165, 128)
SIDEWALK_COLOR = (236, 205, 171)
PAVING_COLOR = (219, 184, 148)
LIP_COLOR = (247, 227, 202)
PLAZA_COLOR = (203, 174, 143)
PLAZA_EDGE_COLOR = (170, 139, 108)
START_COLOR = (38, 112, 207)

# (roof, right wall, bottom wall, roof detail) for each building level.
GREY_ROOFS = {
    1: ((168, 170, 175), (128, 131, 137), (104, 107, 113), (205, 207, 210)),
    2: ((190, 192, 196), (136, 139, 145), (110, 113, 119), (224, 226, 228)),
    3: ((212, 214, 217), (144, 147, 153), (116, 119, 125), (238, 239, 241)),
}


def to_pixels(rect: CellRect, tile: int) -> pygame.Rect:
    left, top, width, height = rect
    return pygame.Rect(left * tile, top * tile, width * tile, height * tile)


def shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, round(channel * factor))) for channel in color)


class Scale:
    """Converts pixel sizes written for 28-pixel tiles to the current tile size."""

    def __init__(self, tile: int) -> None:
        self.tile = tile
        self.factor = tile / BASE_TILE

    def __call__(self, pixels: float) -> int:
        return max(1, round(pixels * self.factor))


def draw_dashes(
    surface: pygame.Surface,
    start: tuple[int, int],
    end: tuple[int, int],
    dash: int,
    gap: int,
    width: int,
) -> None:
    """Draw white dashes along one horizontal or vertical road centerline."""
    if start[0] == end[0]:
        for top in range(start[1], end[1], dash + gap):
            pygame.draw.line(surface, MARKING_COLOR, (start[0], top), (start[0], min(top + dash, end[1])), width)
    else:
        for left in range(start[0], end[0], dash + gap):
            pygame.draw.line(surface, MARKING_COLOR, (left, start[1]), (min(left + dash, end[0]), start[1]), width)


def draw_road_markings(surface: pygame.Surface, scene: CityScene, px: Scale) -> None:
    """Paint centerlines and stop bars for the four near crossings and the four road-end crossings."""
    tile = px.tile
    center_x = (BLOCK_WIDTH + ROAD_WIDTH // 2) * tile
    center_y = (BLOCK_HEIGHT + ROAD_WIDTH // 2) * tile
    road_left, road_right = BLOCK_WIDTH * tile, (BLOCK_WIDTH + ROAD_WIDTH) * tile
    road_top, road_bottom = BLOCK_HEIGHT * tile, (BLOCK_HEIGHT + ROAD_WIDTH) * tile
    dash = gap = tile // 2
    line = px(3)
    bar = px(5)
    clear = px(18)  # centerline stops this far before a stop bar
    stop = px(11)  # stop bar sits this far before its crossing
    inset = px(5)

    # Crossings are two cells deep. "near" ones touch the intersection; "end" ones sit where each road leaves the map.
    near_top, near_bottom = (BLOCK_HEIGHT - 2) * tile, (BLOCK_HEIGHT + ROAD_WIDTH + 2) * tile
    near_left, near_right = (BLOCK_WIDTH - 2) * tile, (BLOCK_WIDTH + ROAD_WIDTH + 2) * tile
    end_top, end_bottom = 2 * tile, (2 * BLOCK_HEIGHT + ROAD_WIDTH - 2) * tile
    end_left, end_right = 2 * tile, (2 * BLOCK_WIDTH + ROAD_WIDTH - 2) * tile

    # Each centerline runs between two crossings and stops short of their bars.
    # The middle intersection has no markings.
    draw_dashes(surface, (center_x, end_top + clear), (center_x, near_top - clear), dash, gap, line)
    draw_dashes(surface, (center_x, near_bottom + clear), (center_x, end_bottom - clear), dash, gap, line)
    draw_dashes(surface, (end_left + clear, center_y), (near_left - clear, center_y), dash, gap, line)
    draw_dashes(surface, (near_right + clear, center_y), (end_right - clear, center_y), dash, gap, line)

    # Right-hand traffic: each stop bar covers only the lane approaching its crossing.
    bars = (
        # Toward the intersection's crossings.
        ((road_left + inset, near_top - stop), (center_x - inset, near_top - stop)),
        ((center_x + inset, near_bottom + stop), (road_right - inset, near_bottom + stop)),
        ((near_left - stop, center_y + inset), (near_left - stop, road_bottom - inset)),
        ((near_right + stop, road_top + inset), (near_right + stop, center_y - inset)),
        # Toward the crossings at the road ends.
        ((center_x + inset, end_top + stop), (road_right - inset, end_top + stop)),
        ((road_left + inset, end_bottom - stop), (center_x - inset, end_bottom - stop)),
        ((end_left + stop, road_top + inset), (end_left + stop, center_y - inset)),
        ((end_right - stop, center_y + inset), (end_right - stop, road_bottom - inset)),
    )
    for start, end in bars:
        pygame.draw.line(surface, MARKING_COLOR, start, end, bar)


def draw_crosswalk(surface: pygame.Surface, crossing_rect: pygame.Rect, direction: str, px: Scale) -> None:
    step = px(14)
    stripe_width = px(9)
    inset = px(4)
    if direction == "vertical":
        for left in range(crossing_rect.left + inset, crossing_rect.right - stripe_width, step):
            stripe = pygame.Rect(left, crossing_rect.top + inset, stripe_width, crossing_rect.height - 2 * inset)
            pygame.draw.rect(surface, MARKING_COLOR, stripe, border_radius=px(2))
    else:
        for top in range(crossing_rect.top + inset, crossing_rect.bottom - stripe_width, step):
            stripe = pygame.Rect(crossing_rect.left + inset, top, crossing_rect.width - 2 * inset, stripe_width)
            pygame.draw.rect(surface, MARKING_COLOR, stripe, border_radius=px(2))


def draw_block(surface: pygame.Surface, block: pygame.Rect, px: Scale) -> None:
    """Draw one raised sidewalk slab with paving joints and rounded corners."""
    radius = px.tile
    pygame.draw.rect(surface, ROAD_SHADOW_COLOR, block.move(px(3), px(4)).inflate(px(4), px(4)), border_radius=radius + px(2))
    pygame.draw.rect(surface, CURB_COLOR, block.inflate(px(4), px(4)), border_radius=radius + px(2))

    slab = pygame.Surface(block.size, pygame.SRCALPHA)
    local = slab.get_rect()
    pygame.draw.rect(slab, SIDEWALK_COLOR, local, border_radius=radius)

    # Draw the paving joints on their own layer, then trim them to the rounded slab.
    joints = pygame.Surface(block.size, pygame.SRCALPHA)
    for x in range(px.tile, local.width, px.tile):
        pygame.draw.line(joints, PAVING_COLOR, (x, 0), (x, local.height), px(1))
    for y in range(px.tile, local.height, px.tile):
        pygame.draw.line(joints, PAVING_COLOR, (0, y), (local.width, y), px(1))
    joints.blit(slab, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    slab.blit(joints, (0, 0))

    pygame.draw.rect(slab, LIP_COLOR, local.inflate(-px(3), -px(3)), px(2), border_radius=radius - px(1))
    surface.blit(slab, block)


def draw_roof_details(surface: pygame.Surface, roof: pygame.Rect, detail_color: tuple[int, int, int], seed: int, px: Scale) -> None:
    """Scatter a few small rooftop boxes. A fixed seed keeps the scene identical every run."""
    rng = random.Random(seed)
    cells = (roof.width // px.tile) * (roof.height // px.tile)
    placed: list[pygame.Rect] = []
    for _ in range(1 if cells < 6 else 3 if cells >= 12 else 2):
        for _attempt in range(12):
            width = rng.choice((px(10), px(14), px(20), px(26)))
            height = rng.choice((px(10), px(14), px(18)))
            margin = px(9)
            if roof.width < width + 2 * margin or roof.height < height + 2 * margin:
                continue
            box = pygame.Rect(
                roof.left + margin + rng.randrange(roof.width - width - 2 * margin + 1),
                roof.top + margin + rng.randrange(roof.height - height - 2 * margin + 1),
                width,
                height,
            )
            if any(box.inflate(px(6), px(6)).colliderect(other) for other in placed):
                continue
            placed.append(box)
            pygame.draw.rect(surface, shade(detail_color, 0.62), box.move(px(2), px(2)), border_radius=px(2))
            pygame.draw.rect(surface, detail_color, box, border_radius=px(2))
            pygame.draw.rect(surface, shade(detail_color, 0.86), box.inflate(-px(6), -px(6)), px(1), border_radius=px(1))
            break


def draw_building(surface: pygame.Surface, building: Building, seed: int, px: Scale) -> None:
    rect = to_pixels(building.rect, px.tile)
    roof_color, side_color, bottom_color, detail_color = GREY_ROOFS[building.level]
    height = building.level * px(4)

    roof = pygame.Rect(rect.left, rect.top, rect.width - height, rect.height - height)
    pygame.draw.rect(surface, bottom_color, rect, border_radius=px(5))
    pygame.draw.rect(surface, side_color, pygame.Rect(roof.right - px(5), rect.top, rect.right - roof.right + px(5), rect.height), border_radius=px(5))
    pygame.draw.rect(surface, roof_color, roof, border_radius=px(5))
    pygame.draw.rect(surface, shade(roof_color, 1.14), roof, px(1), border_radius=px(5))
    if roof.width >= 2 * px.tile and roof.height >= 2 * px.tile:
        pygame.draw.rect(surface, shade(roof_color, 0.9), roof.inflate(-px(14), -px(14)), px(1), border_radius=px(3))
    draw_roof_details(surface, roof, detail_color, seed, px)


def draw_lot_buildings(surface: pygame.Surface, scene: CityScene, lot: CellRect, px: Scale, seed_base: int) -> None:
    """Draw one lot's plaza and rooftops, clipped so shadows never reach the sidewalk."""
    lot_rect = to_pixels(lot, px.tile)
    pygame.draw.rect(surface, PLAZA_EDGE_COLOR, lot_rect.inflate(px(2), px(2)), border_radius=px(9))
    pygame.draw.rect(surface, PLAZA_COLOR, lot_rect, border_radius=px(8))

    lot_cells = {(column, row) for column in range(lot[0], lot[0] + lot[2]) for row in range(lot[1], lot[1] + lot[3])}
    buildings = [
        (index, building)
        for index, building in enumerate(scene.buildings)
        if (building.rect[0], building.rect[1]) in lot_cells
    ]
    shadows = pygame.Surface(lot_rect.size, pygame.SRCALPHA)
    for _, building in buildings:
        footprint = to_pixels(building.rect, px.tile).move(-lot_rect.left, -lot_rect.top)
        offset = building.level * px(4) + px(3)
        pygame.draw.rect(shadows, (20, 16, 30, 85), footprint.move(offset, offset), border_radius=px(6))

    previous_clip = surface.get_clip()
    surface.set_clip(lot_rect)
    surface.blit(shadows, lot_rect)
    for index, building in sorted(buildings, key=lambda item: (item[1].level, item[1].rect[1])):
        draw_building(surface, building, seed_base + index, px)
    surface.set_clip(previous_clip)


@lru_cache(maxsize=None)
def render_background(scene: CityScene) -> pygame.Surface:
    """Draw everything static once. Treat the returned surface as read-only."""
    px = Scale(scene.world.tile_size * SUPERSAMPLE)
    width, height = scene.world.pixel_size
    canvas = pygame.Surface((width * SUPERSAMPLE, height * SUPERSAMPLE))
    canvas.fill(ROAD_COLOR)
    draw_road_markings(canvas, scene, px)

    for block in scene.blocks:
        draw_block(canvas, to_pixels(block, px.tile), px)
    for lot in scene.lots:
        draw_lot_buildings(canvas, scene, lot, px, seed_base=7)
    for crossing in scene.crosswalks:
        draw_crosswalk(canvas, to_pixels(crossing.rect, px.tile), crossing.stripe_direction, px)

    background = pygame.transform.smoothscale(canvas, (width, height))
    return background.convert() if pygame.display.get_surface() else background


def draw_start_marker(screen: pygame.Surface, scene: CityScene) -> None:
    tile = scene.world.tile_size
    column, row = scene.start_cell
    center = (column * tile + tile // 2, row * tile + tile // 2)
    pygame.draw.circle(screen, MARKING_COLOR, center, tile // 3 + 3)
    pygame.draw.circle(screen, START_COLOR, center, tile // 3)


def draw_world(screen: pygame.Surface, scene: CityScene) -> None:
    screen.blit(render_background(scene), (0, 0))
    draw_start_marker(screen, scene)
