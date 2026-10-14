"""Integrated city demo: Selina's scene + Mahbub's Robot + trash collection.

Run: python main.py
Screenshot: python main.py --screenshot out.png
Controls: ESC to quit, R to restart. The robot drives autonomously.
"""

import os
import sys

import pygame

from robot import Robot  # Reuse Mahbub's robot implementation unchanged
from sim.collection import TrashCollector
from sim.grid_navigation import find_grid_path, nearest_target, reachable_cells
from sim.render import draw_world
from sim.scene import create_city_scene


SCENE = create_city_scene()
TILE = SCENE.world.tile_size

# Temporary fixed test objects until Amaya's scene objects are integrated.
# These are CITY GRID CELLS (column, row), not pixel coordinates.
PEOPLE_CELLS = {(8, 1), (25, 14)}
OBSTACLE_CELLS = {(14, 0), (30, 15)}
TRASH_CELLS = {(4, 1), (13, 1), (21, 1), (34, 21), (22, 22), (1, 20), (14, 16)}
STATION_CELL = (1, 2)
BLOCKED = PEOPLE_CELLS | OBSTACLE_CELLS

# Mahbub's Robot.move() expects an indexable keyboard object; supplying
# false for every key gives autonomous movement with no manual override.
class NoKeys:
    def __getitem__(self, _key):
        return False


NO_KEYS = NoKeys()


def cell_center(cell):
    return ((cell[0] + 0.5) * TILE, (cell[1] + 0.5) * TILE)


def robot_center_cell(robot):
    """Only report a cell after the robot has arrived at its exact center."""
    cell = (int(robot.x // TILE), int(robot.y // TILE))
    x, y = cell_center(cell)
    if abs(robot.x - x) < 0.001 and abs(robot.y - y) < 0.001:
        return cell
    return None


def draw_cell_circle(screen, cell, color, radius):
    pygame.draw.circle(screen, color, tuple(map(round, cell_center(cell))), radius)


class Demo:
    def __init__(self):
        for cell in PEOPLE_CELLS | OBSTACLE_CELLS | TRASH_CELLS | {STATION_CELL}:
            if not SCENE.world.is_walkable(cell):
                raise ValueError(f"Scene object {cell} is not on a sidewalk/crosswalk")
        if SCENE.start_cell in BLOCKED:
            raise ValueError("Robot starting cell is blocked")
        if (TRASH_CELLS | {STATION_CELL}) & BLOCKED:
            raise ValueError("Trash or the station overlaps an obstacle/person")

        self.robot = Robot(*cell_center(SCENE.start_cell))
        # 28px sidewalk cells need a smaller robot than Mahbub's 20px radius.
        self.robot.radius = 9
        self.robot.speed = 168  # pixels per second
        self.trash = set(TRASH_CELLS)  # World knows all trash; robot does not
        self.collector = TrashCollector(sensor_range=2, capacity=3)
        self.reachable = reachable_cells(SCENE.world, SCENE.start_cell, BLOCKED)
        self.visited = set()
        self.status = "STARTING"
        self.unloading_timer = 0.0  # Pause briefly to show unloading in the demo

    def update(self, dt):
        # Keep the robot parked at the disposal station briefly so the class
        # can see that the bin is unloading before the robot resumes moving.
        if self.unloading_timer > 0:
            self.unloading_timer = max(0.0, self.unloading_timer - dt)
            if self.unloading_timer > 0:
                return

        # Drive ONE grid cell per waypoint. Mahbub's Robot.move() can carry
        # leftover frame time past multiple waypoints, so one at a time lets
        # us reliably test pickups at EVERY visited cell center.
        if self.robot.path:
            self.robot.move(NO_KEYS, dt, *SCENE.world.pixel_size)
        if self.robot.path:
            return  # Still traveling to the next cell center

        cell = robot_center_cell(self.robot)
        if cell is None:
            raise RuntimeError("Robot stopped between sidewalk cells")

        self.visited.add(cell)
        self.collector.detect(cell, self.trash)
        self.collector.collect(cell, self.trash)
        if cell == STATION_CELL and self.collector.current_load > 0: # changed so that robot can throw away without full trash at the end
            if self.collector.unload(cell, STATION_CELL):
                self.unloading_timer = 1.2  # Seconds visible at the disposal station
                self.status = "UNLOADING TRASH"
                return

        if self.collector.is_full:
            desired = STATION_CELL
            next_status = "FULL - RETURNING TO BIN"
        else:
            # Plan only using trash that the robot has ACTUALLY sensed.
            known_targets = self.collector.known_trash & self.reachable
            desired = nearest_target(SCENE.world, cell, known_targets, BLOCKED)
            if desired is not None:
                next_status = "COLLECTING TRASH"
            else:
                desired = nearest_target(
                    SCENE.world, cell, self.reachable - self.visited, BLOCKED
                )
                if desired is not None:
                    next_status = "SWEEPING SIDEWALKS"
                else:
                    # after sweeping is done then dump out trash if has trash otherwise go to start
                    if self.collector.current_load > 0:
                        desired = STATION_CELL
                        next_status = "RETURNING TO STATION"
                    elif cell != SCENE.start_cell:
                        desired = SCENE.start_cell
                        next_status = "RETURNING TO START"
                    else:
                        desired = None
                        next_status = "COMPLETE"

        # Replan each time the robot arrives at a cell. This allows newly
        # detected trash to interrupt exploration without skipping pickups.
        if desired is not None and desired != cell:
            path = find_grid_path(SCENE.world, cell, desired, BLOCKED)
            if len(path) < 2:
                raise RuntimeError(f"No route from {cell} to target {desired}")
            # Pass just ONE city-grid waypoint (converted to pixel center)
            # to Mahbub's existing Robot.set_path()/Robot.move().
            self.robot.set_path([cell_center(path[1])])
        self.status = next_status

    def draw(self, screen):
        draw_world(screen, SCENE)  # Selina's original city unchanged
        for cell in OBSTACLE_CELLS:
            center = tuple(map(round, cell_center(cell)))
            pygame.draw.rect(screen, (90, 90, 100), pygame.Rect(center[0]-10, center[1]-10, 20, 20), border_radius=3)
        for cell in PEOPLE_CELLS:
            draw_cell_circle(screen, cell, (239, 141, 37), 10)
            draw_cell_circle(screen, cell, (250, 232, 199), 3)
        draw_cell_circle(screen, STATION_CELL, (45, 155, 89), 12)
        draw_cell_circle(screen, STATION_CELL, (255, 255, 255), 5)
        for cell in self.trash:
            discovered = cell in self.collector.known_trash
            draw_cell_circle(screen, cell, (38, 174, 88) if discovered else (209, 70, 63), 7)
        self.robot.draw(screen)  # Mahbub's original drawing code

        # Bottom information panel (HUD)
        hud_height = 108
        hud_top = screen.get_height() - hud_height
        hud = pygame.Surface((screen.get_width(), hud_height), pygame.SRCALPHA)
        hud.fill((17, 22, 30, 215))
        screen.blit(hud, (0, hud_top))

        font = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 19)
        white = (255, 255, 255)

        summary = (
            f"Collected: {self.collector.collected_count}/{len(TRASH_CELLS)}"
            f"     Unloads: {self.collector.unloads}"
            f"     Visited: {len(self.visited)}/{len(self.reachable)}"
        )
        screen.blit(font.render(summary, True, white), (14, hud_top + 7))

        # Highlight the two bin-related states for the live demo.
        bin_status = self.collector.is_full or self.status == "UNLOADING TRASH"
        status_color = (255, 186, 73) if bin_status else (121, 223, 160)
        status_text = f"Status: {self.status}"
        screen.blit(font.render(status_text, True, status_color), (14, hud_top + 31))

        load = self.collector.current_load
        capacity = self.collector.capacity
        screen.blit(font.render(f"Capacity: {load}/{capacity}", True, white), (14, hud_top + 58))

        bar_x, bar_y, bar_width, bar_height = 156, hud_top + 59, 245, 17
        background_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(screen, (65, 72, 82), background_rect, border_radius=7)
        fill_width = round(bar_width * load / capacity)
        if fill_width:
            fill_color = (240, 155, 52) if self.collector.is_full else (48, 190, 110)
            pygame.draw.rect(
                screen, fill_color,
                pygame.Rect(bar_x, bar_y, fill_width, bar_height), border_radius=7
            )
        pygame.draw.rect(screen, (225, 232, 240), background_rect, width=2, border_radius=7)

        percent = round(load / capacity * 100)
        screen.blit(font.render(f"{percent}% full", True, white), (bar_x + bar_width + 12, hud_top + 58))
        instructions = "R = restart | Esc = quit"
        screen.blit(small_font.render(instructions, True, (218, 223, 230)), (14, hud_top + 87))

        # right side of bottom info panel with 2 columns
        legend_x = screen.get_width() - 340
        col1_x = legend_x
        col2_x = legend_x + 165
        
        # row 1 col 1: unseen trash
        pygame.draw.circle(screen, (209, 70, 63), (col1_x + 12, hud_top + 22), 7)
        screen.blit(small_font.render("Unseen Trash", True, white), (col1_x + 32, hud_top + 16))

        # row 1 col 2:disposal station
        pygame.draw.circle(screen, (45, 155, 89), (col2_x + 12, hud_top + 22), 12)
        pygame.draw.circle(screen, (255, 255, 255), (col2_x + 12, hud_top + 22), 5)
        screen.blit(small_font.render("Disposal Station", True, white), (col2_x + 32, hud_top + 16))

        # row 2 col 1: detected trash
        pygame.draw.circle(screen, (38, 174, 88), (col1_x + 12, hud_top + 50), 7)
        screen.blit(small_font.render("Detected Trash", True, white), (col1_x + 32, hud_top + 44))

        # row 2 col 1: start location
        pygame.draw.circle(screen, (240, 240, 235), (col2_x + 12, hud_top + 50), 12)
        pygame.draw.circle(screen, (38, 112, 207), (col2_x + 12, hud_top + 50), 9)
        screen.blit(small_font.render("Start Location", True, white), (col2_x + 32, hud_top + 44))

        # row 3 col 1: Person
        pygame.draw.circle(screen, (239, 141, 37), (col1_x + 12, hud_top + 78), 10)
        pygame.draw.circle(screen, (250, 232, 199), (col1_x + 12, hud_top + 78), 3)
        screen.blit(small_font.render("Person", True, white), (col1_x + 32, hud_top + 72))

        # row 3 col 2: obstacle
        pygame.draw.rect(screen, (90, 90, 100), pygame.Rect(col2_x + 4, hud_top + 68, 16, 16), border_radius=3)
        screen.blit(small_font.render("Obstacle", True, white), (col2_x + 32, hud_top + 72))


def run(frame_limit=None, screenshot=None):
    pygame.init()
    width, height = SCENE.world.pixel_size
    hud_height = 108
    screen = pygame.display.set_mode((width, height + hud_height))
    pygame.display.set_caption("Sidewalk Trash Robot - Integrated Checkpoint 1")
    clock = pygame.time.Clock()
    demo = Demo()
    demo.update(0.0)

    if screenshot is not None:
        demo.draw(screen)
        pygame.image.save(screen, screenshot)
        pygame.quit()
        return

    frames = 0
    running = True
    while running:
        dt = min(clock.tick(60) / 1000, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                demo = Demo()
                demo.update(0.0)

        demo.update(dt)
        demo.draw(screen)
        pygame.display.flip()
        frames += 1
        if frame_limit is not None and frames >= frame_limit:
            running = False
    pygame.quit()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--screenshot":
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        run(screenshot=sys.argv[2])
    else:
        run()
