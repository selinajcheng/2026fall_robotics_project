"""Integrated city demo: Selina's scene + Mahbub's Robot + trash collection.

Run: python main.py
Screenshot: python main.py --screenshot out.png
Controls: ESC to quit, R to restart. The robot drives autonomously.
Additional Controls:
  SPACE to pause/unpause
  UP / DOWN arrows to adjust speed
  C to toggle runtime configuration screen (click input box to type seed or use +/- for speed)
"""

import os
import sys
import math
import argparse
import random
import csv
from collections import deque
import pygame

from robot import Robot  # Reuse Mahbub's robot implementation unchanged
from sim.collection import TrashCollector
from sim.grid_navigation import find_grid_path, nearest_target, reachable_cells
from sim.render import draw_world
from sim.scene import building_entrance_targets, create_city_scene
from sim.traffic import TrafficSystem
from sim.traffic_render import draw_traffic
from sim.trash_layout import random_trash_cells
from icons import pedestrian_icon, trash_icon, trash_can_icon, robot_icon, obstacle_icon
from sim.pedestrian_grid import PedestrianManager, STEP_TIME
from sim.litter import LitterSystem #pedestrians dropping trash
from sim.interaction import HandoffSystem # pedestrians handing trash to the robot



SCENE = create_city_scene()
TILE = SCENE.world.tile_size

# Temporary fixed test objects until Amaya's scene objects are integrated.
# These are CITY GRID CELLS (column, row), not pixel coordinates.
PEOPLE_CELLS = set()  # CHECKPOINT2_TRAFFIC_V2: no static placeholders
OBSTACLE_CELLS = set()  # Dynamic pedestrians will be integrated separately
STATION_CELL = (1, 2)
TRASH_COUNT = 7
IDLE_RESWEEP_SECONDS = 8.0 #after finishing a sweep, it will wait this long and then sweep the map again
BLOCKED = PEOPLE_CELLS | OBSTACLE_CELLS

#PEDESTRIAN SETTINGS
CLOCK_SPEED = 240  # simulated seconds per real second (4 simulated minutes/second)
CROSSWALK_CELLS = {
    (x,y)
    for c in SCENE.crosswalks
    for x in range(c.rect[0], c.rect[0] + c.rect[2])
    for y in range(c.rect[1], c.rect[1] + c.rect[3])
}

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

def blit_cell(screen, icon, cell):
    screen.blit(icon, icon.get_rect(center = tuple(map(round, cell_center(cell)))))
class Demo:
    def __init__(self, seed=42, time_scale=1.0):
        # Runtime control, seed, & event log attributes
        self.current_seed = seed
        random.seed(seed)
        self.paused = False
        self.time_scale = time_scale
        self.event_log = deque(maxlen=20)
        self.equivalent_1x_seconds = 0.0
        self.completion_logged = False
        
        # Configuration screen state
        self.config_mode = False
        self.seed_input_str = str(seed)
        self.input_box_active = False

        self.trash = random_trash_cells(
            SCENE, TRASH_COUNT, keep_clear={STATION_CELL}, rng=random.Random(seed)
        )
        pedestrian_keep_clear = (
            {STATION_CELL, SCENE.start_cell} | self.trash | CROSSWALK_CELLS
        )
        door_targets = building_entrance_targets(SCENE, pedestrian_keep_clear)

        for cell in PEOPLE_CELLS | OBSTACLE_CELLS | self.trash | {STATION_CELL}:
            if not SCENE.world.is_walkable(cell):
                raise ValueError(f"Scene object {cell} is not on a sidewalk/crosswalk")
        if SCENE.start_cell in BLOCKED:
            raise ValueError("Robot starting cell is blocked")
        if (self.trash | {STATION_CELL}) & BLOCKED:
            raise ValueError("Trash or the station overlaps an obstacle/person")

        self.robot = Robot(*cell_center(SCENE.start_cell))
        # 28px sidewalk cells need a smaller robot than Mahbub's 20px radius.
        self.robot.radius = 9
        self.robot.speed = 168  # pixels per second
        self.collector = TrashCollector(sensor_range=2, capacity=8)
        self.reachable = reachable_cells(SCENE.world, SCENE.start_cell, BLOCKED)
        self.visited = set()
        self.status = "STARTING"
        self.unloading_timer = 0.0  # Pause briefly to show unloading in the demo
        self.simulated_seconds = 5 * 60 * 60  # Start each run at 5:00 AM
        self.traffic = TrafficSystem(SCENE)

        # ----- pedestrians -----
        self.pedestrians = PedestrianManager(
            SCENE.world,                   # the city world
            self.reachable,                # cells pedestrians are allowed to use
            BLOCKED,                       # permanently blocked cells
            door_targets=door_targets,     # entrances and their adjacent building cells
            keep_clear=pedestrian_keep_clear,
            crosswalk_cells=CROSSWALK_CELLS,
            seed=seed
        )

        #----- pedestrians drop trash fro robot to find
        self.total_trash = TRASH_COUNT #total: Starting num + what pedestrians drop
        self.idle_time = 0.0  #time robot has sat at COMPLETE
        self.litter = LitterSystem(
            self.trash,  #dropped trash is added to shared trash set
            self.reachable,  #only drop in areas the robot can get to
            pedestrian_keep_clear, #dont drop on station, start, or crosswalks
            seed = seed    #same seed = same littering
        )
                # ----- human interaction: pedestrians handing trash to the robot -----
        self.handoff = HandoffSystem(SCENE.world, CROSSWALK_CELLS)
        self.carry_img = trash_icon(12, (240, 170, 60))  # small orange bag shown on pedestrians carrying trash
        self.robot_next_cell = None        # cell the robot is currently driving into (None = at rest)
        self.ped_img = pedestrian_icon(20) # pedestrian sprite, 20 px
        self._waiting_at_light = False
        self.can_img = trash_can_icon(26)
        self.robot_img = robot_icon(24)
        self.trash_unseen_img = trash_icon(18, (209, 70, 63)) # red = unseen
        self.trash_seen_img = trash_icon(18, (38, 174, 88)) # green = seen

        self.log_event(f"Simulation initialized with seed {seed}.")

    def log_event(self, message):
        """Record timestamped events for the side panel event log."""
        total_minutes = int(self.simulated_seconds // 60)
        hour_24, minute = divmod(total_minutes, 60)
        hour_12 = hour_24 % 12 or 12
        period = "AM" if hour_24 < 12 else "PM"
        timestamp = f"[{hour_12}:{minute:02d} {period}]"
        self.event_log.append(f"{timestamp} {message}")

    def export_metrics(self, filename="simulation_metrics.csv"):
        """Export final run metrics to a CSV file."""
        file_exists = os.path.isfile(filename)
        try:
            with open(filename, mode='a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Seed", "Collected", "Total Trash", "Unloads", "Visited Cells", "Total Reachable", "Time (1x sec)"])
                writer.writerow([
                    self.current_seed,
                    self.collector.collected_count,
                    self.total_trash,
                    self.collector.unloads,
                    len(self.visited),
                    len(self.reachable),
                    round(self.equivalent_1x_seconds, 1)
                ])
            self.log_event(f"Metrics exported to {filename}")
        except Exception as e:
            self.log_event(f"Failed to export metrics: {e}")

        # ----- pedestrians obey the same crosswalk signal check as the robot -----
    def _pedestrian_may_step(self, cell, next_cell):
        # TILE / STEP_TIME = pedestrian walking speed in pixels per second
        return self.traffic.robot_may_enter(cell, next_cell, TILE / STEP_TIME)

       # ----- what the litter system needs to know about each pedestrian -----
    def _walker_snapshot(self):
        walkers = []
        for p in self.pedestrians.peds:
            # Only people fully outdoors who are NOT saving trash for the robot may litter
            visible = not (p.inside or p.entering or p.exiting or p.carrying_trash)
            walkers.append((id(p), p.cell, visible))   # (unique key, grid cell, may litter?)
        return walkers
    
    def update(self, dt):
        if self.paused or self.config_mode:
            return

        # Accumulate time normalized to 1x speed (dt * time_scale)
        self.equivalent_1x_seconds += dt * self.time_scale
        effective_dt = dt * self.time_scale
        effective_clock_speed = CLOCK_SPEED * self.time_scale

        # Advance the display clock continuously, wrapping after 24 simulated hours.
        self.simulated_seconds = (self.simulated_seconds + effective_dt * effective_clock_speed) % (24 * 60 * 60)

        # Pass the robot's actual cell so cars cannot enter its crossing.
        occupied_cell = (int(self.robot.x // TILE), int(self.robot.y // TILE))

        base_speed = 168
        min_dist_to_person = float('inf')

        if hasattr(self, 'pedestrians') and hasattr(self.pedestrians, 'occupied_cells'):
            for cell in self.pedestrians.occupied_cells():
                p_x = (cell[0] + 0.5) * TILE
                p_y = (cell[1] + 0.5) * TILE
                
                dist = math.hypot(self.robot.x - p_x, self.robot.y - p_y)
                if dist < min_dist_to_person:
                    min_dist_to_person = dist

        SLOW_DOWN_DISTANCE = 120
        if min_dist_to_person < SLOW_DOWN_DISTANCE:
            factor = max(0.3, min_dist_to_person / SLOW_DOWN_DISTANCE)
            self.robot.speed = base_speed * factor
        else:
            self.robot.speed = base_speed

        # ----- pedestrians first, staying out of the robot's cells -----
        robot_cells = {occupied_cell}
        if self.robot_next_cell is not None:
            robot_cells.add(self.robot_next_cell)
        self.pedestrians.update(
            effective_dt, robot_cells, self.simulated_seconds,
            may_step=self._pedestrian_may_step,
        )

        self.traffic.update(effective_dt, robot_cell=occupied_cell,
                            walker_cells = self.pedestrians.occupied_cells())

        # ----- litter: pedestrians may drop trash this frame -----
        new_litter = self.litter.update(effective_dt, self._walker_snapshot(), robot_cells)
        for litter_cell in new_litter:
            self.total_trash += 1                                  # one more piece to collect
            self.log_event(f"Pedestrian dropped trash at {litter_cell}.")


        # Keep the robot parked at the disposal station briefly so the class
        # can see that the bin is unloading before the robot resumes moving.
        if self.unloading_timer > 0:
            self.unloading_timer = max(0.0, self.unloading_timer - effective_dt)
            if self.unloading_timer > 0:
                return

        # Drive ONE grid cell per waypoint. Mahbub's Robot.move() can carry
        # leftover frame time past multiple waypoints, so one at a time lets
        # us reliably test pickups at EVERY visited cell center.
        if self.robot.path:
            self.robot.move(NO_KEYS, effective_dt, *SCENE.world.pixel_size)
        if self.robot.path:
            return  # Still traveling to the next cell center

        self.robot_next_cell = None

        cell = robot_center_cell(self.robot)
        if cell is None:
            raise RuntimeError("Robot stopped between sidewalk cells")

        if cell not in self.visited:
            self.visited.add(cell)

        new_sightings = self.collector.detect(cell, self.trash)
        if new_sightings:
            self.log_event(f"Detected {len(new_sightings)} trash item(s).")

        if self.collector.collect(cell, self.trash):
            self.log_event("Collected trash item.")

        if cell == STATION_CELL and self.collector.current_load > 0: # changed so that robot can throw away without full trash at the end
            if self.collector.unload(cell, STATION_CELL):
                self.unloading_timer = 1.2  # Seconds visible at the disposal station
                self.status = "UNLOADING TRASH"
                self.log_event("Unloaded trash at station.")
                return

        # ----- human interaction: wait for a pedestrian to hand over trash -----
        if not self.collector.is_full and cell not in CROSSWALK_CELLS:
            handoff_state, handoff_event = self.handoff.update(
                effective_dt, cell, self.pedestrians.peds)
        else:
            self.handoff.cancel()                     # full bin or on a crosswalk: don't wait for anyone
            handoff_state, handoff_event = "idle", None

        if handoff_event == "accepted":
            already_there = cell in self.trash        # was there already trash on the robot's cell?
            self.trash.add(cell)                      # put the donated trash on the robot's cell...
            if self.collector.collect(cell, self.trash):  # ...and let the normal pickup take it
                self.total_trash += 1
                self.log_event("Pedestrian put trash in the robot.")
            else:
                if not already_there:
                    self.total_trash += 1             # bin full: trash stays on the ground here
                self.log_event("Bin full: pedestrian left trash at the robot.")

        if handoff_state == "waiting":
            self.status = "WAITING FOR PEDESTRIAN"
            return                                    # stay put until the pedestrian arrives
        if handoff_state == "receiving":
            self.status = "RECEIVING TRASH"
            return                                    # stay put while the trash is handed over
        
        # Define live blocked cells including current pedestrians
        live_blocked = BLOCKED | self.pedestrians.occupied_cells()

        if self.collector.is_full:
            desired = STATION_CELL
            next_status = "FULL - RETURNING TO BIN"
        else:
            # Plan only using trash that the robot has ACTUALLY sensed.
            known_targets = self.collector.known_trash & self.reachable
            desired = nearest_target(SCENE.world, cell, known_targets, live_blocked)
            if desired is not None:
                next_status = "COLLECTING TRASH"
            else:
                desired = nearest_target(
                    SCENE.world, cell, self.reachable - self.visited, live_blocked
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

        # Check if simulation just reached COMPLETE status
        if next_status == "COMPLETE" and not self.completion_logged:
            self.completion_logged = True
            self.log_event(f"Robot finished! Took {self.equivalent_1x_seconds:.1f}s at 1x speed.")
            self.export_metrics()

        # ----- keep patrolling: after sitting idle, sweep the whole map again to find new litter -----
        if next_status == "COMPLETE":
            self.idle_time += effective_dt                 # count time spent idle
            if self.idle_time >= IDLE_RESWEEP_SECONDS:
                self.visited.clear()                       # forget visited cells so the robot sweeps again
                self.idle_time = 0.0
        else:
            self.idle_time = 0.0                           # busy again, reset the idle timer


        # Replan each time the robot arrives at a cell. This allows newly
        # detected trash to interrupt exploration without skipping pickups.
        if desired is not None and desired != cell:
            # ----- plan around pedestrians standing on (or stepping onto) cells -----
            live_blocked = BLOCKED | self.pedestrians.occupied_cells()  # permanent blocks + pedestrians right now
            path = find_grid_path(SCENE.world, cell, desired, live_blocked)
            if len(path) < 2:
                # Check again WITHOUT pedestrians: if still no route, it's a real bug, so raise
                if len(find_grid_path(SCENE.world, cell, desired, BLOCKED)) < 2:
                    raise RuntimeError(f"No route from {cell} to target {desired}")
                # Otherwise a pedestrian is just in the way, so wait and retry next frame
                self.status = "YIELDING TO PEDESTRIAN"
                return

            # Pass just ONE city-grid waypoint (converted to pixel center)
            # to Mahbub's existing Robot.set_path()/Robot.move().
            # Wait *before* entering a crosswalk on a red WALK signal.
            # Continue through a crossing once entered (no stopping in road).
            if not self.traffic.robot_may_enter(cell, path[1], self.robot.speed):
                if not self._waiting_at_light:
                    self.traffic.wait_events += 1
                self._waiting_at_light = True
                self.status = 'WAITING FOR GREEN LIGHT'
                return
            self._waiting_at_light = False
            self.robot.set_path([cell_center(path[1])])
            self.robot_next_cell = path[1]  # reserve the cell we're driving into so pedestrians stay out
        self.status = next_status

    def draw(self, screen):
        draw_world(screen, SCENE)  # Selina's original city unchanged
        draw_traffic(screen, SCENE, self.traffic)
        blit_cell(screen, self.can_img, STATION_CELL)
        self.litter.draw(screen, TILE)  # expanding ring where trash was just dropped
        for cell in self.trash:
            discovered = cell in self.collector.known_trash
            blit_cell(screen, self.trash_seen_img if discovered else self.trash_unseen_img, cell)
        self.pedestrians.draw(screen, self.ped_img) # draw all visible pedestrians
                # Small orange bag on pedestrians who are carrying trash for the robot
        for p in self.pedestrians.peds:
            if p.carrying_trash and not (p.entering or p.exiting or p.inside):
                pos = p.pixel_pos(TILE)
                screen.blit(self.carry_img, self.carry_img.get_rect(center=(round(pos.x) + 9, round(pos.y) - 10)))
        screen.blit(self.robot_img, self.robot_img.get_rect(center=(round(self.robot.x), round(self.robot.y))))

        map_width = SCENE.world.pixel_size[0]

        # Bottom information panel (HUD)
        hud_height = 108
        hud_top = SCENE.world.pixel_size[1]
        hud = pygame.Surface((map_width, hud_height), pygame.SRCALPHA)
        hud.fill((17, 22, 30, 215))
        screen.blit(hud, (0, hud_top))

        font = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 19)
        white = (255, 255, 255)

        total_minutes = int(self.simulated_seconds // 60)
        hour_24, minute = divmod(total_minutes, 60)
        period = "AM" if hour_24 < 12 else "PM"
        hour_12 = hour_24 % 12 or 12
        speed_label = f" | Speed: {self.time_scale}x" if self.time_scale != 1.0 else ""
        pause_label = " ** PAUSED **" if (self.paused or self.config_mode) else ""
        clock_text = font.render(f"{hour_12}:{minute:02d} {period}{speed_label}{pause_label}", True, (255, 220, 100) if (self.paused or self.config_mode) else white)
        screen.blit(clock_text, clock_text.get_rect(midtop=(map_width // 2, hud_top + 7)))

        summary = (
            f"Collected: {self.collector.collected_count}/{self.total_trash}"
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
        instructions = f"R = restart | Space = pause | Up/Dn = speed | C = config | Esc = quit"
        screen.blit(small_font.render(instructions, True, (218, 223, 230)), (14, hud_top + 87))

        # Right-side panel (320px width) for Legend & Event Log
        panel_x = map_width
        panel_width = 320
        total_height = SCENE.world.pixel_size[1] + hud_height
        
        side_panel = pygame.Surface((panel_width, total_height), pygame.SRCALPHA)
        side_panel.fill((20, 25, 35, 255))
        screen.blit(side_panel, (panel_x, 0))
        pygame.draw.line(screen, (70, 80, 95), (panel_x, 0), (panel_x, total_height), 2)

        # Legend section in side panel
        screen.blit(font.render("Map Legend", True, (255, 200, 100)), (panel_x + 15, 15))
        
        col1_x = panel_x + 15
        col2_x = panel_x + 165
        
        # row 1 col 1: unseen trash
        screen.blit(self.trash_unseen_img, self.trash_unseen_img.get_rect(center=(col1_x + 12, 55)))
        screen.blit(small_font.render("Unseen Trash", True, white), (col1_x + 32, 49))

        # row 1 col 2: disposal station
        screen.blit(self.can_img, self.can_img.get_rect(center=(col2_x + 12, 55)))
        screen.blit(small_font.render("Station", True, white), (col2_x + 32, 49))

        # row 2 col 1: detected trash
        screen.blit(self.trash_seen_img, self.trash_seen_img.get_rect(center=(col1_x + 12, 85)))
        screen.blit(small_font.render("Detected Trash", True, white), (col1_x + 32, 79))

        # row 2 col 2: start location
        pygame.draw.circle(screen, (240, 240, 235), (col2_x + 12, 85), 12)
        pygame.draw.circle(screen, (38, 112, 207), (col2_x + 12, 85), 9)
        screen.blit(small_font.render("Start Loc", True, white), (col2_x + 32, 79))

        # Display Seed info
        screen.blit(small_font.render(f"Seed: {self.current_seed}", True, white), (col1_x, 115))
        pygame.draw.line(screen, (50, 60, 75), (panel_x + 15, 140), (panel_x + panel_width - 15, 140), 1)

        # Event Log section in side panel with text wrapping
        screen.blit(font.render("Event Log", True, (255, 200, 100)), (panel_x + 15, 155))
        log_start_y = 185
        max_log_width = panel_width - 30

        # Build wrapped lines from the log messages
        wrapped_lines = []
        for msg in list(self.event_log):
            words = msg.split(' ')
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if small_font.size(test_line)[0] <= max_log_width:
                    current_line.append(word)
                else:
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                wrapped_lines.append(' '.join(current_line))

        # Render only the lines that fit in the remaining vertical space
        line_height = 18
        max_lines = (total_height - log_start_y - 15) // line_height
        for idx, line_text in enumerate(wrapped_lines[-max_lines:]):
            m_surf = small_font.render(line_text, True, (220, 225, 235))
            screen.blit(m_surf, (panel_x + 15, log_start_y + (idx * line_height)))

        # Runtime Configuration Overlay Screen
        if self.config_mode:
            overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            cfg_box = pygame.Rect(screen.get_width() // 2 - 210, screen.get_height() // 2 - 160, 420, 320)
            pygame.draw.rect(screen, (30, 35, 45), cfg_box, border_radius=10)
            pygame.draw.rect(screen, (100, 110, 130), cfg_box, width=2, border_radius=10)

            title_font = pygame.font.Font(None, 28)
            screen.blit(title_font.render("Runtime Configuration", True, (255, 255, 255)), (cfg_box.x + 90, cfg_box.y + 20))
            
            screen.blit(font.render(f"Current Active Seed: {self.current_seed}", True, (200, 220, 240)), (cfg_box.x + 30, cfg_box.y + 60))
            
            # Speed display with (-) and (+) buttons
            screen.blit(font.render(f"Speed: {self.time_scale}x", True, (200, 220, 240)), (cfg_box.x + 30, cfg_box.y + 95))
            
            # Draw minus button
            minus_btn = pygame.Rect(cfg_box.x + 290, cfg_box.y + 92, 35, 26)
            pygame.draw.rect(screen, (60, 70, 85), minus_btn, border_radius=4)
            pygame.draw.rect(screen, (120, 140, 170), minus_btn, width=1, border_radius=4)
            screen.blit(font.render("-", True, (255, 255, 255)), (minus_btn.x + 13, minus_btn.y + 3))

            # Draw plus button
            plus_btn = pygame.Rect(cfg_box.x + 335, cfg_box.y + 92, 35, 26)
            pygame.draw.rect(screen, (60, 70, 85), plus_btn, border_radius=4)
            pygame.draw.rect(screen, (120, 140, 170), plus_btn, width=1, border_radius=4)
            screen.blit(font.render("+", True, (255, 255, 255)), (plus_btn.x + 11, plus_btn.y + 3))

            screen.blit(font.render("Click box below & type new seed:", True, (255, 200, 100)), (cfg_box.x + 30, cfg_box.y + 135))

            # Input text box with focus highlighting
            input_box = pygame.Rect(cfg_box.x + 30, cfg_box.y + 165, 360, 38)
            box_border_color = (70, 180, 100) if self.input_box_active else (120, 140, 170)
            pygame.draw.rect(screen, (50, 60, 75), input_box, border_radius=5)
            pygame.draw.rect(screen, box_border_color, input_box, width=2, border_radius=5)
            
            txt_surf = font.render(self.seed_input_str, True, (255, 255, 255))
            screen.blit(txt_surf, (input_box.x + 12, input_box.y + 9))

            instructions_text = "[Enter] Apply & Restart | [C] or [ESC] Close Config"
            screen.blit(small_font.render(instructions_text, True, (180, 190, 205)), (cfg_box.x + 40, cfg_box.y + 230))


def run(frame_limit=None, screenshot=None, seed=42):
    pygame.init()
    width, height = SCENE.world.pixel_size
    hud_height = 108
    side_panel_width = 320
    screen = pygame.display.set_mode((width + side_panel_width, height + hud_height))
    pygame.display.set_caption(f"Sidewalk Trash Robot - Seed: {seed}")
    clock = pygame.time.Clock()
    demo = Demo(seed=seed, time_scale=1.0)
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
        
        # Calculate UI element rects in screen coordinates during config mode
        screen_w, screen_h = width + side_panel_width, height + hud_height
        cfg_box = pygame.Rect(screen_w // 2 - 210, screen_h // 2 - 160, 420, 320)
        input_box = pygame.Rect(cfg_box.x + 30, cfg_box.y + 165, 360, 38)
        minus_btn = pygame.Rect(cfg_box.x + 290, cfg_box.y + 92, 35, 26)
        plus_btn = pygame.Rect(cfg_box.x + 335, cfg_box.y + 92, 35, 26)

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                if demo.config_mode:
                    demo.config_mode = False
                else:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and demo.config_mode:
                if input_box.collidepoint(event.pos):
                    demo.input_box_active = True
                else:
                    demo.input_box_active = False

                if minus_btn.collidepoint(event.pos):
                    demo.time_scale = round(max(0.5, demo.time_scale - 0.5), 1)
                elif plus_btn.collidepoint(event.pos):
                    demo.time_scale = round(min(5.0, demo.time_scale + 0.5), 1)
            elif event.type == pygame.KEYDOWN:
                if demo.config_mode:
                    if event.key == pygame.K_c:
                        # Pressing C again toggles configuration mode closed
                        demo.config_mode = False
                    elif event.key == pygame.K_UP:
                        demo.time_scale = round(min(5.0, demo.time_scale + 0.5), 1)
                    elif event.key == pygame.K_DOWN:
                        demo.time_scale = round(max(0.5, demo.time_scale - 0.5), 1)
                    elif event.key == pygame.K_RETURN:
                        try:
                            new_seed = int(demo.seed_input_str)
                            current_speed = demo.time_scale
                            demo = Demo(seed=new_seed, time_scale=current_speed)
                            demo.update(0.0)
                        except ValueError:
                            # Invalid input; close config and continue simulation
                            demo.config_mode = False
                    elif event.key == pygame.K_BACKSPACE and demo.input_box_active:
                        demo.seed_input_str = demo.seed_input_str[:-1]
                    else:
                        if demo.input_box_active:
                            if event.unicode.isdigit() or (event.unicode == '-' and len(demo.seed_input_str) == 0):
                                demo.seed_input_str += event.unicode
                else:
                    # Normal simulation keybindings
                    if event.key == pygame.K_r:
                        demo = Demo(seed=demo.current_seed, time_scale=demo.time_scale)
                        demo.update(0.0)
                    elif event.key == pygame.K_c:
                        demo.config_mode = True
                        demo.seed_input_str = str(demo.current_seed)
                        demo.input_box_active = False
                    elif event.key == pygame.K_SPACE:
                        demo.paused = not demo.paused
                        demo.log_event("Simulation " + ("paused." if demo.paused else "resumed."))
                    elif event.key == pygame.K_UP:
                        demo.time_scale = round(min(5.0, demo.time_scale + 0.5), 1)
                    elif event.key == pygame.K_DOWN:
                        demo.time_scale = round(max(0.5, demo.time_scale - 0.5), 1)

        demo.update(dt)
        demo.draw(screen)
        pygame.display.flip()
        frames += 1
        if frame_limit is not None and frames >= frame_limit:
            running = False
    pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sidewalk Trash Collection Robot Simulation")
    parser.add_argument("--screenshot", type=str, default=None, help="Save screenshot and exit")
    args = parser.parse_args()

    # Generate a random seed by default since command-line seed input was removed
    chosen_seed = random.randint(0, 999999)

    if args.screenshot:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        run(screenshot=args.screenshot, seed=chosen_seed)
    else:
        run(seed=chosen_seed)
