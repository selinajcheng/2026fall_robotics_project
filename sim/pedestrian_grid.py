""" CHECK POINT 2: Pedestrian Grid

Pedestrians walk in the sidewalk/crosswalk cells. The robot will treat the cells they occupy as temporarily blocked and yields until they pass. 

"""
import random
import pygame
from sim.grid_navigation import find_grid_path

#CONFIG
STEP_TIME = 0.5 #seconds it takes to walk one cell
INSIDE_RANGE = (3.0, 8.0) #min/max sec a pedestrian stays inside a building
WANDER_CHANCE = 0.3 # 30% of trips go to a random sidewalk cell insteas of a door
STUCK_TIMEOUT = 2.0 #seconds of being blocked giving up and picking a new destination

# ===== SINGLE PEDESTRIAN =====
class Pedestrian:
    def __init__(self, world, doors, cells, static_blocked, rng, start_cell, start_inside):
        self.world = world                  # the city world (needed by find_grid_path)
        self.doors = doors                  # list of cells where pedestrians enter/exit buildings
        self.cells = cells                  # list of cells usable as random "stroll" destinations
        self.static_blocked = static_blocked  # permanently blocked cells (never walk through these)
        self.rng = rng                      # shared random generator (seeded so runs repeat)
 
        self.cell = start_cell              # the cell the pedestrian is standing on / just left
        self.next_cell = None               # the cell being walked into (None = standing still)
        self.progress = 0.0                 # how far along the step is: 0.0 = start, 1.0 = arrived
        self.path = []                      # cells still to walk through, in order
        self.goal = None                    # final destination cell of the current trip
        self.goal_is_door = False           # True if the goal is a building door (enter on arrival)
 
        self.inside = start_inside          # True = currently inside a building (hidden, no collision)
        # If starting inside, pick how long to wait before coming out; otherwise no timer needed
        self.timer = rng.uniform(*INSIDE_RANGE) if start_inside else 0.0
        self.blocked_time = 0.0             # how long someone has been in the way of our next step
 
    # --- picking where to go next ---
    def _choose_goal(self):
        for _ in range(5):                  # try up to 5 times to find a reachable destination
            if self.rng.random() < WANDER_CHANCE:
                # Stroll: pick any random sidewalk cell (not a door, so no entering a building)
                goal, is_door = self.rng.choice(self.cells), False
            else:
                # Errand: pick a random building door (will go inside on arrival)
                goal, is_door = self.rng.choice(self.doors), True
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
 
    # --- per-frame update ---
    def update(self, dt, blocked, may_step=None):
        """dt = seconds since last frame.
        blocked = cells held by the robot and other pedestrians (not our own).
        may_step = optional function(cell, next_cell) -> bool, used for crosswalk signals."""
 
        # ----- inside a building: count down, then come back out -----
        if self.inside:
            self.timer -= dt                # tick the wait-time down
            # Only come out if the timer is done AND nobody is standing on the door cell
            if self.timer <= 0 and self.cell not in blocked:
                self.inside = False         # reappear on the sidewalk at the door
                self._drop_goal()           # forget the old trip so a new one gets chosen
            return                          # nothing else to do this frame
 
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
            self.inside = True              # hide and stop colliding
            self.timer = self.rng.uniform(*INSIDE_RANGE)  # random time to stay inside
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
        if nxt in blocked:                  # robot or another pedestrian is in that cell (or entering it)
            self.blocked_time += dt         # count how long we've been waiting on them
            if self.blocked_time > STUCK_TIMEOUT:
                self.blocked_time = 0.0
                self._drop_goal()           # give up this trip so a new route gets picked
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
        if self.next_cell is None:
            return a                        # standing still: draw at the cell center
        # Pixel center of the cell we're walking into
        b = pygame.Vector2((self.next_cell[0] + 0.5) * tile, (self.next_cell[1] + 0.5) * tile)
        return a.lerp(b, self.progress)     # slide from a to b by 'progress' (0..1)
 
 
# ===== MANAGER (what main.py talks to) =====
class PedestrianManager:
    def __init__(self, world, cells, static_blocked, doors=None, count=6, seed=7, keep_clear=()):
        rng = random.Random(seed)           # one seeded generator so every run looks the same
        self.tile = world.tile_size         # pixels per grid cell (for drawing)
 
        # Cells pedestrians may use as doors / stroll targets: walkable, not blocked, not keep_clear
        candidates = sorted(c for c in cells if c not in static_blocked and c not in keep_clear)
 
        # No doors given? Auto-pick some random cells so it works out of the box.
        if not doors:
            doors = rng.sample(candidates, min(6, len(candidates)))
        self.doors = list(doors)
 
        self.peds = []                      # all pedestrians in the sim
        for i in range(count):
            door = self.doors[i % len(self.doors)]  # spread pedestrians across the doors
            # Every other pedestrian starts inside a building, so people trickle out over time.
            # Extra pedestrians beyond the door count also start inside to avoid overlapping.
            start_inside = (i % 2 == 0) or (i >= len(self.doors))
            self.peds.append(
                Pedestrian(world, self.doors, candidates, static_blocked, rng, door, start_inside)
            )
 
    def update(self, dt, robot_cells, may_step=None):
        for p in self.peds:
            blocked = set(robot_cells)      # start with the cells the robot holds
            for other in self.peds:
                if other is not p:
                    blocked |= other.occupied_cells()  # add every OTHER pedestrian's cells
            p.update(dt, blocked, may_step)
 
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
            screen.blit(icon, icon.get_rect(center=(round(pos.x), round(pos.y))))
 