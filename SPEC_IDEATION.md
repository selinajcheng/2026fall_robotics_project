# Autonomous Sidewalk Sanitation Robot — Project Specification

**Course:** CSCI 39536 — Introduction to Robotics  
**Project type:** Team project; 2D simulated autonomous robot  
**Status:** Earlier design notes (not yet implemented)  
**Initial checkpoint:** October 15, 2026, before in-class demonstrations

## 1. Project summary

Build a simulated autonomous sanitation robot that **actively explores a designated sidewalk area to discover litter**, navigates to detected items, collects them, and returns to a fixed disposal station when its bin is full or its task is complete. The robot must avoid obstacles and, in later iterations, account for pedestrians and safety constraints.

The central robotics challenge is **online exploration and collection under incomplete information**: the robot may know which areas are walkable, but **does not start with the locations of litter**. It must discover these through simulated sensing.

**Primary question:** How can a sidewalk robot systematically cover an area, discover and collect litter efficiently, and operate safely around other sidewalk users?

## 2. Scope and assumptions

### Initial environment

- A **top-down, 2D, grid-based** neighborhood sidewalk simulation implemented in **Python + Pygame**.
- The robot, static obstacles, litter, and one disposal station are represented as distinct entities.
- The robot starts with a map of *walkable vs. blocked* cells; it does **not** initially know litter positions.
- Litter locations are randomly seeded or preconfigured in test scenarios and remain hidden until sensed.
- Collection is **abstracted**: when the robot is close enough to litter, it takes a simulated pickup action; no robotic arm physics are required.
- Sidewalk-only travel is the baseline. Road crossings, traffic lights, vehicles, and manipulation physics are optional future extensions, **not Checkpoint 1 requirements**.

### Non-goals for the initial implementation

- Realistic computer vision, SLAM, robotic arm dynamics, or ROS/Gazebo integration.
- Unstructured, photorealistic neighborhood simulation.
- Optimally solving the full multi-target collection/routing problem.

These simplifications should be disclosed in the memo and demo.

## 3. Stakeholders and design considerations

| Stakeholder | Relevant need | Initial or future design response |
|---|---|---|
| Sanitation workers / city operations | Less repetitive litter collection; predictable operation | Defined service area, collection progress and disposal counts |
| Pedestrians | Safe, unobstructed sidewalk access | Obstacle avoidance now; yielding/clearance around people later |
| Wheelchair users and others with mobility constraints | Adequate passage and accessibility | Treat narrow passages as unsuitable; maintain safety clearance |
| Neighborhood residents | Cleaner shared space and minimal disturbance | Complete collection with measurable coverage and reasonable travel distance |

**Human-centered requirement:** The robot should not prioritize trash collection at the expense of sidewalk accessibility or pedestrian safety. The first prototype can encode clearance around static objects; later checkpoints should demonstrate explicit responses to pedestrians and document the resulting tradeoffs.

## 4. Functional requirements

### Checkpoint 1 — Minimum viable prototype (MVP)

| ID | Requirement | Acceptance criterion |
|---|---|---|
| FR-01 | Render a 2D sidewalk environment | Distinguishable walkable cells, obstacles, robot, litter and disposal station |
| FR-02 | Autonomously explore | Robot follows a systematic route toward unvisited reachable cells, without manual driving |
| FR-03 | Simulate local trash sensing | Litter becomes known to the robot only when inside a configurable detection radius |
| FR-04 | Plan paths around static obstacles | A* produces valid routes through traversable cells to waypoints or detected litter |
| FR-05 | Navigate and collect | Robot moves along the path, reaches reachable litter and registers simulated pickup |
| FR-06 | Track carrying capacity | A visible counter increases on pickup; robot cannot collect beyond set capacity |
| FR-07 | Return and unload | When full, robot plans a route to the station, empties its bin, then resumes if areas or litter remain |
| FR-08 | Complete task safely | Robot returns to station and enters `DONE` when reachable area is covered and no known reachable litter remains |
| FR-09 | Show runtime diagnostics | Show current state, collected items, capacity, and coverage estimate |

**Fallback for a tight Checkpoint 1 schedule:** Demonstrate FR-01 through FR-05 first; implement capacity-triggered return (FR-06 to FR-08) if time permits. A coherent working exploration → detection → collection loop is more valuable than incomplete features.

### Future capabilities

- **Checkpoint 2:** Moving pedestrians, real-time obstacle detection, stopping/replanning, improved target selection and route efficiency, multiple randomized maps.
- **Checkpoint 3:** Concrete pedestrian-safe navigation rules (e.g., yielding and clearance), stakeholder-oriented evaluation, responsible-design tradeoffs, documented failure modes.
- **Final:** End-to-end neighborhood sanitation behavior across multiple seeded scenarios, comparative evaluation, polished demonstration, and thorough documentation.

## 5. Architecture sketch

```text
World / Simulation (grid, static obstacles, litter, disposal station)
         │  local observations, map + sensor readings
         ▼
Perception (limited-range litter detection; future pedestrian sensing)
         │  detected litter + local occupancy
         ▼
Task Manager / State Machine  ◄──── bin capacity, coverage, task progress
   ├─ choose next unexplored target (Coverage Planner)
   ├─ choose detected litter target
   └─ return to disposal station
         │  navigation goal
         ▼
Global Planner (A* over walkable cells, obstacle clearance)
         │  waypoint path
         ▼
Motion Controller (step toward next waypoint; stop if blocked)
         │  move/pickup/unload action
         ▼
World / Simulation  ─────► status and metrics / Pygame display
```

### Suggested Python modules

```text
sidewalk-sanitation-robot/
├── main.py             # Loop, initialization, rendering
├── world.py            # Map, obstacles, litter, disposal station
├── robot.py            # Pose, capacity, action state
├── perception.py       # Limited-range observations
├── coverage.py         # Next unvisited reachable cell/region
├── planner.py          # A* grid routing
├── controller.py       # Waypoint following and collision checks
├── task_manager.py     # State transitions and priorities
├── metrics.py          # Coverage, collected litter, distance, collisions
├── scenarios.py        # Reproducible maps / RNG seeds
├── tests/
├── requirements.txt
└── README.md
```

The initial version can start with fewer files, but keep **world state** separate from **robot knowledge**. Otherwise hidden litter may unintentionally leak into the planner.

## 6. Behavior specification

### Robot states

- `EXPLORE`: Select and travel toward the next unvisited reachable sidewalk area.
- `NAVIGATE_TO_LITTER`: Travel to a detected, reachable litter item.
- `COLLECT`: Pick up the item when within collection distance and increment bin load.
- `RETURN_TO_STATION`: Navigate to disposal station if full, or when cleaning is complete.
- `UNLOAD`: Reset bin load at station; resume exploration if unfinished.
- `DONE`: Stop when the reachable region has been explored and no collectible detected litter remains.
- `BLOCKED` (optional): Stop safely and report that no valid route exists.

### Priority rules

1. Never intentionally move into a blocked cell or violate required clearance.
2. If capacity is reached, return to disposal station before another pickup.
3. Otherwise, if reachable detected litter is available, select a target and collect it.
4. Otherwise, continue systematic exploration.
5. If all reachable space has been covered and no known reachable litter remains, return and finish.
6. If a destination becomes unreachable, do not loop forever: record the failure and select another target or stop.

### Exploration policy (MVP)

Use a **systematic coverage heuristic**: track visited traversable cells and choose a reachable unvisited cell, then route to it using A*. A simple nearest-unvisited-cell policy is suitable for an initial implementation. A lawnmower/boustrophedon sweep can be explored for more regular maps. This is *coverage-driven navigation*, not a claim of globally optimal coverage.

### Local sensing

At each simulation step, reveal litter within a configurable sensing radius centered on the robot. A small on-screen sensor circle helps viewers understand what the robot can and cannot see. For the MVP, detection may be perfect within range; document this assumption.

### Navigation

- Use **A*** for route planning on the currently known traversable map.
- Model the robot as having a nonzero radius; conservatively block narrow gaps by inflating obstacles or by equivalent clearance checking.
- Follow waypoints with a simple discrete movement controller. More realistic steering/control can come later.
- For dynamic obstacles (future), stop or replan when a path is invalidated.

### Collection and unloading

- Pickup succeeds only within a defined range and while the bin has space.
- Each collected item disappears from the world and increments the counter exactly once.
- At the disposal station, unloading resets the counter; maintain a separate lifetime total of items disposed.
- Task completion must account for unvisited reachable locations; the robot must not declare the area clean merely because its current list of detected litter is empty.

## 7. Testing and evaluation

Use deterministic random seeds to reproduce test cases.

| Test scenario | Expected result | Measurements |
|---|---|---|
| Empty, unobstructed map | Full reachable-area coverage, return to station | Coverage %, distance, elapsed steps |
| Static obstacles and scattered litter | Navigate around obstacles; discover and collect reachable litter | Collection %, collisions, route failures |
| Trash count exceeds bin capacity | Return, unload and resume before reaching capacity limit again | Unloading trips, collected/disposed count |
| Narrow or blocked route | Avoid collision; handle unreachable target without hanging | Collisions, unreachable-target handling |
| Multiple random seeds | Stable task behavior, with failures documented | Success rate, distance, coverage % |

**Metric definitions:**

- **Coverage:** unique reachable walkable cells visited or sensed ÷ total reachable walkable cells (state which definition is used).
- **Collection rate:** litter items collected ÷ total reachable litter items (ground truth used **for evaluation only**, not by the robot).
- **Collision count:** invalid attempts to occupy blocked/unsafe space.
- **Travel distance:** total cells/units traveled, including disposal trips.
- **Disposal trips:** number of completed unloading events.

For Checkpoint 1, include at least a few test runs with a small table or screenshots, and explain one failure/limitation and the resulting design decision.

## 8. Checkpoint plan and deliverables

### Checkpoint 1 — Thursday, October 15, 2026

**Submission:**

- [ ] GitHub repository with code, requirements, README, setup/run instructions, and a **specific commit link**.
- [ ] Memo **no longer than two pages** covering: problem, context, stakeholders, initial requirements, architecture + **system diagram**, current functionality, initial test evidence, limitations, next priorities, and major stakeholder-driven changes (if any).
- [ ] **In-class demonstration of actual running system behavior**, not slides alone.
- [ ] Disclosure of significant generative AI use and how important AI-produced code/outputs were tested or modified.

**Demo script (target sequence):** Launch one seeded map → show exploration with undiscovered litter → robot senses an item → routes to it → collects it → [if implemented] fills bin → returns to station → unloads → resumes. Display state and counters throughout.

**Checkpoint 1 grading:** Problem/context/stakeholders 20%; working prototype 30%; architecture/integration 20%; testing/learning 20%; communication/documentation 10%.

### Checkpoint 2 — November 5, 2026

Focus on **technical integration and autonomous behavior**: pedestrians, replanning, more robust task planning, quantitative performance, and at least two significant failure modes in a memo of at most two pages.

### Checkpoint 3 — November 24, 2026

Focus on **human-centered and responsible robotics**: pedestrian clearance/yielding, accessibility/safety behaviors, evaluation evidence, remaining risks, and final changes. Memo at most three pages.

### Final — Finals Week

Complete GitHub repository, slides and script, final report **at most seven pages**, and approximately 10-minute presentation with live or recorded demonstration plus questions.

## 9. Suggested team workstreams

1. **Environment + rendering:** Grid, objects, maps, seeded scenarios, simulation display.
2. **Planning + motion:** A*, clearance, waypoint following, route failure handling.
3. **Autonomy + perception:** Sensing, coverage, target selection, state machine, capacity/unloading.
4. **Integration + evaluation:** Tests, metrics, README, GitHub hygiene, memo, demo rehearsal.

Assign owners to suit team size; each member should understand the overall system and be able to explain the design decisions.

## 10. Open decisions

- Grid size and cell scale; 4-connected vs. 8-connected movement.
- Trash sensing radius and whether visibility can be occluded by obstacles.
- Pickup radius and simulated pickup duration.
- Bin capacity and whether different trash types have different sizes (defer initially).
- Coverage target: every reachable cell vs. sensing-based coverage of the area.
- Tie-breaking for detected litter: nearest by Euclidean distance vs. shortest planned route.
- Whether disposal station is mandatory for completion when the bin is empty.

**Recommended defaults for Checkpoint 1:** 4-connected grid, fixed sensor radius, single litter type, identical item size, bin capacity of 3, static obstacles, one disposal station, and deterministic seeded maps.

---

*Basis: CSCI 39536 Semester Robotics Project & Checkpoints handout. The course's checkpoint dates, submission rules, memo lengths and rubric weights are drawn from that document; the robot design and implementation choices above are an earlier design sketch.*
