"""Checkpoint 2 synchronized road traffic; pure Python and ROS 2 portable.

There is ONE deterministic signal controller shared by cars and the robot.
Every pedestrian crossing is part of an exclusive vehicle conflict zone:
- cars request permission before their *front bumper* reaches a crosswalk;
- cars enter only with sufficient green time to clear the entire zone;
- the robot requests permission at the sidewalk curb and enters only with
  enough WALK time to finish and with no car still inside that zone.

This is a controlled grid demo, not general-purpose vehicle dynamics.
"""
from dataclasses import dataclass

# Deliberately fixed, reproducible signal timing.
PHASES = (("NS_GREEN", 9.0), ("ALL_RED_NS", 2.5),
          ("EW_GREEN", 9.0), ("ALL_RED_EW", 2.5))
CYCLE_DURATION = sum(duration for _, duration in PHASES)
STOP_GAP = 20.0  # front bumper stays behind the painted STOP bar (~11 px before crossing)
CAR_CLEARANCE = 0.35  # add on top of estimated crossing time
ROBOT_CLEARANCE = 0.75


def crossing_at(scene, cell):
    x, y = cell
    for crossing in scene.crosswalks:
        left, top, w, h = crossing.rect
        if left <= x < left + w and top <= y < top + h:
            return crossing
    return None


def crosswalk_axis(crossing):
    # White vertical bars mean a person crosses the north/south road E/W.
    return "NS" if crossing.stripe_direction == "vertical" else "EW"


def conflict_zones(scene, axis):
    """Intervals on one driving axis that cars must clear as a single unit.

    The two inner crosswalks AND the central intersection are one zone. Cars
    cannot stop in the middle of the intersection or on its far crosswalk.
    Edge crosswalks are separate, smaller zones.
    """
    tile = scene.world.tile_size
    intervals = []
    for cross in scene.crosswalks:
        if crosswalk_axis(cross) != axis:
            continue
        x, y, w, h = cross.rect
        intervals.append((x * tile, (x + w) * tile) if axis == "EW"
                         else (y * tile, (y + h) * tile))
    intervals.sort()
    merged = []
    # Adjacent central crosswalks are separated by the four-cell intersection.
    max_gap = 4 * tile + 0.001
    for start, end in intervals:
        if merged and start - merged[-1][1] <= max_gap:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return tuple(merged)


def signal_position(scene, crossing):
    """Place one C/W signal head per crosswalk, on an actual sidewalk.

    Positions deliberately alternate around the four city blocks so a
    north/south crossing head cannot stack on the adjacent east/west head.
    The function returns pixel centers, ready for the renderer. It derives
    dimensions from the scene rather than relying on screen screenshots.
    """
    tile = scene.world.tile_size
    l, top, w, h = crossing.rect
    world_columns = scene.world.columns
    world_rows = scene.world.rows
    if crosswalk_axis(crossing) == "NS":
        # Vertical-bar crosswalk spanning the north/south road.
        # Keep the head on its WEST sidewalk, away from the next corner's
        # east/west-road light. Choose the block side of the crosswalk.
        x = (l - 1) * tile
        if top == 0 or (0 < top < world_rows / 2):
            y = (top + h + 1) * tile if top == 0 else (top - 1) * tile
        else:
            y = (top - 1) * tile if top + h == world_rows else (top + h + 1) * tile
    else:
        # Horizontal-bar crosswalk spanning the east/west road.
        # Locate the head one cell NORTH of the crossing and just away from
        # the center vertical road, leaving distinct curb-side positions.
        y = (top - 1) * tile
        center = world_columns / 2
        x = (l - 1) * tile if l < center and l != 0 else (l + w + 1) * tile
        if l + w == world_columns:
            x = (l - 1) * tile
    return (round(x), round(y))


@dataclass
class Car:
    axis: str
    direction: int
    x: float
    y: float
    speed: float = 94.0
    color: tuple[int, int, int] = (56, 146, 219)
    length: float = 35.0
    width: float = 17.0

    @property
    def position(self):
        return self.x if self.axis == "EW" else self.y

    def advance(self, dt, green, remaining, world, zones, robot_zones=()):
        """Advance until next legal stop line, never parking on a crosswalk."""
        if dt < 0:
            raise ValueError("dt must be nonnegative")
        if self.axis not in ("NS", "EW") or self.direction not in (-1, 1):
            raise ValueError("invalid car axis/direction")
        if self.speed <= 0:
            raise ValueError("car speed must be positive")

        start = self.position
        signed_start = self.direction * start
        signed_goal = signed_start + self.speed * dt
        half = self.length / 2
        for low, high in zones:
            # Sort zones in direction of travel, but only consider zones ahead.
            entry = low if self.direction > 0 else -high
            exit_ = high if self.direction > 0 else -low
            stop = entry - half - STOP_GAP
            # The stop-line is BEFORE the crosswalk, not the intersection.
            # If a car is already between the stop line and the crossing,
            # never accelerate into a red light. Once its FRONT has entered
            # the protected crossing, it must clear the zone without parking.
            if signed_start > stop + 0.001:
                if signed_start + half <= entry + 0.001:
                    if not green or (low, high) in robot_zones:
                        signed_goal = signed_start
                        break
                continue
            if signed_goal < stop:
                continue
            safe_to_enter = bool(green) and (low, high) not in robot_zones
            # Check enough green remains to clear REAR bumper, + margin.
            clear_distance = (exit_ + half) - max(signed_start, stop)
            if remaining + 1e-9 < clear_distance / self.speed + CAR_CLEARANCE:
                safe_to_enter = False
            if not safe_to_enter:
                signed_goal = min(signed_goal, stop)
                break
        end = self.direction * signed_goal
        width, height = world.pixel_size
        world_extent = width if self.axis == "EW" else height
        if self.direction > 0 and end > world_extent + self.length:
            end = -self.length
        elif self.direction < 0 and end < -self.length:
            end = world_extent + self.length
        if self.axis == "EW":
            self.x = end
        else:
            self.y = end


class TrafficSystem:
    def __init__(self, scene):
        self.scene = scene
        self.elapsed = 0.0
        tile = scene.world.tile_size
        width, height = scene.world.pixel_size
        self.cars = [
            # US right-hand traffic: eastbound SOUTH/lower lane, westbound
            # NORTH/upper lane. This matches Selina's white stop bars.
            Car("EW", +1, 4 * tile, 12.7 * tile, 90, (58, 159, 221)),
            Car("EW", -1, width - 3 * tile, 11.3 * tile, 105, (237, 166, 61)),
            Car("NS", +1, 17.3 * tile, 3 * tile, 100, (184, 93, 215)),
            Car("NS", -1, 18.7 * tile, height - 3 * tile, 85, (238, 106, 98)),
        ]
        self.zones = {axis: conflict_zones(scene, axis) for axis in ("EW", "NS")}
        self.wait_events = 0

    @property
    def phase_and_remaining(self):
        point = round(round(self.elapsed, 9) % CYCLE_DURATION, 9)
        for name, duration in PHASES:
            if point < duration:
                return name, duration - point
            point -= duration
        return PHASES[-1][0], 0.0

    @property
    def phase(self):
        return self.phase_and_remaining[0]

    def vehicle_green(self, axis):
        if axis not in ("EW", "NS"):
            raise ValueError("axis must be EW or NS")
        return self.phase == f"{axis}_GREEN"

    def pedestrian_green(self, crossing):
        # Pedestrians cross a roadway ONLY while that roadway's cars are red,
        # with the opposite direction's cars green (after all-red clearance).
        return self.phase == ("EW_GREEN" if crosswalk_axis(crossing) == "NS"
                              else "NS_GREEN")

    def _car_occupies_zone(self, car, zone):
        if car.axis not in ("EW", "NS"):
            return False
        low, high = zone
        center = car.position
        return center + car.length / 2 > low and center - car.length / 2 < high

    def zone_for_crossing(self, crossing):
        axis = crosswalk_axis(crossing)
        tile = self.scene.world.tile_size
        a = crossing.rect[0] * tile if axis == "EW" else crossing.rect[1] * tile
        b = (crossing.rect[0] + crossing.rect[2]) * tile if axis == "EW" else (crossing.rect[1] + crossing.rect[3]) * tile
        for z in self.zones[axis]:
            if a >= z[0] and b <= z[1]:
                return z
        raise ValueError("crossing without conflict zone")

    def robot_may_enter(self, from_cell, to_cell, robot_speed=168.0):
        crossing = crossing_at(self.scene, to_cell)
        if crossing is None:
            return True
        if crossing_at(self.scene, from_cell) == crossing:
            return True  # Already committed: finish crossing without midroad stop.
        if not self.pedestrian_green(crossing):
            return False
        if robot_speed <= 0:
            raise ValueError("robot_speed must be positive")
        along = crossing.rect[2] if crossing.stripe_direction == "vertical" else crossing.rect[3]
        seconds = along * self.scene.world.tile_size / robot_speed + ROBOT_CLEARANCE
        if self.phase_and_remaining[1] < seconds:
            return False
        axis = crosswalk_axis(crossing)
        zone = self.zone_for_crossing(crossing)
        # Defensive interlock: even if a car enters unexpectedly, robot waits
        # rather than crossing in front of it.
        return not any(car.axis == axis and self._car_occupies_zone(car, zone)
                       for car in self.cars)

    def update(self, dt, robot_cell=None, walker_cells=()):
        if dt < 0:
            raise ValueError("dt must be nonnegative")

        # ----- split a long frame into small slices so cars can't skip a red light -----
        pending = dt                                   # time still left to simulate
        while pending > 1e-9:
            _, left_in_phase = self.phase_and_remaining  # seconds left in the current signal phase
            portion = min(pending, left_in_phase)      # never step past a signal change
            portion = min(portion, 0.05)               # never step more than 0.05 s at a time

            # ----- work out which crossing zones cars must NOT enter this slice -----
            axis_blocked = {"EW": set(), "NS": set()}
            held_cells = list(walker_cells)            # cells held by pedestrians
            if robot_cell is not None:
                held_cells.append(robot_cell)          # plus the robot's cell
            for held in held_cells:
                occupied = crossing_at(self.scene, held)  # None if it's plain sidewalk
                if occupied is not None:
                    # Block that crosswalk's whole zone for cars on that axis
                    axis_blocked[crosswalk_axis(occupied)].add(self.zone_for_crossing(occupied))

            # ----- move every car, respecting signals and blocked zones -----
            for car in self.cars:
                car.advance(portion, self.vehicle_green(car.axis),
                            self.phase_and_remaining[1], self.scene.world,
                            self.zones[car.axis], axis_blocked[car.axis])

            # ----- advance the clock (these two lines must be at THIS indent level) -----
            self.elapsed += portion
            pending -= portion