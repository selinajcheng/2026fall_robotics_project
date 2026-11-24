"""sim/interaction.py - pedestrians walk up to the robot and hand it their trash.

How a handoff works:
  1. The robot stops at a cell center and notices a pedestrian carrying trash nearby.
  2. That pedestrian walks to a cell next to the robot and stands there.
  3. They stay for HANDOFF_TIME seconds (the "handing it over" pause).
  4. The handoff finishes and main.py puts the trash into the robot's bin.
If the pedestrian never arrives (blocked, leaving for a building), the robot gives up
after WAIT_LIMIT seconds and ignores that pedestrian from then on.
"""

# ===== CONFIG =====
NOTICE_RANGE = 4      # robot notices carriers within this many cells (Manhattan distance)
WAIT_LIMIT = 10.0     # seconds the robot waits for a carrier to arrive before giving up
HANDOFF_TIME = 1.5    # seconds the pedestrian stands next to the robot handing over trash

NEIGHBORS = ((1, 0), (-1, 0), (0, 1), (0, -1))  # the 4 cells touching a cell


def _manhattan(a, b):
    # Distance counted in grid cells (no diagonals)
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ===== HANDOFF SYSTEM =====
class HandoffSystem:
    def __init__(self, world, crosswalk_cells=()):
        self.world = world                           # for is_walkable()
        self.crosswalk_cells = set(crosswalk_cells)  # robot never waits for handoffs on these
        self.state = "idle"                          # "idle", "waiting" (for donor), or "receiving"
        self.donor = None                            # the pedestrian handing over trash
        self.target = None                           # the cell next to the robot they walk to
        self.timer = 0.0                             # seconds spent in the current state
        self.refused = set()                         # ids of pedestrians the robot gave up on
        self.total_handoffs = 0                      # completed handoffs (for metrics)

    # --- is this pedestrian a valid donor right now? ---
    def _available(self, p):
        return (
            p.carrying_trash                                          # actually holding trash
            and not (p.inside or p.entering or p.exiting or p.returning)  # not fading / heading home
            and id(p) not in self.refused                             # robot hasn't given up on them
        )

    # --- stop the current handoff (optionally ignoring this pedestrian afterwards) ---
    def cancel(self, refuse=False):
        if self.donor is not None:
            self.donor.release()                     # let them go back to wandering
            if refuse:
                self.refused.add(id(self.donor))
        self.state, self.donor, self.target, self.timer = "idle", None, None, 0.0

    # --- look for a carrier near the robot and send them over ---
    def _start(self, robot_cell, peds):
        carriers = [
            p for p in peds
            if self._available(p) and _manhattan(p.cell, robot_cell) <= NOTICE_RANGE
        ]
        carriers.sort(key=lambda p: _manhattan(p.cell, robot_cell))  # nearest first

        # Cells touching the robot where a pedestrian could stand (never on a crosswalk)
        spots = [(robot_cell[0] + dx, robot_cell[1] + dy) for dx, dy in NEIGHBORS]
        spots = [s for s in spots if self.world.is_walkable(s) and s not in self.crosswalk_cells]

        for p in carriers:
            for spot in sorted(spots, key=lambda s: _manhattan(p.cell, s)):  # closest spot first
                if p.walk_to(spot):                  # a route exists: send them there
                    self.state, self.donor, self.target, self.timer = "waiting", p, spot, 0.0
                    return

    # --- per-frame update ---
    def update(self, dt, robot_cell, peds):
        """Call every frame while the robot is standing at a cell center.
        Returns (state, event). event is "accepted" on the frame a handoff completes."""
        # Forget "given up on" pedestrians who have since left the map
        self.refused &= {id(p) for p in peds}

        # ----- nobody yet: look for a carrier -----
        if self.state == "idle":
            self._start(robot_cell, peds)
            return self.state, None

        # ----- donor left the map or is heading home: cancel -----
        if self.donor not in peds or not self._available(self.donor):
            self.cancel()
            return "idle", None

        self.timer += dt
        donor = self.donor

        # ----- waiting for the donor to walk up -----
        if self.state == "waiting":
            arrived = donor.next_cell is None and _manhattan(donor.cell, robot_cell) == 1
            if arrived:
                self.state, self.timer = "receiving", 0.0
                donor.holding = HANDOFF_TIME         # donor stands still during the handoff
            elif self.timer > WAIT_LIMIT:
                self.cancel(refuse=True)             # took too long, stop waiting for them
                return "idle", None
            elif donor.goal != self.target:
                # Donor lost their route (e.g. got stuck and re-planned): send them again
                if not donor.walk_to(self.target):
                    self.cancel(refuse=True)
                    return "idle", None
            return self.state, None

        # ----- receiving: donor is standing next to the robot -----
        if self.timer >= HANDOFF_TIME:
            donor.carrying_trash = False             # they no longer have the trash
            donor.release()                          # free them to walk away
            self.total_handoffs += 1
            self.state, self.donor, self.target, self.timer = "idle", None, None, 0.0
            return "idle", "accepted"                # main.py now puts the trash in the bin
        return self.state, None