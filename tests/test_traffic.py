"""Traffic-light synchronization, pre-crosswalk stopping, robot yield tests."""
import unittest
from dataclasses import dataclass
from sim.traffic import TrafficSystem, Car, PHASES, CYCLE_DURATION, STOP_GAP, signal_position, crosswalk_axis

@dataclass(frozen=True)
class Crossing:
    rect: tuple[int,int,int,int]
    stripe_direction: str

class World:
    tile_size=28
    columns=36
    rows=24
    pixel_size=(36*28,24*28)

class Scene:
    world=World()
    crosswalks=(
        Crossing((16,8,4,2),'vertical'),Crossing((16,14,4,2),'vertical'),
        Crossing((16,0,4,2),'vertical'),Crossing((16,22,4,2),'vertical'),
        Crossing((14,10,2,4),'horizontal'),Crossing((20,10,2,4),'horizontal'),
        Crossing((0,10,2,4),'horizontal'),Crossing((34,10,2,4),'horizontal'))

class TestTraffic(unittest.TestCase):
    def setUp(self):
        self.t=TrafficSystem(Scene())

    def test_one_synchronized_cycle(self):
        self.assertEqual(self.t.phase,'NS_GREEN')
        self.assertTrue(self.t.vehicle_green('NS'))
        self.assertFalse(self.t.vehicle_green('EW'))
        self.assertTrue(self.t.pedestrian_green(Scene.crosswalks[4]))
        self.assertFalse(self.t.pedestrian_green(Scene.crosswalks[0]))
        self.t.update(PHASES[0][1]+0.1)
        self.assertTrue(self.t.phase.startswith('ALL_RED'))
        self.assertFalse(self.t.vehicle_green('NS'))
        self.assertFalse(self.t.vehicle_green('EW'))
        self.t.update(PHASES[1][1])
        self.assertEqual(self.t.phase,'EW_GREEN')
        self.assertTrue(self.t.pedestrian_green(Scene.crosswalks[0]))

    def test_eastbound_stops_before_west_side_crosswalk(self):
        c=Car('EW',1,300,12.7*28,120)
        self.t.cars=[c]
        self.t.update(1)
        # x=14*tile is the *near white stripe*, NOT x=16 at junction.
        stop=14*28-c.length/2-STOP_GAP
        self.assertAlmostEqual(c.x,stop)
        self.assertLessEqual(c.x+c.length/2,14*28-STOP_GAP)
        self.t.update(1)
        self.assertAlmostEqual(c.x,stop)

    def test_westbound_stops_before_east_side_crosswalk(self):
        c=Car('EW',-1,700,11.3*28,90)
        self.t.cars=[c]
        self.t.update(1)
        self.assertAlmostEqual(c.x,22*28+c.length/2+STOP_GAP)

    def test_northbound_stops_before_south_crosswalk_on_red(self):
        self.t.update(PHASES[0][1]+PHASES[1][1]+0.1) # EW green => NS red
        c=Car('NS',-1,18.7*28,495,120)
        self.t.cars=[c]
        self.t.update(1)
        self.assertAlmostEqual(c.y,16*28+c.length/2+STOP_GAP)

    def test_green_not_just_anytime_enough_to_clear_entire_intersection(self):
        c=Car('NS',1,17.3*28,180,100)
        self.t.cars=[c]
        self.t.update(PHASES[0][1]-0.8)
        self.assertLessEqual(c.y+c.length/2,8*28-STOP_GAP+1e-6)

    def test_green_car_crosses_without_stopping_at_far_crosswalk(self):
        c=Car('NS',1,17.3*28,180,100)
        self.t.cars=[c]
        for _ in range(100):self.t.update(0.05)
        self.assertGreater(c.y,16*28+c.length/2)

    def test_robot_must_wait_for_green_and_for_clearance(self):
        self.t.update(PHASES[0][1]+PHASES[1][1]) # enter EW_GREEN
        c=Car('NS',1,17.3*28,8.5*28,70)  # an unexpected lingering car
        self.t.cars=[c]
        self.assertFalse(self.t.robot_may_enter((15,8),(16,8)))
        c.y=5*28 # move clear, case sim should forbid this naturally
        self.assertTrue(self.t.robot_may_enter((15,8),(16,8)))

    def test_robot_waits_at_red_at_sidewalk_and_clears_crossing(self):
        self.assertFalse(self.t.robot_may_enter((15,8),(16,8)))
        self.assertTrue(self.t.robot_may_enter((16,8),(17,8)))
        self.assertTrue(self.t.robot_may_enter((14,9),(14,10)))

    def test_robot_no_entry_near_signal_change(self):
        self.t.update(PHASES[0][1]+PHASES[1][1]+PHASES[2][1]-0.4)
        self.assertFalse(self.t.robot_may_enter((15,8),(16,8)))

    def test_car_does_not_stop_on_remote_crosswalk(self):
        c=Car('EW',1,-50,12.7*28,90)
        self.t.cars=[c]
        self.t.update(1)
        self.assertLessEqual(c.x+c.length/2,0-STOP_GAP)

    def test_sync_wrap_and_invalid_time(self):
        self.t.update(CYCLE_DURATION)
        self.assertEqual(self.t.phase,'NS_GREEN')
        with self.assertRaises(ValueError):self.t.update(-0.1)
        with self.assertRaises(ValueError):self.t.vehicle_green('x')

    def test_robot_present_prevents_car_entry_even_with_green(self):
        c=Car('NS',1,17.3*28,180,100)
        self.t.cars=[c]
        self.t.update(1,robot_cell=(16,8))
        self.assertLessEqual(c.y+c.length/2,8*28-STOP_GAP+1e-6)


    def test_lane_centers_match_us_right_hand_traffic_and_white_bars(self):
        east, west, south, north = self.t.cars
        self.assertEqual((east.axis, east.direction), ('EW', 1))
        self.assertEqual((west.axis, west.direction), ('EW', -1))
        self.assertEqual((south.axis, south.direction), ('NS', 1))
        self.assertEqual((north.axis, north.direction), ('NS', -1))
        self.assertGreater(east.y, west.y)  # eastbound on south/lower half
        self.assertLess(south.x, north.x)   # southbound on west/left half
        self.assertGreater(east.y, 12 * 28)
        self.assertLess(west.y, 12 * 28)
        self.assertLess(south.x, 18 * 28)
        self.assertGreater(north.x, 18 * 28)

    def test_all_four_approaches_stop_behind_painted_stop_bars(self):
        # NS_GREEN gives EW a red. EW_GREEN gives NS a red.
        cases = [
            ('EW', 1, 280, 12.7*28, 0.0, 14*28),
            ('EW', -1, 730, 11.3*28, 0.0, 22*28),
            ('NS', 1, 17.3*28, 110, 11.6, 8*28),
            ('NS', -1, 18.7*28, 530, 11.6, 16*28),
        ]
        for axis, direction, x, y, time, entering_edge in cases:
            with self.subTest(axis=axis, direction=direction):
                t = TrafficSystem(Scene())
                t.elapsed = time
                car = Car(axis, direction, x, y, 150)
                t.cars = [car]
                t.update(2.0)
                front = car.position + direction * car.length/2
                if direction == 1:
                    self.assertLessEqual(front, entering_edge - STOP_GAP + 1e-6)
                else:
                    self.assertGreaterEqual(front, entering_edge + STOP_GAP - 1e-6)

    def test_signal_heads_are_distinct_non_overlapping_and_inside_city(self):
        centers = [signal_position(Scene(), c) for c in Scene.crosswalks]
        self.assertEqual(len(centers), 8)
        self.assertEqual(len(set(centers)), 8)
        for i, (x, y) in enumerate(centers):
            self.assertGreaterEqual(x - 21, 0)
            self.assertLessEqual(x + 21, Scene.world.pixel_size[0])
            self.assertGreaterEqual(y - 12, 0)
            self.assertLessEqual(y + 12, Scene.world.pixel_size[1])
            for j, (a, b) in enumerate(centers[:i]):
                # 42x24-pixel heads plus a small visual margin.
                self.assertTrue(abs(x-a) >= 48 or abs(y-b) >= 30,
                                f'signals {i} and {j} overlap')

    def test_signals_not_over_white_crosswalks(self):
        tile=Scene.world.tile_size
        for crossing in Scene.crosswalks:
            x, y = signal_position(Scene(), crossing)
            left, top, w, h = crossing.rect
            cl, ct, cr, cb = left*tile, top*tile, (left+w)*tile, (top+h)*tile
            self.assertFalse(x+21 > cl and x-21 < cr and y+12 > ct and y-12 < cb)

    def test_past_stop_line_car_does_not_run_red_light(self):
        # Even if a car starts slightly beyond the computed stop center,
        # if its bumper has not entered the actual crosswalk, it must wait.
        z=next(z for z in self.t.zones['EW'] if z[0] == 14*28)
        car=Car('EW',+1,14*28-22,12.7*28,100)
        old=car.x
        car.advance(0.2,False,0.0,self.t.scene.world,(z,))
        self.assertAlmostEqual(old,car.x)

if __name__=='__main__':unittest.main()
