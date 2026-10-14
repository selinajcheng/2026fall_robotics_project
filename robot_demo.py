import math
import pygame
from robot import Robot
from navigation import find_path

pygame.init()

WIDTH = 1000
HEIGHT = 650

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Autonomous Garbage Collection Robot")

SIDEWALK = (210, 210, 210)
GRID = (185, 185, 185)
OBSTACLE = (110, 110, 110)
PATH_COLOR = (30, 170, 90)
GOAL_COLOR = (230, 70, 70)
PEDESTRIAN_COLOR = (235, 155, 45)
WHITE = (255, 255, 255)
TEXT_COLOR = (40, 40, 40)

robot = Robot(100, 325)
robot.speed = 150

obstacles = [
    pygame.Rect(300, 100, 75, 280),
    pygame.Rect(550, 330, 100, 180),
    pygame.Rect(750, 80, 75, 220)
]

pedestrians = [
    {
        "x": 410.0,
        "y": 410.0,
        "speed": 65,
        "direction": 1,
        "minimum": 390,
        "maximum": 530,
        "radius": 15,
        "yielding": False,
        "yield_target": None,
        "crossing_side": 0
    },
    {
        "x": 850.0,
        "y": 550.0,
        "speed": 90,
        "direction": -1,
        "minimum": 660,
        "maximum": 960,
        "radius": 15,
        "yielding": False,
        "yield_target": None,
        "crossing_side": 0
    }
]

STATIC_MARGIN = 8
PEDESTRIAN_MARGIN = 18
MOVEMENT_STEP = 2
YIELD_DISTANCE = 125
CLEARANCE_DISTANCE = 65

font = pygame.font.SysFont("Arial", 22)

goal = None
status = "READY"
clock = pygame.time.Clock()
running = True


def distance_to_person(x, y, person):
    return math.hypot(
        x - person["x"],
        y - person["y"]
    )


def minimum_distance(person):
    return (
        robot.radius
        + person["radius"]
        + PEDESTRIAN_MARGIN
    )


def static_position_safe(x, y):
    margin = robot.radius + STATIC_MARGIN

    if not (
        margin <= x <= WIDTH - margin
        and margin <= y <= HEIGHT - margin
    ):
        return False

    for obstacle in obstacles:
        closest_x = max(obstacle.left, min(x, obstacle.right))
        closest_y = max(obstacle.top, min(y, obstacle.bottom))

        if math.hypot(
            x - closest_x,
            y - closest_y
        ) <= margin:
            return False

    return True


def pedestrian_position_safe(x, y):
    return all(
        distance_to_person(x, y, person)
        >= minimum_distance(person)
        for person in pedestrians
    )


def position_safe(x, y):
    return (
        static_position_safe(x, y)
        and pedestrian_position_safe(x, y)
    )


def calculate_route(destination):
    return find_path(
        (robot.x, robot.y),
        destination,
        obstacles,
        WIDTH,
        HEIGHT,
        robot.radius + STATIC_MARGIN
    )


def update_pedestrians(dt):
    for person in pedestrians:
        if goal is not None and not person["yielding"]:
            distance = distance_to_person(
                robot.x,
                robot.y,
                person
            )

            if distance < YIELD_DISTANCE and robot.path:
                person["yielding"] = True

                person["crossing_side"] = (
                    1 if robot.y >= person["y"] else -1
                )

                if person["x"] >= robot.x:
                    person["yield_target"] = person["maximum"]
                else:
                    person["yield_target"] = person["minimum"]

        if person["yielding"]:
            crossed = (
                (robot.y - person["y"])
                * person["crossing_side"]
                < -CLEARANCE_DISTANCE
            )

            if goal is None or crossed:
                person["yielding"] = False
                person["yield_target"] = None

            else:
                target = person["yield_target"]
                difference = target - person["x"]
                movement = person["speed"] * dt

                if abs(difference) <= movement:
                    person["x"] = target
                else:
                    person["x"] += math.copysign(
                        movement,
                        difference
                    )

                continue

        old_x = person["x"]

        new_x = (
            old_x
            + person["speed"] * person["direction"] * dt
        )

        if new_x >= person["maximum"]:
            new_x = person["maximum"]
            person["direction"] = -1

        elif new_x <= person["minimum"]:
            new_x = person["minimum"]
            person["direction"] = 1

        steps = max(
            1,
            math.ceil(abs(new_x - old_x) / MOVEMENT_STEP)
        )

        safe_x = old_x

        for step in range(1, steps + 1):
            candidate_x = old_x + (
                new_x - old_x
            ) * step / steps

            if distance_to_person(
                robot.x,
                robot.y,
                {
                    "x": candidate_x,
                    "y": person["y"]
                }
            ) < minimum_distance(person):
                break

            safe_x = candidate_x

        person["x"] = safe_x

        if abs(safe_x - new_x) > 0.001:
            if person["x"] >= robot.x:
                person["direction"] = 1
            else:
                person["direction"] = -1


def update_robot(keys, dt):
    global status

    steps = max(
        1,
        math.ceil(robot.speed * dt / MOVEMENT_STEP)
    )

    step_dt = dt / steps

    for _ in range(steps):
        old_x = robot.x
        old_y = robot.y
        old_path = robot.path.copy()

        robot.move(keys, step_dt, WIDTH, HEIGHT)

        if not static_position_safe(robot.x, robot.y):
            robot.x = old_x
            robot.y = old_y
            robot.set_path(old_path)
            status = "BLOCKED"
            return

        if not pedestrian_position_safe(robot.x, robot.y):
            robot.x = old_x
            robot.y = old_y
            robot.set_path(old_path)
            status = "WAITING FOR PEDESTRIAN"
            return

    if goal is not None and robot.path:
        status = "MOVING"


while running:
    dt = min(clock.tick(60) / 1000.0, 0.05)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            destination = event.pos
            new_path = calculate_route(destination)

            if new_path:
                goal = destination
                robot.set_path(new_path)
                status = "MOVING"
            else:
                goal = None
                robot.set_path([])
                status = "NO ROUTE AVAILABLE"

            for person in pedestrians:
                person["yielding"] = False
                person["yield_target"] = None

    keys = pygame.key.get_pressed()

    manual_keys = (
        pygame.K_LEFT,
        pygame.K_RIGHT,
        pygame.K_UP,
        pygame.K_DOWN,
        pygame.K_w,
        pygame.K_a,
        pygame.K_s,
        pygame.K_d
    )

    manual_active = any(
        keys[key] for key in manual_keys
    )

    if manual_active:
        goal = None
        robot.set_path([])
        status = "MANUAL CONTROL"

    update_pedestrians(dt)

    if goal is not None or manual_active:
        update_robot(keys, dt)

    if goal is not None and not robot.path:
        goal = None
        status = "DESTINATION REACHED"

    screen.fill(SIDEWALK)

    for x in range(0, WIDTH, 50):
        pygame.draw.line(
            screen,
            GRID,
            (x, 0),
            (x, HEIGHT)
        )

    for y in range(0, HEIGHT, 50):
        pygame.draw.line(
            screen,
            GRID,
            (0, y),
            (WIDTH, y)
        )

    for obstacle in obstacles:
        pygame.draw.rect(
            screen,
            OBSTACLE,
            obstacle,
            border_radius=5
        )

    if robot.path:
        points = [
            (round(robot.x), round(robot.y))
        ]

        points.extend(
            (round(x), round(y))
            for x, y in robot.path
        )

        if len(points) >= 2:
            pygame.draw.lines(
                screen,
                PATH_COLOR,
                False,
                points,
                4
            )

    if goal is not None:
        pygame.draw.circle(
            screen,
            GOAL_COLOR,
            goal,
            9
        )

    for person in pedestrians:
        position = (
            round(person["x"]),
            round(person["y"])
        )

        pygame.draw.circle(
            screen,
            PEDESTRIAN_COLOR,
            position,
            person["radius"]
        )

        pygame.draw.circle(
            screen,
            WHITE,
            position,
            5
        )

    robot.draw(screen)

    status_text = font.render(
        f"Status: {status}",
        True,
        TEXT_COLOR
    )

    status_background = pygame.Rect(
        10,
        10,
        status_text.get_width() + 20,
        40
    )

    pygame.draw.rect(
        screen,
        WHITE,
        status_background,
        border_radius=5
    )

    screen.blit(status_text, (20, 18))

    pygame.display.flip()

pygame.quit()
