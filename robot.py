import pygame


class Robot:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.radius = 20
        self.speed = 200
        self.color = (40, 110, 220)
        self.path = []

    def set_path(self, path):
        self.path = list(path)

    def move(self, keys, dt, width, height):
        dx = 0
        dy = 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1

        direction = pygame.Vector2(dx, dy)

        if direction.length_squared() > 0:
            self.path = []
            direction = direction.normalize()
            self.x += direction.x * self.speed * dt
            self.y += direction.y * self.speed * dt

        elif self.path:
            remaining = self.speed * dt

            while self.path and remaining > 0:
                target = pygame.Vector2(self.path[0])
                position = pygame.Vector2(self.x, self.y)
                offset = target - position
                distance = offset.length()

                if distance <= remaining:
                    self.x, self.y = target.x, target.y
                    remaining -= distance
                    self.path.pop(0)
                else:
                    position += offset.normalize() * remaining
                    self.x, self.y = position.x, position.y
                    remaining = 0

        self.x = max(self.radius, min(width - self.radius, self.x))
        self.y = max(self.radius, min(height - self.radius, self.y))

    def draw(self, screen):
        pygame.draw.circle(
            screen,
            self.color,
            (round(self.x), round(self.y)),
            self.radius
        )

        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (round(self.x), round(self.y)),
            6
        )
