# Sidewalk Trash Collection Robot — Working Specification

**Scope:** Checkpoint 1 implementation guide.  
**Source of truth for team tasks:** [`copy_of_shared_google_doc.md`](copy_of_shared_google_doc.md), especially its Pre-demo task list, plus Selina's clarifications.  
**Course requirements:** [`project_specifications.pdf`](project_specifications.pdf).  
**Visual environment:** [`VISUAL_ENVIRONMENT_SPEC.md`](VISUAL_ENVIRONMENT_SPEC.md) records Selina's scene requirements.
**Earlier concept draft:** [`SPEC_IDEATION.md`](SPEC_IDEATION.md); useful ideas outside the current scope.

## Goal and first demonstration

The current Checkpoint 1 demo is a runnable, top-down Python/Pygame simulation. The robot autonomously sweeps reachable sidewalk cells, discovers and collects trash, routes around fixed obstacles and people, unloads at the station, and returns to its start. The team will discuss the demo on Wednesday, October 14; the course checkpoint is due Thursday, October 15, 2026, before the in-class demonstrations.

The course asks for a working prototype or integrated subsystem, an in-class demonstration of real behavior, a GitHub commit link, and a memo of no more than two pages. The memo needs a system diagram, initial testing evidence, limitations, and next priorities. Ali is expected to cover the memo; the code team needs to provide accurate behavior and test evidence for it.

## Checkpoint 1 scope

| Component | First-demo expectation | Task owner from team notes |
| --- | --- | --- |
| Project setup | `requirements.txt` and useful `README.md` with install/run instructions for teammates | Selina |
| Simulation world | Bounded sidewalk area that the robot cannot leave | Selina |
| Robot and motion | Visible robot with autonomous movement | Mahbub |
| Navigation | Route around static obstacles; behavior when a route is blocked must be defined | Mahbub |
| Scene objects | Obstacles, people, one disposal station, and fixed trash locations in the initial scene | Amaya |
| Collection | Remove/reclassify a reached trash item and increment a visible count once | Ishraq |
| Presentation and verification | Visual polish and full demo run-through | Wei Xi |

The integrated demo now includes the previously optional bin capacity, return, and unloading behavior. The earlier concept draft describes further features such as randomized maps, pedestrian replanning, and responsible-design evaluation; those remain later work. `robot_demo.py` is a separate prototype with moving pedestrians and manual controls; its pedestrian behavior is not part of the integrated city demo.

## Checkpoint 1 behavior

These choices describe the behavior currently implemented by `main.py`.

| Decision | Checkpoint 1 behavior |
| --- | --- |
| Exploration | Robot autonomously sweeps the entire reachable sidewalk from its start, interrupting the sweep to collect detected trash and then resuming |
| Map knowledge | Give the robot the complete static walkable/blocked map, including fixed people, at startup |
| Trash knowledge | World stores all trash; robot learns an item's location only when that item enters sensor range |
| Audience view | Render all trash from the start while keeping undiscovered positions out of robot/planner state; indicate which items the robot has sensed |
| People | Show people as fixed obstacles that the robot routes around |
| Map and movement | Tile grid with four-direction moves; only sidewalk and marked crosswalk cells are traversable; reject buildings, ordinary roads, blocked cells, and out-of-bounds moves |
| Pickup | Pick up when the robot reaches the trash cell; count each item once |
| Priority | If trash is known and reachable, navigate to it; otherwise continue exploring |
| Bin and station | Capacity is three items. At capacity, route to station `(1, 2)` and unload; after the sweep, unload any partial load too |
| Blocked target | Choose only targets reachable from the start; a missing route to a selected target raises an error |
| End of run | After visiting every reachable cell and clearing the bin, return to start `(1, 1)` and show `COMPLETE` |
| Scene | One fixed, repeatable arrangement for the initial demo |

With the complete static map, determine the cells reachable from the robot's start. Track which of those cells the robot has visited, then choose the nearest unvisited reachable cell by shortest path length. Prioritize newly detected reachable trash, collect it, and resume the sweep. Replan at each cell center so newly detected trash can change the next target. Coverage means **every reachable walkable cell visited**, not merely passed by the sensor's radius. The map has 416 walkable cells; the two fixed people and two fixed obstacles leave 412 reachable. A later version can replace the known map with incremental mapping without changing the collection goal.

The world and the robot's knowledge are separate. The robot knows the sidewalk and fixed blockers at startup, while trash stays unknown until sensed. The audience sees red, undiscovered trash from the start; sensed trash turns green. Rendering reads world state without passing hidden positions to navigation or target selection. The sensor uses Manhattan distance of at most two grid cells and does not model occlusion by obstacles.

## Integration boundaries

- **`sim/scene.py` and `sim/world.py`:** define the walkable city grid, buildings, and start cell.
- **`main.py`:** defines fixed people, obstacles, trash, and station cells; owns the world trash set, visited cells, target selection, and autonomous loop.
- **`sim/collection.py`:** tracks sensed trash, pickups, current load, capacity, and unload count.
- **`sim/grid_navigation.py`:** computes reachable cells, selects nearest reachable targets by breadth-first search, and finds legal grid paths with A*.
- **`robot.py`:** moves the robot between pixel-center waypoints supplied by `main.py`.
- **`sim/render.py` and `icons.py`:** draw the city background and scene-object icons; `main.py` draws the status panel and legend.

The separate `navigation.py` and `robot_demo.py` implement an open-area navigation prototype; `main.py` uses the city-grid adapter instead.

## Verification for the first demo

Before the rehearsal, run the fixed scene from a fresh launch and record whether the robot (1) stays within bounds, (2) avoids blocked cells and static people, (3) visits all 412 reachable cells, (4) discovers trash according to the two-cell sensor rule, (5) collects each of the seven reachable items once, (6) unloads whenever full and unloads the final partial load, and (7) returns to start with a correct status and count. Run `python -m unittest discover -s tests -v` for collection and grid-navigation checks. Keep one short record of a failure or limitation and what the team changed or plans to change; Ali can use it in the memo. A repeatable start state is enough for this first pass; additional seeded scenes and comparative performance tests can follow later.

## Values to record during implementation

1. Trash sensing uses Manhattan range two, without obstacle occlusion. Pickup requires the robot to reach the item's cell and have free bin space.
2. Fixed people and obstacles block their own cells. The integrated demo adds no clearance beyond those cells.
3. The four-block world uses 36 columns, 24 rows, 28-pixel tiles, and start cell `(1, 1)`. Four equal 16-by-10-cell rectangular blocks each contain a cluster of six or seven stepped grey rooftop volumes and a two-cell sidewalk ring with rounded visual corners. Four-cell roads form a central intersection, and eight marked crosswalks connect the blocks: four around the intersection and one at the end of each road, giving 416 walkable cells. The center of the intersection has no lane paint; white stop bars and dashed lane lines sit on the approaches. The map lives in `sim/scene.py` and is drawn by `sim/render.py`.
4. The seven trash cells, two people, two obstacles, and station cell are fixed in `main.py`. Target selection uses breadth-first search; equal-distance choices follow the world neighbor order. The A* path uses Manhattan distance and its queue's tuple order to break equal-cost ties.
5. Bin capacity is three. Unloading requires the robot to be at station `(1, 2)` with a nonempty bin; the display pauses there briefly. After the full sweep, the robot unloads any remaining items and returns to start.

Update this document when implementation values or behavior change. The course handout controls submission rules; Selina's team task list controls planned work; this document records robot behavior and interfaces.
