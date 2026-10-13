"""Entry point: opens the four-block sidewalk world.

Run `python main.py` for the live window, or `python main.py --screenshot out.png`
to save one frame without opening a window.
"""

import os
import sys

import pygame

from sim.render import draw_world
from sim.scene import create_city_scene


SCENE = create_city_scene()


def run(frame_limit: int | None = None, screenshot: str | None = None) -> None:
    pygame.init()
    if not SCENE.world.is_walkable(SCENE.start_cell):
        raise ValueError("The start cell must be walkable")

    screen = pygame.display.set_mode(SCENE.world.pixel_size)
    pygame.display.set_caption("Sidewalk Trash Collection Robot - Four Blocks")
    if screenshot is not None:
        draw_world(screen, SCENE)
        pygame.image.save(screen, screenshot)
        pygame.quit()
        return

    clock = pygame.time.Clock()
    frames = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        draw_world(screen, SCENE)
        pygame.display.flip()
        clock.tick(30)
        frames += 1
        if frame_limit is not None and frames >= frame_limit:
            running = False

    pygame.quit()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--screenshot":
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        run(screenshot=sys.argv[2])
    else:
        run()
