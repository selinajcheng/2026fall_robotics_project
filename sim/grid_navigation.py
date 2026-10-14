"""A* adapter for Mahbub's robot on Selina's 28px sidewalk grid.

Mahbub's original navigation.py uses a 25px open-area grid. This adapter
keeps the A* algorithm, but obtains legal steps from Selina's GridWorld.
"""

from collections import deque
from heapq import heappop, heappush

from sim.world import Cell, GridWorld


def legal_neighbors(world: GridWorld, cell: Cell, blocked: set[Cell]):
    return (next_cell for next_cell in world.neighbors(cell) if next_cell not in blocked)


def nearest_target(
    world: GridWorld,
    start: Cell,
    targets: set[Cell],
    blocked: set[Cell],
) -> Cell | None:
    """Find a nearest reachable target by shortest path length (BFS)."""
    if not world.is_walkable(start) or start in blocked:
        return None
    pending = deque([start])
    seen = {start}
    while pending:
        current = pending.popleft()
        if current in targets:
            return current
        for neighbor in legal_neighbors(world, current, blocked):
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    return None


def reachable_cells(world: GridWorld, start: Cell, blocked: set[Cell]) -> set[Cell]:
    """Get all walkable cells reachable from start without crossing blockers."""
    if not world.is_walkable(start) or start in blocked:
        return set()
    seen = {start}
    pending = deque([start])
    while pending:
        current = pending.popleft()
        for neighbor in legal_neighbors(world, current, blocked):
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    return seen


def find_grid_path(
    world: GridWorld,
    start: Cell,
    goal: Cell,
    blocked: set[Cell],
) -> list[Cell]:
    """Return an A* path through legal cells, including start and goal."""
    if (
        not world.is_walkable(start)
        or not world.is_walkable(goal)
        or start in blocked
        or goal in blocked
    ):
        return []

    def distance(a: Cell, b: Cell) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    queue = [(distance(start, goal), 0, start)]
    came_from: dict[Cell, Cell] = {}
    best_cost = {start: 0}

    while queue:
        _, cost, current = heappop(queue)
        if cost != best_cost.get(current):
            continue  # skip outdated queue entries
        if current == goal:
            result = [current]
            while current in came_from:
                current = came_from[current]
                result.append(current)
            return list(reversed(result))
        for neighbor in legal_neighbors(world, current, blocked):
            new_cost = cost + 1
            if new_cost < best_cost.get(neighbor, float('inf')):
                best_cost[neighbor] = new_cost
                came_from[neighbor] = current
                priority = new_cost + distance(neighbor, goal)
                heappush(queue, (priority, new_cost, neighbor))
    return []
