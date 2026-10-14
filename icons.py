import pygame
import math

def pedestrian_icon(size = 48, color = (70,130,220)):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    def P(x, y):
        return (int(x * size), int(y * size))

    w = max(2, size // 9)

    # head
    pygame.draw.circle(s, color, P(0.5, 0.14), int(size * 0.12))
    # torso
    pygame.draw.rect(s, color, pygame.Rect(P(0.36, 0.28), (int(size * 0.28), int(size * 0.30))),
                     border_radius=int(size * 0.06))
    # arms
    pygame.draw.line(s, color, P(0.37, 0.32), P(0.20, 0.55), w)
    pygame.draw.line(s, color, P(0.63, 0.32), P(0.80, 0.55), w)
    # legs
    pygame.draw.line(s, color, P(0.44, 0.56), P(0.38, 0.95), w + 1)
    pygame.draw.line(s, color, P(0.56, 0.56), P(0.62, 0.95), w + 1)
    return s 

def trash_icon(size = 48, color = (170, 150, 120)):
    """"Crumpled paper ball icon"""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size /2
    radii = [0.40, 0.27, 0.38, 0.24, 0.41, 0.30, 0.37,
             0.25, 0.40, 0.28, 0.36, 0.26, 0.41, 0.29]
    n = len(radii)
    pts = []
    for i, r in enumerate(radii):
        angle = i * (2 * math.pi / n)
        pts.append((int(c + r * size * math.cos(angle)),
                    int(c + r * size * math.sin(angle))))

    w = max(1, size // 24)
    light = tuple(min(255, v + 35) for v in color)
    mid = tuple(max(0, v - 25) for v in color)
    dark = tuple(max(0, v - 70) for v in color)
    center = (int(c - size * 0.03), int(c + size * 0.02))

    # base shape, then shaded facets to look folded
    pygame.draw.polygon(s, color, pts)
    for i in range(n):
        shade = light if i % 3 == 0 else mid if i % 3 == 1 else None
        if shade:
            pygame.draw.polygon(s, shade, [center, pts[i], pts[(i + 1) % n]])

    # crease lines running in different directions
    for i in (1, 4, 7, 10, 12):
        pygame.draw.line(s, dark, center, pts[i], w)
    pygame.draw.line(s, dark, pts[2], pts[9], w)
    pygame.draw.line(s, dark, pts[5], pts[12], w)

    # outline
    pygame.draw.polygon(s, dark, pts, w)
    return s

def trash_can_icon(size=48, color=(110, 120, 135)):
    s = pygame.Surface((size, size), pygame.SRCALPHA)

    def R(x, y, w, h):
        return pygame.Rect(int(x * size), int(y * size), int(w * size), int(h * size))

    dark = tuple(max(0, v - 50) for v in color)
    pygame.draw.rect(s, color, R(0.38, 0.06, 0.24, 0.10), border_radius=2)   # handle
    pygame.draw.rect(s, color, R(0.14, 0.15, 0.72, 0.09), border_radius=2)   # lid
    body = [(0.22 * size, 0.28 * size), (0.78 * size, 0.28 * size),
            (0.72 * size, 0.94 * size), (0.28 * size, 0.94 * size)]
    pygame.draw.polygon(s, color, body)
    for x in (0.40, 0.50, 0.60):                                              # ridges
        pygame.draw.line(s, dark, (int(x * size), int(0.36 * size)),
                         (int(x * size), int(0.84 * size)), max(1, size // 24))
    return s

def robot_icon(size=48, color=(90, 190, 130)):
    s = pygame.Surface((size, size), pygame.SRCALPHA)

    def R(x, y, w, h):
        return pygame.Rect(int(x * size), int(y * size), int(w * size), int(h * size))

    dark = tuple(max(0, v - 70) for v in color)
    lw = max(1, size // 24)

    # antenna
    pygame.draw.line(s, dark, (int(size * 0.5), int(size * 0.04)), (int(size * 0.5), int(size * 0.16)), lw + 1)
    pygame.draw.circle(s, (230, 70, 70), (int(size * 0.5), int(size * 0.05)), max(2, size // 16))
    # head
    pygame.draw.rect(s, color, R(0.24, 0.16, 0.52, 0.30), border_radius=int(size * 0.07))
    pygame.draw.rect(s, dark, R(0.24, 0.16, 0.52, 0.30), lw, border_radius=int(size * 0.07))
    # eyes
    pygame.draw.circle(s, (255, 255, 255), (int(size * 0.39), int(size * 0.31)), max(2, size // 14))
    pygame.draw.circle(s, (255, 255, 255), (int(size * 0.61), int(size * 0.31)), max(2, size // 14))
    pygame.draw.circle(s, dark, (int(size * 0.39), int(size * 0.31)), max(1, size // 28))
    pygame.draw.circle(s, dark, (int(size * 0.61), int(size * 0.31)), max(1, size // 28))
    # body
    pygame.draw.rect(s, color, R(0.28, 0.50, 0.44, 0.30), border_radius=int(size * 0.05))
    pygame.draw.rect(s, dark, R(0.28, 0.50, 0.44, 0.30), lw, border_radius=int(size * 0.05))
    pygame.draw.circle(s, dark, (int(size * 0.5), int(size * 0.65)), max(2, size // 16))
    # arms
    pygame.draw.line(s, dark, (int(size * 0.28), int(size * 0.55)), (int(size * 0.12), int(size * 0.72)), lw + 2)
    pygame.draw.line(s, dark, (int(size * 0.72), int(size * 0.55)), (int(size * 0.88), int(size * 0.72)), lw + 2)
    # wheels
    pygame.draw.circle(s, dark, (int(size * 0.36), int(size * 0.90)), int(size * 0.08))
    pygame.draw.circle(s, dark, (int(size * 0.64), int(size * 0.90)), int(size * 0.08))
    return s

def obstacle_icon(size=48, color=(235, 120, 40)):
    """Traffic cone"""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    dark = tuple(max(0, v - 80) for v in color)
    lw = max(1, size // 24)

    def P(x, y):
        return (int(x * size), int(y * size))

    def half_width(y):
        # cone gets wider from top (y=0.08) to bottom (y=0.86)
        return 0.08 + (y - 0.08) * (0.22 / 0.78)

    # base
    pygame.draw.rect(s, dark, pygame.Rect(P(0.12, 0.84), (int(size * 0.76), int(size * 0.12))), border_radius=2)
    # cone body
    body = [P(0.42, 0.08), P(0.58, 0.08), P(0.80, 0.86), P(0.20, 0.86)]
    pygame.draw.polygon(s, color, body)
    # white stripes
    for y1, y2 in ((0.32, 0.44), (0.56, 0.68)):
        stripe = [P(0.5 - half_width(y1), y1), P(0.5 + half_width(y1), y1),
                  P(0.5 + half_width(y2), y2), P(0.5 - half_width(y2), y2)]
        pygame.draw.polygon(s, (250, 250, 250), stripe)
    pygame.draw.polygon(s, dark, body, lw)
    return s

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((380, 120))
    screen.fill((245, 245, 245))
    screen.blit(pedestrian_icon(64), (10, 20))
    screen.blit(pedestrian_icon(64, (220, 100, 90)), (80, 20))
    screen.blit(trash_icon(64), (150, 20))
    screen.blit(trash_can_icon(64), (220, 20))
    screen.blit(robot_icon(64), (290, 20))
    screen.blit(obstacle_icon(64), (360, 20))
    pygame.display.flip()
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
    pygame.quit()