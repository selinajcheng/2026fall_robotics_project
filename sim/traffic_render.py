"""Small, consistent Pygame signal heads at the curbs, never in the roadway.

C = car signal for traffic on the crossing's road; W = walk signal for robot.
Each pair reads the same shared TrafficSystem phase, not separate clocks.
"""
import pygame
from sim.traffic import crosswalk_axis, signal_position

RED = (231, 70, 64)
GREEN = (61, 218, 116)
DIM = (33, 39, 46)


def _head(screen, x, y, vehicle_allowed, walk_allowed):
    width, height = screen.get_size()
    x = max(28, min(width - 28, int(x)))
    y = max(22, min(height - 22, int(y)))
    # Two small heads together: car facing roadway + pedestrian WALK.
    pygame.draw.rect(screen, (19, 23, 31), (x-21, y-12, 42, 24), border_radius=6)
    pygame.draw.rect(screen, (210, 218, 225), (x-21, y-12, 42, 24), 1, border_radius=6)
    pygame.draw.circle(screen, GREEN if vehicle_allowed else RED, (x-12, y), 6)
    pygame.draw.circle(screen, GREEN if walk_allowed else RED, (x+12, y), 6)
    f = pygame.font.Font(None, 14)
    screen.blit(f.render('C', True, (255,255,255)), (x-16,y+9))
    screen.blit(f.render('W', True, (255,255,255)), (x+8,y+9))


def draw_traffic(screen, scene, traffic):
    # Each crosswalk gets one pair; none overlaps a neighboring signal.
    for crossing in scene.crosswalks:
        axis = crosswalk_axis(crossing)
        x, y = signal_position(scene, crossing)
        _head(screen, x, y, traffic.vehicle_green(axis), traffic.pedestrian_green(crossing))

    # Car bodies (actual positions remain in sim/traffic.py).
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
