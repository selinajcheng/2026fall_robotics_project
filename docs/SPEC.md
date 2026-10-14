# Sidewalk Trash Collection Robot — Working Specification

**Scope:** Checkpoint 1 implementation guide.  
**Source of truth for team tasks:** [`copy_of_shared_google_doc.md`](copy_of_shared_google_doc.md), especially its Pre-demo task list, plus Selina's clarifications.  
**Course requirements:** [`project_specifications.pdf`](project_specifications.pdf).  
**Visual environment:** [`VISUAL_ENVIRONMENT_SPEC.md`](VISUAL_ENVIRONMENT_SPEC.md) records Selina's scene requirements.
**Earlier concept draft:** [`SPEC_IDEATION.md`](SPEC_IDEATION.md); useful ideas outside the current scope.

## Goal and first demonstration

Build a runnable, top-down Python/Pygame simulation of a sidewalk trash collection robot. The immediate Checkpoint 1 demonstration should show the robot autonomously sweeping the reachable sidewalk, discovering trash, navigating to it while avoiding static obstacles and people, and collecting it with a visible count. The team will discuss the demo on Wednesday, October 14; the course checkpoint is due Thursday, October 15, 2026, before the in-class demonstrations.

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

The first demo's priority is **autonomous exploration with detection and collection across the reachable area**. Bin capacity, return to the station, and unloading are optional extensions, even though they appear in the team's task list. A station may be drawn before it has any behavior. The earlier concept draft describes further features such as randomized maps, pedestrian replanning, and responsible-design evaluation; those are later work unless added to this specification.

## Checkpoint 1 behavior

These choices define how the first implementation's modules fit together. Record any changes here when implementation requires them.

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
| Blocked target | Record the failure and select another reachable target; never loop indefinitely |
| End of run | Stop after visiting every reachable walkable cell and collecting all trash detected during that sweep |
| Scene | One fixed, repeatable arrangement for the initial demo |

With the complete static map, determine the cells reachable from the robot's start. Track which of those cells the robot has visited, then route to the nearest unvisited reachable cell by planned path length. Prioritize newly detected reachable trash, collect it, and resume the sweep. Mark the run complete only when the reachable set has been visited and no detected reachable trash remains. Coverage means **every reachable walkable cell visited**, not merely passed by the sensor's radius. Cells isolated by walls or static people are outside that reachable set. A later version can replace the known map with incremental mapping without changing the collection goal.

The world and the robot's knowledge must be separate. The robot knows the sidewalk and fixed blockers at startup, while trash stays unknown until sensed. The audience sees trash from the start to understand the task; that display reads world state without passing hidden positions to navigation or target selection. Mark discovered items visually so viewers can distinguish robot knowledge from the audience view.

## Integration boundaries

- **World:** owns bounds, walkable/blocked cells, people, station, and actual trash positions; rejects invalid movement and pickup.
- **Robot:** owns position, movement state, visited cells, known trash, and collection count.
- **Navigator:** given the robot's known map and a target, returns a legal path or a clear unreachable result. A* is the team's stated approach and needs no separate package.
- **Controller:** chooses an exploration or known-trash target, requests a path, and advances the robot along it.
- **Renderer/main loop:** draws the current world, robot, and count; advances simulation steps without requiring manual steering.

The exact Python file layout can be chosen during implementation. These boundaries describe data ownership so teammates can work in parallel without hidden trash leaking into navigation or duplicate pickup counts.

## Verification for the first demo

Before the rehearsal, run the fixed scene from a fresh launch and record whether the robot (1) stays within bounds, (2) avoids blocked cells and static people, (3) visits every reachable sidewalk cell, (4) discovers trash according to the chosen sensor rule, (5) reaches and collects each reachable item once, and (6) displays a correct count. Keep one short record of a failure or limitation and what the team changed or plans to change; Ali can use it in the memo. A repeatable start state is enough for this first pass; additional seeded scenes and comparative performance tests can follow later.

## Values to record during implementation

1. Set and document the trash sensing radius and whether obstacles block sensing.
2. Set and document any clearance around static people beyond their blocked cells.
3. The current four-block world uses 36 columns, 24 rows, 28-pixel tiles, and start cell `(1, 1)`. Four equal 16-by-10-cell rectangular blocks each contain a cluster of six or seven stepped grey rooftop volumes and a two-cell sidewalk ring with rounded visual corners. Four-cell roads form a central intersection, and eight marked crosswalks connect the blocks: four around the intersection and one at the end of each road, giving 416 walkable cells. The center of the intersection has no lane paint; white stop bars and dashed lane lines sit on the approaches. The map lives in `sim/scene.py` and is drawn by `sim/render.py`. Document any later scene-placement changes here.
4. Document the route tie-break rule when multiple targets have the same planned path length.
5. If station behavior, capacity, or unloading is added after the core loop works, document its rules and update the demo plan.

Update this document when implementation values or behavior change. The course handout controls submission rules; Selina's team task list controls planned work; this document records robot behavior and interfaces.
