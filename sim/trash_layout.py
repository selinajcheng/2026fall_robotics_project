"""Random, valid trash placement for each integrated demo process."""

import random

from sim.grid_navigation import reachable_cells


def random_trash_cells(scene, count, keep_clear=(), rng=None):
    """Return distinct reachable sidewalk cells, excluding reserved locations."""
    if count < 0:
        raise ValueError("trash count must be nonnegative")

    reserved = set(keep_clear) | {scene.start_cell}
    reachable = reachable_cells(scene.world, scene.start_cell, set())
    candidates = sorted((scene.sidewalk_cells & reachable) - reserved)
    if count > len(candidates):
        raise ValueError("trash count exceeds available sidewalk cells")

    picker = rng if rng is not None else random.SystemRandom()
    return set(picker.sample(candidates, count))
