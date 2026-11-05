import random
import sys
import types
import unittest

try:
    import pygame  # noqa: F401
except ModuleNotFoundError:
    sys.modules["pygame"] = types.SimpleNamespace()

from sim.grid_navigation import reachable_cells
from sim.pedestrian_grid import ENTRY_TIME, Pedestrian
from sim.scene import building_entrance_targets, create_city_scene


class TestPedestrianBuildingEntry(unittest.TestCase):
    def make_pedestrian(self):
        scene = create_city_scene()
        door_targets = building_entrance_targets(scene)
        entrance, building_cell = next(iter(door_targets.items()))
        pedestrian = Pedestrian(
            scene.world,
            door_targets,
            sorted(reachable_cells(scene.world, scene.start_cell, set())),
            set(),
            random.Random(1),
            entrance,
            return_at=0,
            cohort="test",
            crosswalk_cells=scene.crosswalk_cells,
        )
        return pedestrian, entrance, building_cell

    def test_pedestrian_fades_out_of_building_before_walking(self):
        pedestrian, entrance, building_cell = self.make_pedestrian()
        self.assertTrue(pedestrian.exiting)
        self.assertEqual(pedestrian.entry_target, building_cell)
        self.assertEqual(pedestrian.occupied_cells(), {entrance})

        pedestrian.update(ENTRY_TIME / 2, set(), 0)
        self.assertTrue(pedestrian.exiting)
        self.assertAlmostEqual(pedestrian.entry_progress, 0.5)

        pedestrian.update(ENTRY_TIME / 2, set(), 0)
        self.assertFalse(pedestrian.exiting)
        self.assertFalse(pedestrian.inside)
        self.assertEqual(pedestrian.cell, entrance)

    def test_pedestrian_walks_inside_before_becoming_hidden(self):
        pedestrian, entrance, building_cell = self.make_pedestrian()
        pedestrian.exiting = False
        pedestrian.returning = True
        pedestrian.goal = entrance
        pedestrian.goal_is_door = True

        pedestrian.update(0, set(), 0)
        self.assertTrue(pedestrian.entering)
        self.assertFalse(pedestrian.inside)
        self.assertEqual(pedestrian.entry_target, building_cell)
        self.assertEqual(pedestrian.occupied_cells(), {entrance})

        pedestrian.update(ENTRY_TIME / 2, set(), 0)
        self.assertAlmostEqual(pedestrian.entry_progress, 0.5)
        self.assertFalse(pedestrian.inside)

        pedestrian.update(ENTRY_TIME / 2, set(), 0)
        self.assertTrue(pedestrian.inside)
        self.assertEqual(pedestrian.occupied_cells(), set())


if __name__ == "__main__":
    unittest.main()
