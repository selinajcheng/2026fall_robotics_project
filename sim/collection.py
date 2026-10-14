"""Trash detection, pickup counting, and bin unloading for the city demo.

Positions use the city's (column, row) cell coordinates, not pixels.
"""

from sim.world import Cell


class TrashCollector:
    def __init__(self, sensor_range: int = 2, capacity: int = 3) -> None:
        if sensor_range < 0:
            raise ValueError("sensor_range must be nonnegative")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.sensor_range = sensor_range
        self.capacity = capacity
        self.known_trash: set[Cell] = set()
        self.collected_count = 0
        self.current_load = 0
        self.unloads = 0

    @property
    def is_full(self) -> bool:
        return self.current_load >= self.capacity

    def detect(self, robot_cell: Cell, world_trash: set[Cell]) -> set[Cell]:
        """Discover trash within Manhattan sensor range; return new sightings."""
        sensed = {
            cell
            for cell in world_trash
            if abs(cell[0] - robot_cell[0]) + abs(cell[1] - robot_cell[1])
            <= self.sensor_range
        }
        new_sightings = sensed - self.known_trash
        self.known_trash.update(sensed)
        return new_sightings

    def collect(self, robot_cell: Cell, world_trash: set[Cell]) -> bool:
        """Collect one item at the robot's cell, if there is bin space."""
        if self.is_full or robot_cell not in world_trash:
            return False
        world_trash.remove(robot_cell)
        self.known_trash.discard(robot_cell)
        self.current_load += 1
        self.collected_count += 1
        return True

    def unload(self, robot_cell: Cell, station_cell: Cell) -> bool:
        """Empty the robot's onboard bin only while at the station."""
        if robot_cell != station_cell or self.current_load == 0:
            return False
        self.current_load = 0
        self.unloads += 1
        return True
