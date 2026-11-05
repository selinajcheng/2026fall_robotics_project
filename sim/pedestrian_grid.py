""" CHECK POINT 2: Pedestrian Grid

Pedestrians walk in the sidewalk/crosswalk cells. The robot will treat the cells they occupy as temporarily blocked and yields until they pass. 

NEW RULES FOR PEDESTRIANS:
1: head on pedestrians can walk through/past eachother
2: nobody steps onto the crosswalk unles the WHOLE crossing is clear so that no one gets stranded in the street
"""
import random
import pygame
from sim.grid_navigation import find_grid_path
from sim.pedestrian_schedule import PedestrianSchedule

#CONFIG
STEP_TIME = 0.5 #seconds it takes to walk one cell
ENTRY_TIME = 0.75 #seconds to walk from an entrance into a building and fade
STUCK_TIMEOUT = 2.0 #seconds of being blocked giving up and picking a new destination

# ===== SINGLE PEDESTRIAN =====
class Pedestrian:
    def __init__(self, world, door_targets, cells, static_blocked, rng, start_cell,
                 return_at, cohort, crosswalk_cells=()):
        self.world = world                  # the city world (needed by find_grid_path)
        self.door_targets = door_targets    # entrance cell -> adjacent cell inside its building
        self.doors = list(door_targets)
        self.cells = cells                  # list of cells usable as random "stroll" destinations
        self.static_blocked = static_blocked  # permanently blocked cells (never walk through these)
        self.rng = rng                      # shared random generator (seeded so runs repeat)
        self.crosswalk_cells = set(crosswalk_cells) #every cell that is part of a crosswalk
        self.cell = start_cell              # the cell the pedestrian is standing on / just left
        self.next_cell = None               # the cell being walked into (None = standing still)
        self.progress = 0.0                 # how far along the step is: 0.0 = start, 1.0 = arrived
        self.path = []                      # cells still to walk through, in order
        self.goal = None                    # final destination cell of the current trip
        self.goal_is_door = False           # True if the goal is a building door (enter on arrival)
        self.inside = False                 # becomes True only after completing a return route
        self.exiting = True                 # spawn by fading/walking out of the assigned building
        self.entering = False               # True while walking/fading into a building
        self.entry_target = self.door_targets[start_cell]
        self.entry_progress = 0.0
        self.return_at = return_at          # accelerated-clock time to begin heading inside
        self.returning = False
        self.cohort = cohort
        self.blocked_time = 0.0             # how long someone has been in the way of our next step
 
    # --- picking where to go next ---
    def _choose_goal(self):
        for _ in range(5):                  # try up to 5 times to find a reachable destination
            if self.returning:
                goal, is_door = self.rng.choice(self.doors), True
            else:
                goal, is_door = self.rng.choice(self.cells), False
            if goal == self.cell:
                continue                    # already standing there, pick again
            route = find_grid_path(self.world, self.cell, goal, self.static_blocked)
            if len(route) >= 2:             # a valid route has at least start + one more cell
                self.goal, self.goal_is_door = goal, is_door
                self.path = list(route[1:])  # drop route[0]: that's the cell we're already on
                return
        self.path = []                      # nothing reachable found; try again next frame
 
    def _drop_goal(self):
        # Forget the current trip entirely (used when arriving, giving up, or leaving a building)
        self.path = []
        self.goal = None
        self.goal_is_door = False

    # --- crosswalk safety: is anything in the way of the WHOLE crossing? ---
    def _crossing_blocked(self, blocked):
        for c in self.path:                 # walk along the upcoming route
            if c not in self.crosswalk_cells:
                break                       # past the end of the crosswalk: stop checking
            if c in blocked:
                return True                 # someone is on a crosswalk cell we need
        return False

    # --- head-on check: are we and 'other' trying to swap places? ---
    def is_head_on_with(self, other):
        if (self.inside or other.inside or self.entering or other.entering
                or self.exiting or other.exiting):
            return False                    # people inside buildings aren't in the way
        if self.next_cell is not None or other.next_cell is not None:
            return False                    # only handle two pedestrians who are both standing still
        if not self.path or not other.path:
            return False                    # someone has no route right now
        # Each one wants the cell the other is standing on
        return self.path[0] == other.cell and other.path[0] == self.cell
 
    # --- per-frame update ---
    def update(self, dt, blocked, simulated_seconds, may_step=None, passable=()):
        """dt = seconds since last frame.
        blocked = cells held by the robot and other pedestrians (not our own).
        may_step = optional function(cell, next_cell) -> bool, used for crosswalk signals."""
 
        # Finished pedestrians remain hidden until the manager removes them.
        if self.inside:
            return

        # Spawn from inside the building, fading in until fully clear of its edge.
        if self.exiting:
            self.entry_progress = min(1.0, self.entry_progress + dt / ENTRY_TIME)
            if self.entry_progress >= 1.0:
                self.exiting = False
                self.entry_progress = 0.0
            return

        # This final off-grid step visually carries the pedestrian through
        # the building edge. The entrance stays occupied until the fade ends.
        if self.entering:
            self.entry_progress = min(1.0, self.entry_progress + dt / ENTRY_TIME)
            if self.entry_progress >= 1.0:
                self.inside = True
            return

        # Reaching the scheduled time starts a routed trip to an entrance.
        if not self.returning and simulated_seconds >= self.return_at:
            self.returning = True
            self._drop_goal()
 
        # ----- mid-step: keep walking toward next_cell -----
        if self.next_cell is not None:
            self.progress += dt / STEP_TIME  # advance the step by the fraction of STEP_TIME elapsed
            if self.progress < 1.0:
                return                      # still between cells; wait for the step to finish
            self.cell = self.next_cell      # step finished: we now officially stand on the new cell
            self.next_cell = None
            self.progress = 0.0
 
        # ----- reached a door: go inside -----
        if self.goal_is_door and self.cell == self.goal:
            self.entering = True
            self.entry_target = self.door_targets[self.cell]
            self.entry_progress = 0.0
            self._drop_goal()
            return
 
        # ----- need a new destination? -----
        if not self.path:                   # path is empty = trip finished (or none started yet)
            self._drop_goal()
            self._choose_goal()             # pick a new destination and compute the route
            if not self.path:
                return                      # couldn't find one; try again next frame
 
        # ----- try to step onto the next cell -----
        nxt = self.path[0]                  # the next cell on our route (peek, don't remove yet)
        if may_step is not None and not may_step(self.cell, nxt):
            return                          # a crosswalk signal says wait; this is NOT counted as stuck
        # About to step from the curb onto a crosswalk: wait until the whole crossing is clear
        if nxt in self.crosswalk_cells and self.cell not in self.crosswalk_cells:
            if self._crossing_blocked(blocked):
                return                      # wait on the curb (not counted as stuck)

        # Blocked by someone? (head-on pedestrians are 'passable', so we just walk past them)
        if nxt in blocked and nxt not in passable:
            self.blocked_time += dt         # count how long we've been waiting on them
            # Give up on the trip, but NEVER while standing in a crosswalk
            if self.blocked_time > STUCK_TIMEOUT and self.cell not in self.crosswalk_cells:
                self.blocked_time = 0.0
                self._drop_goal()           # retry a destination (or another entrance)
            return
        self.blocked_time = 0.0             # path is clear, reset the stuck timer
        self.next_cell = self.path.pop(0)   # commit to the step (also reserves that cell for others)
        self.progress = 0.0
 
    # --- what the robot needs to know ---
    def occupied_cells(self):
        if self.inside:
            return set()                    # people inside buildings block nothing
        cells = {self.cell}                 # the cell we're standing on
        if self.next_cell is not None:
            cells.add(self.next_cell)       # plus the cell we're walking into (reserved early)
        return cells
 
    # --- drawing helper: smooth position between cells ---
    def pixel_pos(self, tile):
        # Pixel center of the current cell
        a = pygame.Vector2((self.cell[0] + 0.5) * tile, (self.cell[1] + 0.5) * tile)
        if self.entering:
            b = pygame.Vector2(
                (self.entry_target[0] + 0.5) * tile,
                (self.entry_target[1] + 0.5) * tile,
            )
            return a.lerp(b, self.entry_progress)
        if self.exiting:
            b = pygame.Vector2(
                (self.entry_target[0] + 0.5) * tile,
                (self.entry_target[1] + 0.5) * tile,
            )
            return b.lerp(a, self.entry_progress)
        if self.next_cell is None:
            return a                        # standing still: draw at the cell center
        # Pixel center of the cell we're walking into
        b = pygame.Vector2((self.next_cell[0] + 0.5) * tile, (self.next_cell[1] + 0.5) * tile)
        return a.lerp(b, self.progress)     # slide from a to b by 'progress' (0..1)
 
 
# ===== MANAGER (what main.py talks to) =====
class PedestrianManager:
    def __init__(self, world, cells, static_blocked, door_targets, seed=7,
                 keep_clear=(), crosswalk_cells=()):
        if not door_targets:
            raise ValueError("PedestrianManager requires at least one building entrance")
        self.world = world
        self.cells = sorted(c for c in cells if c not in static_blocked and c not in keep_clear)
        self.static_blocked = static_blocked
        self.crosswalk_cells = crosswalk_cells
        self.rng = random.Random(seed)       # seeded so runs repeat
        self.tile = world.tile_size         # pixels per grid cell (for drawing)
        self.door_targets = dict(door_targets)
        self.doors = list(door_targets)
        self.rng.shuffle(self.doors)
        self.door_cursor = 0
        self.peds = []                      # only pedestrians currently outdoors
        self.pending = []                   # scheduled people waiting for a clear entrance
        self.schedule = PedestrianSchedule(seed + 1)

    def _queue_requests(self, simulated_seconds):
        for request in self.schedule.update(simulated_seconds):
            self.pending.extend((return_at, request.label) for return_at in request.return_times)

    def _release_pending(self, robot_cells):
        occupied = set(robot_cells) | self.occupied_cells()
        remaining = []
        for return_at, cohort in self.pending:
            selected = None
            for offset in range(len(self.doors)):
                index = (self.door_cursor + offset) % len(self.doors)
                candidate = self.doors[index]
                if candidate not in occupied:
                    selected = candidate
                    self.door_cursor = (index + 1) % len(self.doors)
                    break
            if selected is None:
                remaining.append((return_at, cohort))
                continue
            pedestrian = Pedestrian(
                self.world, self.door_targets, self.cells, self.static_blocked,
                self.rng, selected, return_at, cohort, self.crosswalk_cells,
            )
            self.peds.append(pedestrian)
            occupied.add(selected)
        self.pending = remaining

    def update(self, dt, robot_cells, simulated_seconds, may_step=None):
        self._queue_requests(simulated_seconds)
        self._release_pending(robot_cells)
        for p in self.peds:
            blocked = set(robot_cells)      # start with the cells the robot holds
            passable = set()                # cells of head-on pedestrians p may walk past
            for other in self.peds:
                if other is p:
                    continue
                blocked |= other.occupied_cells()  # add every OTHER pedestrian's cells
                if p.is_head_on_with(other):
                    passable.add(other.cell)       # standoff: let them swap
            p.update(dt, blocked, simulated_seconds, may_step, passable)
        self.peds = [p for p in self.peds if not p.inside]
 
    def occupied_cells(self):
        # All cells currently held by any visible pedestrian (the robot and traffic read this)
        cells = set()
        for p in self.peds:
            cells |= p.occupied_cells()
        return cells
 
    def draw(self, screen, icon):
        for p in self.peds:
            if p.inside:
                continue                    # hidden while inside a building
            pos = p.pixel_pos(self.tile)    # smooth pixel position between cells
            draw_icon = icon
            if p.entering or p.exiting:
                horizontal = p.entry_target[0] != p.cell[0]
                half_size = (icon.get_width() if horizontal else icon.get_height()) / 2
                collision_progress = max(0.0, min(1.0, (self.tile / 2 - half_size) / self.tile))
                if p.entering:
                    opacity = min(
                        1.0,
                        (1.0 - p.entry_progress) / (1.0 - collision_progress),
                    )
                else:
                    opacity = min(
                        1.0,
                        p.entry_progress / (1.0 - collision_progress),
                    )
                draw_icon = icon.copy()
                draw_icon.set_alpha(round(255 * max(0.0, opacity)))
            screen.blit(draw_icon, draw_icon.get_rect(center=(round(pos.x), round(pos.y))))
 
