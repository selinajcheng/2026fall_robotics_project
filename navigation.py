import heapq
import math


CELL_SIZE = 25


def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path(start, goal, obstacles, width, height, radius=20):
    cols = width // CELL_SIZE
    rows = height // CELL_SIZE

    def to_cell(position):
        return (
            int(position[0] // CELL_SIZE),
            int(position[1] // CELL_SIZE)
        )

    def to_position(cell):
        return (
            cell[0] * CELL_SIZE + CELL_SIZE / 2,
            cell[1] * CELL_SIZE + CELL_SIZE / 2
        )

    def valid(cell):
        x, y = cell

        if not (0 <= x < cols and 0 <= y < rows):
            return False

        px, py = to_position(cell)

        if not (
            radius <= px <= width - radius
            and radius <= py <= height - radius
        ):
            return False

        for obstacle in obstacles:
            closest_x = max(obstacle.left, min(px, obstacle.right))
            closest_y = max(obstacle.top, min(py, obstacle.bottom))

            if math.hypot(px - closest_x, py - closest_y) <= radius:
                return False

        return True

    start_cell = to_cell(start)
    goal_cell = to_cell(goal)

    if not valid(start_cell) or not valid(goal_cell):
        return []

    open_set = [(heuristic(start_cell, goal_cell), start_cell)]
    came_from = {}
    g_score = {start_cell: 0}
    closed = set()

    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    while open_set:
        _, current = heapq.heappop(open_set)

        if current in closed:
            continue

        if current == goal_cell:
            path = [current]

            while current in came_from:
                current = came_from[current]
                path.append(current)

            path.reverse()
            return [to_position(cell) for cell in path]

        closed.add(current)

        for dx, dy in directions:
            neighbor = (current[0] + dx, current[1] + dy)

            if not valid(neighbor) or neighbor in closed:
                continue

            tentative_g = g_score[current] + 1

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g

                f_score = tentative_g + heuristic(neighbor, goal_cell)

                heapq.heappush(open_set, (f_score, neighbor))

    return []
