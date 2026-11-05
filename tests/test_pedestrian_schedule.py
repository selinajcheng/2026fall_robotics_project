import unittest

from sim.pedestrian_schedule import HOUR, MINUTE, PedestrianSchedule
from sim.scene import building_entrance_cells, cells_in, create_city_scene


class TestPedestrianSchedule(unittest.TestCase):
    def setUp(self):
        self.schedule = PedestrianSchedule(seed=8)
        self.assertEqual(self.schedule.update(5 * HOUR), [])

    def requests_at(self, time):
        return self.schedule.update(time)

    def scheduled_request(self, time, label):
        matches = [request for request in self.requests_at(time) if request.label == label]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_no_pedestrians_before_six(self):
        self.assertEqual(self.requests_at(5 * HOUR + 59 * MINUTE), [])

    def test_no_fixed_cohort_at_six(self):
        self.assertEqual(self.requests_at(6 * HOUR), [])

    def test_rush_and_meal_cohorts(self):
        self.requests_at(6 * HOUR)
        morning = self.scheduled_request(8 * HOUR + 45 * MINUTE, "morning_rush")
        self.assertEqual(morning.return_times, (9 * HOUR,) * 10)

        lunch = self.scheduled_request(12 * HOUR, "lunch")
        self.assertEqual(lunch.count, 8)
        for return_at in lunch.return_times:
            self.assertGreaterEqual(return_at, 12 * HOUR + 30 * MINUTE)
            self.assertLessEqual(return_at, 12 * HOUR + 40 * MINUTE)

        afternoon = self.scheduled_request(13 * HOUR, "afternoon")
        self.assertEqual(afternoon.count, 4)
        for return_at in afternoon.return_times:
            self.assertGreaterEqual(return_at, 13 * HOUR + 30 * MINUTE)
            self.assertLessEqual(return_at, 13 * HOUR + 40 * MINUTE)

        evening = self.scheduled_request(17 * HOUR, "evening_rush")
        self.assertEqual(evening.return_times, (17 * HOUR + 30 * MINUTE,) * 10)

    def test_background_stream_starts_after_six(self):
        self.requests_at(6 * HOUR)
        requests = self.requests_at(8 * HOUR)
        background = [request for request in requests if request.label == "background"]
        self.assertTrue(background)
        self.assertTrue(all(1 <= request.count <= 3 for request in background))


class TestBuildingEntrances(unittest.TestCase):
    def test_entrances_are_distinct_sidewalk_cells_beside_buildings(self):
        scene = create_city_scene()
        keep_clear = {scene.start_cell, (1, 2)} | set(scene.crosswalk_cells)
        entrances = building_entrance_cells(scene, keep_clear)
        self.assertEqual(len(entrances), len(set(entrances)))
        self.assertTrue(entrances)
        self.assertFalse(set(entrances) & keep_clear)

        building_cells = [cells_in(building.rect) for building in scene.buildings]
        for entrance in entrances:
            self.assertIn(entrance, scene.sidewalk_cells)
            x, y = entrance
            neighbors = {(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)}
            self.assertTrue(any(neighbors & cells for cells in building_cells))


if __name__ == "__main__":
    unittest.main()
