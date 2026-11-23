"""Traffic synchronization, crosswalk safety, and Checkpoint 3 signal tests."""
import unittest
from dataclasses import dataclass

from sim.traffic import (
    TrafficSystem, Car, PHASES, CYCLE_DURATION, STOP_GAP,
    signal_position, crosswalk_axis,
)


@dataclass(frozen=True)
class Crossing:
    rect: tuple[int, int, int, int]
    stripe_direction: str


class World:
    tile_size = 28
    columns = 36
    rows = 24
    pixel_size = (36 * 28, 24 * 28)


class Scene:
    world = World()
    crosswalks = (
        Crossing((16, 8, 4, 2), 'vertical'),
        Crossing((16, 14, 4, 2), 'vertical'),
        Crossing((16, 0, 4, 2), 'vertical'),
        Crossing((16, 22, 4, 2), 'vertical'),
        Crossing((14, 10, 2, 4), 'horizontal'),
        Crossing((20, 10, 2, 4), 'horizontal'),
        Crossing((0, 10, 2, 4), 'horizontal'),
        Crossing((34, 10, 2, 4), 'horizontal'),
    )


class TestTraffic(unittest.TestCase):
    def setUp(self):
        self.t = TrafficSystem(Scene())

    def test_one_synchronized_cycle(self):
        # Every vehicle-green interval is followed by yellow and all-red
        # before the perpendicular direction can turn green.
        self.assertEqual(self.t.phase, 'NS_GREEN')
        self.assertTrue(self.t.vehicle_green('NS'))
        self.assertFalse(self.t.vehicle_green('EW'))
        self.assertTrue(self.t.pedestrian_green(Scene.crosswalks[4]))
        self.assertFalse(self.t.pedestrian_green(Scene.crosswalks[0]))

        self.t.update(PHASES[0][1])
        self.assertEqual(self.t.phase, 'NS_YELLOW')
        self.assertFalse(self.t.vehicle_green('NS'))
        self.assertFalse(self.t.vehicle_green('EW'))
        self.assertFalse(self.t.pedestrian_green(Scene.crosswalks[4]))

        self.t.update(PHASES[1][1])
        self.assertEqual(self.t.phase, 'ALL_RED_NS')
        self.assertFalse(self.t.vehicle_green('NS'))
        self.assertFalse(self.t.vehicle_green('EW'))

        self.t.update(PHASES[2][1])
        self.assertEqual(self.t.phase, 'EW_GREEN')
        self.assertTrue(self.t.vehicle_green('EW'))
        self.assertTrue(self.t.pedestrian_green(Scene.crosswalks[0]))

        self.t.update(PHASES[3][1])
        self.assertEqual(self.t.phase, 'EW_YELLOW')
        self.t.update(PHASES[4][1])
        self.assertEqual(self.t.phase, 'ALL_RED_EW')
        self.t.update(PHASES[5][1])
        self.assertEqual(self.t.phase, 'NS_GREEN')

    def test_checkpoint3_display_states_and_yellow_safety(self):
        """All six phases have the right colors and pedestrian permissions."""
        timeline = (
            ('NS_GREEN', 'GREEN', 'RED', 'WALK', 'DONT_WALK'),
            ('NS_YELLOW', 'YELLOW', 'RED', 'DONT_WALK', 'DONT_WALK'),
            ('ALL_RED_NS', 'RED', 'RED', 'DONT_WALK', 'DONT_WALK'),
            ('EW_GREEN', 'RED', 'GREEN', 'DONT_WALK', 'WALK'),
            ('EW_YELLOW', 'RED', 'YELLOW', 'DONT_WALK', 'DONT_WALK'),
            ('ALL_RED_EW', 'RED', 'RED', 'DONT_WALK', 'DONT_WALK'),
        )
        time = 0.0
        for i, (phase, ns, ew, pedestrian_across_ew, pedestrian_across_ns) in enumerate(timeline):
            self.t.elapsed = time + 0.1
            with self.subTest(phase=phase):
                self.assertEqual(self.t.phase, phase)
                self.assertEqual(self.t.vehicle_signal('NS'), ns)
                self.assertEqual(self.t.vehicle_signal('EW'), ew)
                self.assertEqual(
                    self.t.pedestrian_signal(Scene.crosswalks[4]),
                    pedestrian_across_ew,
                )
                self.assertEqual(
                    self.t.pedestrian_signal(Scene.crosswalks[0]),
                    pedestrian_across_ns,
                )
            time += PHASES[i][1]

        # No new car or robot may enter the north/south roadway on yellow.
        self.t.elapsed = PHASES[0][1] + 0.1
        self.assertFalse(self.t.vehicle_green('NS'))
        self.assertFalse(self.t.robot_may_enter((14, 9), (14, 10)))
        car = Car('NS', 1, 17.3 * 28, 180, 100)
        self.t.cars = [car]
        self.t.update(0.2)
        self.assertLessEqual(car.y + car.length / 2, 8 * 28 - STOP_GAP + 1e-6)

    def test_eastbound_stops_before_west_side_crosswalk(self):
        c = Car('EW', 1, 300, 12.7 * 28, 120)
        self.t.cars = [c]
        self.t.update(1)
        # x=14*tile is the near white stripe, NOT x=16 at the junction.
        stop = 14 * 28 - c.length / 2 - STOP_GAP
        self.assertAlmostEqual(c.x, stop)
        self.assertLessEqual(c.x + c.length / 2, 14 * 28 - STOP_GAP)
        self.t.update(1)
        self.assertAlmostEqual(c.x, stop)

    def test_westbound_stops_before_east_side_crosswalk(self):
        c = Car('EW', -1, 700, 11.3 * 28, 90)
        self.t.cars = [c]
        self.t.update(1)
        self.assertAlmostEqual(c.x, 22 * 28 + c.length / 2 + STOP_GAP)

    def test_northbound_stops_before_south_crosswalk_on_red(self):
        # Advance through NS green, NS yellow, and all-red to EW green.
        self.t.update(sum(duration for _, duration in PHASES[:3]) + 0.1)
        c = Car('NS', -1, 18.7 * 28, 495, 120)
        self.t.cars = [c]
        self.t.update(1)
        self.assertAlmostEqual(c.y, 16 * 28 + c.length / 2 + STOP_GAP)

    def test_green_not_just_anytime_enough_to_clear_entire_intersection(self):
        c = Car('NS', 1, 17.3 * 28, 180, 100)
        self.t.cars = [c]
        self.t.update(PHASES[0][1] - 0.8)
        self.assertLessEqual(c.y + c.length / 2, 8 * 28 - STOP_GAP + 1e-6)

    def test_green_car_crosses_without_stopping_at_far_crosswalk(self):
        c = Car('NS', 1, 17.3 * 28, 180, 100)
        self.t.cars = [c]
        for _ in range(100):
            self.t.update(0.05)
        self.assertGreater(c.y, 16 * 28 + c.length / 2)

    def test_robot_must_wait_for_green_and_for_clearance(self):
        # This crossing gets WALK during EW_GREEN, after yellow and all-red.
        self.t.update(sum(duration for _, duration in PHASES[:3]))
        c = Car('NS', 1, 17.3 * 28, 8.5 * 28, 70)
        self.t.cars = [c]
        self.assertFalse(self.t.robot_may_enter((15, 8), (16, 8)))
        c.y = 5 * 28  # Remove the simulated obstruction.
        self.assertTrue(self.t.robot_may_enter((15, 8), (16, 8)))

    def test_robot_waits_at_red_at_sidewalk_and_clears_crossing(self):
        self.assertFalse(self.t.robot_may_enter((15, 8), (16, 8)))
        self.assertTrue(self.t.robot_may_enter((16, 8), (17, 8)))
        self.assertTrue(self.t.robot_may_enter((14, 9), (14, 10)))

    def test_robot_no_entry_near_signal_change(self):
        # End of EW_GREEN: not enough WALK time to start a crossing.
        self.t.update(sum(duration for _, duration in PHASES[:4]) - 0.4)
        self.assertFalse(self.t.robot_may_enter((15, 8), (16, 8)))

    def test_car_does_not_stop_on_remote_crosswalk(self):
        c = Car('EW', 1, -50, 12.7 * 28, 90)
        self.t.cars = [c]
        self.t.update(1)
        self.assertLessEqual(c.x + c.length / 2, 0 - STOP_GAP)

    def test_sync_wrap_and_invalid_time(self):
        self.t.update(CYCLE_DURATION)
        self.assertEqual(self.t.phase, 'NS_GREEN')
        with self.assertRaises(ValueError):
            self.t.update(-0.1)
        with self.assertRaises(ValueError):
            self.t.vehicle_green('x')

    def test_robot_present_prevents_car_entry_even_with_green(self):
        c = Car('NS', 1, 17.3 * 28, 180, 100)
        self.t.cars = [c]
        self.t.update(1, robot_cell=(16, 8))
        self.assertLessEqual(c.y + c.length / 2, 8 * 28 - STOP_GAP + 1e-6)

    def test_lane_centers_match_us_right_hand_traffic_and_white_bars(self):
        east, west, south, north = self.t.cars
        self.assertEqual((east.axis, east.direction), ('EW', 1))
        self.assertEqual((west.axis, west.direction), ('EW', -1))
        self.assertEqual((south.axis, south.direction), ('NS', 1))
        self.assertEqual((north.axis, north.direction), ('NS', -1))
        self.assertGreater(east.y, west.y)
        self.assertLess(south.x, north.x)
        self.assertGreater(east.y, 12 * 28)
        self.assertLess(west.y, 12 * 28)
        self.assertLess(south.x, 18 * 28)
        self.assertGreater(north.x, 18 * 28)

    def test_all_four_approaches_stop_behind_painted_stop_bars(self):
        # NS_GREEN gives EW red; EW_GREEN gives NS red.
        cases = [
            ('EW', 1, 280, 12.7 * 28, 0.0, 14 * 28),
            ('EW', -1, 730, 11.3 * 28, 0.0, 22 * 28),
            ('NS', 1, 17.3 * 28, 110, 14.0, 8 * 28),
            ('NS', -1, 18.7 * 28, 530, 14.0, 16 * 28),
        ]
        for axis, direction, x, y, time, entering_edge in cases:
            with self.subTest(axis=axis, direction=direction):
                t = TrafficSystem(Scene())
                t.elapsed = time
                car = Car(axis, direction, x, y, 150)
                t.cars = [car]
                t.update(2.0)
                front = car.position + direction * car.length / 2
                if direction == 1:
                    self.assertLessEqual(front, entering_edge - STOP_GAP + 1e-6)
                else:
                    self.assertGreaterEqual(front, entering_edge + STOP_GAP - 1e-6)

    def test_signal_heads_are_distinct_non_overlapping_and_inside_city(self):
        # Checkpoint 3 uses 42x42-pixel combined vehicle/pedestrian heads.
        half_width = half_height = 21
        centers = [signal_position(Scene(), c) for c in Scene.crosswalks]
        self.assertEqual(len(centers), 8)
        self.assertEqual(len(set(centers)), 8)
        for i, (x, y) in enumerate(centers):
            self.assertGreaterEqual(x - half_width, 0)
            self.assertLessEqual(x + half_width, Scene.world.pixel_size[0])
            self.assertGreaterEqual(y - half_height, 0)
            self.assertLessEqual(y + half_height, Scene.world.pixel_size[1])
            for j, (a, b) in enumerate(centers[:i]):
                # Leave 6px clearance between signal bounding boxes.
                self.assertTrue(abs(x - a) >= 48 or abs(y - b) >= 48,
                                f'signals {i} and {j} overlap')

    def test_signals_not_over_white_crosswalks(self):
        tile = Scene.world.tile_size
        # Check full 42x42 signal area against ALL crosswalks.
        for crossing in Scene.crosswalks:
            x, y = signal_position(Scene(), crossing)
            for other in Scene.crosswalks:
                left, top, w, h = other.rect
                cl, ct = left * tile, top * tile
                cr, cb = (left + w) * tile, (top + h) * tile
                self.assertFalse(
                    x + 21 > cl and x - 21 < cr and
                    y + 21 > ct and y - 21 < cb,
                    f'signal at {(x, y)} overlaps crosswalk {other.rect}',
                )

    def test_past_stop_line_car_does_not_run_red_light(self):
        # If a car starts slightly beyond its stop center, but has not entered
        # the actual crossing, it cannot proceed on red.
        z = next(z for z in self.t.zones['EW'] if z[0] == 14 * 28)
        car = Car('EW', +1, 14 * 28 - 22, 12.7 * 28, 100)
        old = car.x
        car.advance(0.2, False, 0.0, self.t.scene.world, (z,))
        self.assertAlmostEqual(old, car.x)


if __name__ == '__main__':
    unittest.main()
