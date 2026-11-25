import random
import sys
import types
import unittest

try:
    import pygame  # noqa: F401
except ModuleNotFoundError:
    sys.modules["pygame"] = types.SimpleNamespace()

from sim.grid_navigation import reachable_cells
from sim.pedestrian_grid import ENTRY_TIME, STEP_TIME, Pedestrian, PedestrianManager
from sim.scene import building_doors, building_entrance_targets, cells_in, create_city_scene
from sim.trash_layout import random_trash_cells


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

    def test_assigned_destination_is_the_building_entered(self):
        scene = create_city_scene()
        doors = building_doors(scene)
        origin, destination = doors[0], doors[-1]
        pedestrian = Pedestrian(
            scene.world,
            {door.sidewalk_cell: door.interior_cell for door in doors},
            sorted(reachable_cells(scene.world, scene.start_cell, set())),
            set(), random.Random(3), origin.sidewalk_cell, 0, "morning_rush",
            destination_cell=destination.sidewalk_cell,
            destination_building_index=destination.building_index,
        )
        pedestrian.exiting = False
        for _ in range(200):
            pedestrian.update(STEP_TIME, set(), 0)
            if pedestrian.inside:
                break
        self.assertTrue(pedestrian.inside)
        self.assertEqual(pedestrian.entry_target, destination.interior_cell)


class TestBuildingDoorFlow(unittest.TestCase):
    def setUp(self):
        self.scene = create_city_scene()
        self.keep_clear = {self.scene.start_cell, (1, 2)} | set(self.scene.crosswalk_cells)
        self.doors = building_doors(self.scene, self.keep_clear)

    def manager(self, seed):
        return PedestrianManager(
            self.scene.world,
            reachable_cells(self.scene.world, self.scene.start_cell, set()),
            set(), self.doors, seed=seed, keep_clear=self.keep_clear,
            crosswalk_cells=self.scene.crosswalk_cells,
        )

    def test_every_active_door_belongs_to_one_reachable_building(self):
        self.assertEqual(len(self.doors), 23)
        self.assertEqual(len({door.building_index for door in self.doors}), len(self.doors))
        self.assertEqual(len({door.sidewalk_cell for door in self.doors}), len(self.doors))
        for door in self.doors:
            self.assertIn(door.sidewalk_cell, self.scene.sidewalk_cells)
            self.assertNotIn(door.sidewalk_cell, self.keep_clear)
            self.assertIn(door.interior_cell, cells_in(self.scene.buildings[door.building_index].rect))
            self.assertEqual(
                abs(door.sidewalk_cell[0] - door.interior_cell[0])
                + abs(door.sidewalk_cell[1] - door.interior_cell[1]), 1,
            )

    def test_trash_never_obscures_a_door(self):
        door_cells = {door.sidewalk_cell for door in self.doors}
        for seed in range(10):
            trash = random_trash_cells(
                self.scene, 7, keep_clear=self.keep_clear | door_cells,
                rng=random.Random(seed),
            )
            self.assertFalse(trash & door_cells)

    def test_seeded_trips_use_distinct_buildings_and_free_entrances(self):
        def trips(seed):
            manager = self.manager(seed)
            manager.pending = [(9 * 60 * 60, "morning_rush")] * 12
            manager._release_pending({self.doors[0].sidewalk_cell})
            self.assertEqual(len(manager.peds), 12)
            self.assertFalse(manager.pending)
            for pedestrian in manager.peds:
                self.assertNotEqual(
                    pedestrian.origin_building_index,
                    pedestrian.destination_building_index,
                )
                self.assertNotEqual(pedestrian.cell, self.doors[0].sidewalk_cell)
            self.assertEqual(len({p.cell for p in manager.peds}), 12)
            return [(p.origin_building_index, p.destination_building_index)
                    for p in manager.peds]

        self.assertEqual(trips(7), trips(7))
        self.assertNotEqual(trips(7), trips(8))

    def test_rush_trips_favor_more_distant_buildings(self):
        origin = self.doors[0]
        def mean_distance(cohort):
            manager = self.manager(9)
            chosen = [manager._choose_destination(origin, cohort) for _ in range(200)]
            return sum(
                abs(door.sidewalk_cell[0] - origin.sidewalk_cell[0])
                + abs(door.sidewalk_cell[1] - origin.sidewalk_cell[1])
                for door in chosen
            ) / len(chosen)

        self.assertGreater(mean_distance("morning_rush"), mean_distance("lunch"))


if __name__ == "__main__":
    unittest.main()
