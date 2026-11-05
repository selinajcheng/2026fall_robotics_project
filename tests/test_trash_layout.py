import random
import unittest

from sim.scene import create_city_scene
from sim.trash_layout import random_trash_cells


class TestTrashLayout(unittest.TestCase):
    def setUp(self):
        self.scene = create_city_scene()

    def test_trash_is_distinct_reachable_sidewalk_and_avoids_reserved_cells(self):
        reserved = {(1, 2), (4, 1)}
        cells = random_trash_cells(
            self.scene, 7, keep_clear=reserved, rng=random.Random(12)
        )
        self.assertEqual(len(cells), 7)
        self.assertTrue(cells <= self.scene.sidewalk_cells)
        self.assertFalse(cells & reserved)
        self.assertNotIn(self.scene.start_cell, cells)

    def test_seeded_layout_is_reproducible_for_tests(self):
        first = random_trash_cells(self.scene, 7, rng=random.Random(3))
        second = random_trash_cells(self.scene, 7, rng=random.Random(3))
        self.assertEqual(first, second)

    def test_invalid_counts_are_rejected(self):
        with self.assertRaises(ValueError):
            random_trash_cells(self.scene, -1)
        with self.assertRaises(ValueError):
            random_trash_cells(self.scene, len(self.scene.sidewalk_cells) + 1)


if __name__ == "__main__":
    unittest.main()
