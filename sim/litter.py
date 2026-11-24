"""sim/litter.py - pedestrians drop trash on sidewalks for the robot to find.

Each time a visible pedestrian arrives at a new cell, there is a small chance
they drop a piece of trash there. Dropped trash goes straight into the sim's
shared trash set, so the robot senses and collects it like any other trash.
"""

import random  # seeded random generator so the same seed gives the same littering

import pygame  # used to draw the little "drop" ring animation

# ===== CONFIG =====
DROP_CHANCE = 0.015        # chance per cell walked that a pedestrian drops trash (1.5%)
DROP_COOLDOWN = 20.0       # seconds before the SAME pedestrian can drop again
MAX_ACTIVE_LITTER = 8      # most dropped pieces allowed lying on the map at once
POP_TIME = 0.8             # seconds the "something was dropped" ring animation lasts


# ===== LITTER SYSTEM =====
class LitterSystem:
    def __init__(self, trash, reachable, keep_clear, seed=0):
        self.trash = trash                # the SAME set the robot/collector uses (we add cells to it)
        self.reachable = reachable        # cells the robot can actually get to
        self.keep_clear = keep_clear      # cells that must never get litter (station, start, crosswalks)
        self.rng = random.Random(seed)    # own generator so littering is repeatable per seed

        self.dropped_cells = set()        # dropped pieces still lying on the ground
        self.total_dropped = 0            # how many pieces pedestrians have dropped in total
        self.last_cell = {}               # pedestrian key -> the cell they were on last frame
        self.cooldowns = {}               # pedestrian key -> seconds until they may drop again
        self.pops = []                    # [cell, age] pairs for the drop animation

    # --- can litter go on this cell right now? ---
    def _can_drop_at(self, cell, robot_cells):
        return (
            cell in self.reachable            # robot can get there
            and cell not in self.keep_clear   # not the station, start, or a crosswalk
            and cell not in self.trash        # no stacking two pieces on one cell
            and cell not in robot_cells       # not on top of the robot
        )

    # --- per-frame update ---
    def update(self, dt, walkers, robot_cells):
        """walkers = list of (key, cell, visible) for every pedestrian.
        robot_cells = cells the robot is in / driving into.
        Returns the list of cells where trash was dropped this frame."""
        new_cells = []

        # Age the drop animations and remove finished ones
        self.pops = [[c, age + dt] for c, age in self.pops if age + dt < POP_TIME]

        # Forget dropped pieces the robot has already picked up
        self.dropped_cells &= self.trash

        for key, cell, visible in walkers:
            # Tick this pedestrian's cooldown down toward zero
            self.cooldowns[key] = max(0.0, self.cooldowns.get(key, 0.0) - dt)

            # First time we see this pedestrian: just remember where they are
            if key not in self.last_cell:
                self.last_cell[key] = cell
                continue

            arrived = self.last_cell[key] != cell   # True only on the frame they reach a NEW cell
            self.last_cell[key] = cell

            if not (arrived and visible):
                continue                            # only roll the dice on new cells, and only when seen
            if self.cooldowns[key] > 0:
                continue                            # dropped something recently
            if len(self.dropped_cells) >= MAX_ACTIVE_LITTER:
                continue                            # too much litter already on the map
            if self.rng.random() >= DROP_CHANCE:
                continue                            # lucky: no drop this time
            if not self._can_drop_at(cell, robot_cells):
                continue                            # bad spot for litter

            # Drop it!
            self.trash.add(cell)                    # robot can now sense and collect it
            self.dropped_cells.add(cell)
            self.total_dropped += 1
            self.cooldowns[key] = DROP_COOLDOWN
            self.pops.append([cell, 0.0])           # start the ring animation
            new_cells.append(cell)

            #forget pedestrians who have left the map (they went in the buildings)
            alive = {key for key, _, _ in walkers}
            for table in (self.last_cell, self.cooldowns):
                for key in list(table):
                    if key not in alive:
                        del table[key]

        return new_cells

    # --- drawing: an expanding ring where trash was just dropped ---
    def draw(self, screen, tile):
        for cell, age in self.pops:
            fraction = age / POP_TIME                       # 0.0 at the drop, 1.0 when finished
            radius = round(8 + 14 * fraction)               # ring grows outward
            width = max(1, round(3 * (1 - fraction)))       # ring thins as it grows
            center = (round((cell[0] + 0.5) * tile), round((cell[1] + 0.5) * tile))
            pygame.draw.circle(screen, (255, 210, 90), center, radius, width)