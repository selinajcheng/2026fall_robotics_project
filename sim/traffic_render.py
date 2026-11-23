"""Compact traffic lights and walking-person signals for Checkpoint 3.

The same walking-person pictogram is WHITE when crossing is permitted and
RED when pedestrians/robot must wait. Both heads use the shared
TrafficSystem clock and the original crosswalk curb positions.

This module only renders signals and existing cars; the traffic controller
remains authoritative for stopping, clearing, and robot crossing permission.
"""
import pygame

from sim.traffic import crosswalk_axis, signal_position

# Colors are chosen to remain legible against the team's pavement and roads.
RED = (233, 68, 62)
YELLOW = (247, 195, 59)
GREEN = (68, 216, 112)
WHITE = (250, 250, 248)
DIM = (48, 55, 62)
HOUSING = (17, 22, 29)
BORDER = (171, 180, 190)

# One small head per crosswalk; total width matches the original 42px box.
CAR_WIDTH = 16
CAR_HEIGHT = 42
GAP = 4
PED_WIDTH = 22
PED_HEIGHT = 30
SIGNAL_WIDTH = CAR_WIDTH + GAP + PED_WIDTH  # 42px
SIGNAL_HEIGHT = CAR_HEIGHT                    # 42px


def signal_rect(x, y):
    """Actual bounding box centered on the team's existing curb signal anchor."""
    return pygame.Rect(round(x - SIGNAL_WIDTH / 2),
                       round(y - SIGNAL_HEIGHT / 2),
                       SIGNAL_WIDTH, SIGNAL_HEIGHT)


def _draw_car_light(screen, x, y, state):
    """A vertical, three-bulb signal: only the selected light is bright."""
    box = pygame.Rect(x, y, CAR_WIDTH, CAR_HEIGHT)
    pygame.draw.rect(screen, HOUSING, box, border_radius=4)
    pygame.draw.rect(screen, BORDER, box, width=1, border_radius=4)

    for lamp, color, cy in (
        ("RED", RED, box.top + 9),
        ("YELLOW", YELLOW, box.top + 21),
        ("GREEN", GREEN, box.top + 33),
    ):
        center = (box.centerx, cy)
        pygame.draw.circle(screen, color if state == lamp else DIM, center, 4)


def _draw_walking_person(screen, x, y, color):
    """Draw one consistent walking pictogram; its color conveys permission."""
    # Head, torso, arms, and split legs. This fits in a 22x30-pixel sign.
    pygame.draw.circle(screen, color, (x, y - 8), 3)
    pygame.draw.line(screen, color, (x, y - 4), (x, y + 2), 3)
    pygame.draw.line(screen, color, (x, y - 2), (x - 6, y + 1), 2)
    pygame.draw.line(screen, color, (x, y - 2), (x + 6, y - 1), 2)
    pygame.draw.line(screen, color, (x, y + 2), (x - 5, y + 10), 3)
    pygame.draw.line(screen, color, (x, y + 2), (x + 6, y + 8), 3)


def _draw_pedestrian_light(screen, x, y, state):
    """White walker = WALK; red walker = DON'T WALK / wait."""
    box = pygame.Rect(x, y, PED_WIDTH, PED_HEIGHT)
    pygame.draw.rect(screen, HOUSING, box, border_radius=4)
    pygame.draw.rect(screen, BORDER, box, width=1, border_radius=4)
    icon_color = WHITE if state == "WALK" else RED
    _draw_walking_person(screen, box.centerx, box.centery, icon_color)


def _head(screen, x, y, vehicle_state, pedestrian_state):
    """Use the existing curb anchor, with no extra displacement or large signs."""
    rect = signal_rect(x, y)
    _draw_car_light(screen, rect.left, rect.top, vehicle_state)
    pedestrian_top = rect.top + (SIGNAL_HEIGHT - PED_HEIGHT) // 2
    _draw_pedestrian_light(screen,
                           rect.left + CAR_WIDTH + GAP,
                           pedestrian_top,
                           pedestrian_state)


def draw_traffic(screen, scene, traffic):
    """Draw signals and the team's original cars, using one shared controller."""
    for crossing in scene.crosswalks:
        axis = crosswalk_axis(crossing)
        x, y = signal_position(scene, crossing)
        _head(screen, x, y,
              traffic.vehicle_signal(axis),
              traffic.pedestrian_signal(crossing))

    # Preserve the existing Checkpoint 2 car sprites and lane-direction cues.
    for car in traffic.cars:
        if car.axis == 'EW':
            rect = pygame.Rect(round(car.x-car.length/2),round(car.y-car.width/2),
                               round(car.length),round(car.width))
        else:
            rect = pygame.Rect(round(car.x-car.width/2),round(car.y-car.length/2),
                               round(car.width),round(car.length))
        pygame.draw.rect(screen, (19, 22, 28), rect.inflate(4, 4), border_radius=5)
        pygame.draw.rect(screen, car.color, rect, border_radius=5)
        if car.axis == 'EW':
            at = rect.right-9 if car.direction>0 else rect.left+4
            windshield = pygame.Rect(at,rect.top+3,5,max(3,rect.height-6))
        else:
            at = rect.bottom-9 if car.direction>0 else rect.top+4
            windshield = pygame.Rect(rect.left+3,at,max(3,rect.width-6),5)
        pygame.draw.rect(screen,(207,239,249),windshield,border_radius=2)
