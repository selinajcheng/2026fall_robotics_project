"""Run: python -m unittest discover -s tests -v"""

import unittest

from sim.collection import TrashCollector
from sim.grid_navigation import find_grid_path, nearest_target, reachable_cells
from sim.world import GridWorld


class TestCollection(unittest.TestCase):
    def test_discovery_only_in_range(self):
        collector = TrashCollector(sensor_range=2)
        trash = {(3, 1), (10, 10)}
        self.assertEqual(collector.detect((1, 1), trash), {(3, 1)})
        self.assertEqual(collector.known_trash, {(3, 1)})
        self.assertEqual(collector.detect((1, 1), trash), set())

    def test_pickup_only_on_cell_once(self):
        collector = TrashCollector()
        trash = {(3, 1)}
        self.assertFalse(collector.collect((1, 1), trash))
        self.assertTrue(collector.collect((3, 1), trash))
        self.assertFalse(collector.collect((3, 1), trash))
        self.assertEqual(collector.collected_count, 1)
        self.assertEqual(trash, set())

    def test_capacity_and_unload_at_station_only(self):
        collector = TrashCollector(capacity=2)
        trash = {(2, 2), (3, 3), (4, 4)}
        self.assertTrue(collector.collect((2, 2), trash))
        self.assertTrue(collector.collect((3, 3), trash))
        self.assertTrue(collector.is_full)
        self.assertFalse(collector.collect((4, 4), trash))
        self.assertFalse(collector.unload((5, 5), (1, 1)))
        self.assertTrue(collector.unload((1, 1), (1, 1)))
        self.assertFalse(collector.is_full)
        self.assertEqual(collector.current_load, 0)
        self.assertEqual(collector.unloads, 1)
        self.assertTrue(collector.collect((4, 4), trash))
        self.assertEqual(collector.collected_count, 3)

    def test_reject_invalid_capacity(self):
        with self.assertRaises(ValueError):
            TrashCollector(capacity=0)


class TestNavigation(unittest.TestCase):
    def setUp(self):
        self.world = GridWorld(columns=5, rows=4, tile_size=28)

    def test_path_avoids_blocked_cell(self):
        blocked = {(2, 1)}
        path = find_grid_path(self.world, (1, 1), (3, 1), blocked)
        self.assertTrue(path)
        self.assertEqual(path[0], (1, 1))
        self.assertEqual(path[-1], (3, 1))
        self.assertNotIn((2, 1), path)
        for first, second in zip(path, path[1:]):
            self.assertIn(second, self.world.neighbors(first))

    def test_reachable_only_excludes_isolated_cells(self):
        blocked = {(1, 0), (1, 1), (1, 2), (1, 3)}
        self.assertNotIn((2, 2), reachable_cells(self.world, (0, 0), blocked))
        self.assertIsNone(nearest_target(self.world, (0, 0), {(2, 2)}, blocked))
        self.assertEqual(find_grid_path(self.world, (0, 0), (2, 2), blocked), [])


if __name__ == "__main__":
    unittest.main()
