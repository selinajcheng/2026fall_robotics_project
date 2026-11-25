# Sidewalk Trash Collection Robot

CSCI 39536 team project. Run `python main.py` for the integrated four-block simulation: an autonomous robot collects trash while pedestrians move between buildings and cars obey traffic signals. The display shows collection progress, status, a simulated clock, an event log, and a map legend.

## File guide


| File                                                                                 | What it is                                                       | How to use it                                                                     |
| ------------------------------------------------------------------------------------ | ---------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| [README.md](README.md)                                                               | Entry point and file guide                                       | Start here when opening the repository.                                           |
| [requirements.txt](requirements.txt)                                                 | Shared Python dependency versions                                | Install inside a virtual environment on each laptop.                              |
| [main.py](main.py)                                                                   | Integrated autonomous demo and status display                   | **This is the file to run:** `python main.py`.                                    |
| [robot.py](robot.py)                                                                 | Robot position and movement along waypoints                     | Used by both demos.                                                               |
| [navigation.py](navigation.py)                                                       | A* pathfinding for the separate open-area demo                  | Used by `robot_demo.py`.                                                          |
| [robot_demo.py](robot_demo.py)                                                       | Separate navigation prototype with moving pedestrians           | Run `python robot_demo.py` to try click-to-route or manual movement.               |
| [icons.py](icons.py)                                                                 | Pygame icons for robot, trash, station, people, and obstacles    | Used by `main.py` and its legend.                                                  |
| [sim/world.py](sim/world.py)                                                         | Bounded grid and legal-move checks                               | Defines the city's walkable cells.                                                |
| [sim/scene.py](sim/scene.py)                                                         | The map data: blocks, roads, crosswalks, buildings               | Edit `BLOCK_LAYOUTS` to move or resize buildings.                                 |
| [sim/render.py](sim/render.py)                                                       | Background drawing: colors, sidewalks, buildings, road paint     | Edit to change the city background.                                                |
| [sim/pedestrian_grid.py](sim/pedestrian_grid.py)                                       | Pedestrian movement and building trips                          | Uses the active doors defined by `sim/scene.py`.                                   |
| [sim/pedestrian_schedule.py](sim/pedestrian_schedule.py)                               | Time-based pedestrian arrivals                                  | Controls the daytime cohorts.                                                      |
| [sim/traffic.py](sim/traffic.py)                                                       | Cars and crossing signals                                       | Coordinates vehicle and pedestrian crossing permissions.                          |
| [sim/litter.py](sim/litter.py)                                                         | Trash dropped by pedestrians                                    | Adds litter during a run.                                                          |
| [sim/interaction.py](sim/interaction.py)                                               | Pedestrian trash handoffs                                       | Lets a nearby person give trash to the robot.                                      |
| [sim/grid_navigation.py](sim/grid_navigation.py)                                     | Reachability, nearest-target search, and A* on sidewalk cells    | Used by the integrated demo.                                                      |
| [sim/collection.py](sim/collection.py)                                               | Trash sensing, pickup, capacity, and unloading                   | Used by the integrated demo.                                                      |
| [tests/test_collection.py](tests/test_collection.py)                                 | Collection and grid-navigation unit tests                       | Run `python -m unittest discover -s tests -v`.                                    |
| [docs/project_specifications.pdf](docs/project_specifications.pdf)                   | Instructor's semester-project handout                            | Authoritative for course deadlines, submission rules, memo lengths, and grading.  |
| [docs/copy_of_shared_google_doc.md](docs/copy_of_shared_google_doc.md)               | Selina's copy of the team-call notes and assigned pre-demo tasks | Source of truth for who is doing what and the team's initial task list.           |
| [docs/SPEC.md](docs/SPEC.md)                                                         | Checkpoint 1 behavior and integration specification              | Read as the baseline for later work.                                               |
| [docs/VISUAL_ENVIRONMENT_SPEC.md](docs/VISUAL_ENVIRONMENT_SPEC.md)                   | Selina's visual environment requirements                         | Use as the target for any change to how the scene looks.                          |
| [docs/reference/generated_city_blocks.png](docs/reference/generated_city_blocks.png) | Visual reference image                                           | Target style for rooftops, sidewalks, and road paint.                             |
| [docs/SPEC_IDEATION.md](docs/SPEC_IDEATION.md)                                       | Earlier LLM-assisted concept draft                               | Reference for possible later features; it does not set Checkpoint 1 requirements. |


When the documents differ, follow the course handout for course obligations and the team notes for assigned tasks. `docs/SPEC.md` records the Checkpoint 1 baseline; the current code and run instructions below describe the newer demo.

Record scene-specific values, such as sensor range and grid size, alongside the code that uses them.

**Folder layout.** `main.py`, `robot.py`, `navigation.py`, `robot_demo.py`, and `icons.py` are at the top level. City-specific world, navigation, and collection code lives in `sim/`; documents live in `docs/`. Follow the existing imports when adding modules.

```
main.py            integrated demo; run this
robot.py           shared robot movement
navigation.py      open-area A* for robot_demo.py
robot_demo.py      separate navigation prototype
icons.py           integrated demo icons
requirements.txt
sim/               city, pedestrians, traffic, litter, navigation, collection
tests/             collection, pedestrian, traffic, and trash-layout tests
docs/              specs, team notes, course handout, reference image
```



## 1. Set up once

Install 64-bit Python 3.12 and Git. Then open a terminal in the folder where you keep projects.

**Clone the repository and switch to** `dev`**:**

```sh
git clone https://github.com/selinajcheng/2026fall_robotics_project.git
cd 2026fall_robotics_project
git switch dev
```

Run the remaining commands inside `2026fall_robotics_project`. 

**Create a virtual environment and install dependencies on macOS/Linux:**

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**Or create it on Windows PowerShell:**

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**Check the installation** with the active environment:

```sh
python -c "import pygame; print(pygame.version.ver)"
```

It should print `2.6.1`. If PowerShell blocks activation, run `.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.venv\Scripts\python.exe -c "import pygame; print(pygame.version.ver)"` instead. On macOS/Linux, use your Python 3.12 executable to create `.venv` if `python3` points to a different version.

## 2. Start each work session

Open a terminal in your cloned `2026fall_robotics_project` folder. Everyone works on `dev`.

**Check for local changes:**

```sh
git status --short
```

If this prints files, finish or commit your work before pulling. Ask the team about changes you do not recognize.

**Switch to** `dev` **and get the latest work:**

```sh
git switch dev
git pull --ff-only origin dev
```

**Activate the existing environment** (choose your operating system):

```sh
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Do not recreate `.venv` each time. If `requirements.txt` changed after the pull, run `python -m pip install -r requirements.txt`. If PowerShell blocks activation, use `.venv\Scripts\python.exe` in place of `python`. Run `deactivate` when you finish using an activated environment.

## 3. Save and share your changes

**Review your changes:**

```sh
git status --short
git diff --check
git diff
```

**Stage, check, commit, and push to** `dev`**:**

```sh
git add README.md
git diff --cached
git commit -m "Describe the change"
git push origin dev
```

Replace `README.md` with the files you changed. Stage only your intended changes. `.venv` is ignored by Git and stays on your laptop. Tell the team after you push so they can pull your work.

## 4. Run the integrated demo

Run `main.py` from the project folder after installing the dependencies.

1. Open a terminal in your `2026fall_robotics_project` folder.
2. Activate the virtual environment (macOS/Linux `source .venv/bin/activate`; Windows PowerShell `.venv\Scripts\Activate.ps1`).
3. Run:

```sh
python main.py
```

A window opens showing the city and the robot moving autonomously. Press **Space** to pause, **Up/Down** to change speed, **C** for seed and speed configuration, **R** to restart with the current seed, or **Esc** to quit. On Windows, if activation is blocked, run `.venv\Scripts\python.exe main.py` instead. On WSL, the window needs WSLg (included in current Windows 11 and recent Windows 10 builds).

**Save a picture without opening a window** (useful for the memo and for checking a change):

```sh
python main.py --screenshot out.png
```

**What you will see.** An aerial view of four long blocks around one unpainted intersection, styled after [docs/reference/generated_city_blocks.png](docs/reference/generated_city_blocks.png). The city has 416 walkable sidewalk and crosswalk cells. Gold-framed door marks identify the 23 buildings with direct sidewalk entrances; two interior buildings do not have an active entrance. Pedestrians fade out through those marked doors, walk through the city, and enter a different marked building. Rush-hour trips favor more distant buildings, while lunch and afternoon trips favor nearer ones. A seed reproduces the same door choices and trash layout.

**Show the building flow.** Set a seed in the **C** configuration screen, then use **Up** to speed toward the 8:45 AM morning cohort. Watch people leave marked doors and enter different marked buildings. Press **R** to repeat the same seeded run, or choose another seed to compare a different set of building trips.

**Robot behavior.** The robot starts at `(1, 1)`, senses trash within two cells by Manhattan distance, and collects an item when it reaches its cell. Undetected trash is red; detected trash is green. It visits reachable cells, prioritizes detected trash, and uses A* routes around pedestrians. Its bin holds eight items. When full, it goes to the station at `(1, 2)`, unloads, and resumes. Cars follow traffic lights; the robot and pedestrians wait for safe crossing signals. Pedestrians can drop new litter or hand trash to the robot. The panel shows collection progress, status, and bin fill; a run's metrics are appended to `simulation_metrics.csv` when the robot first completes its sweep.

**Map facts.** 36 columns by 24 rows, 28-pixel tiles, coordinates `(column, row)` from the top-left `(0, 0)`. Seven starting trash cells are randomized per seed; marked door cells are reserved so trash does not hide an entrance.

**Separate navigation prototype.** Run `python robot_demo.py` for the older open-area robot demo. Click a destination to route around obstacles, or use the arrow or WASD keys for manual movement.

**Run the unit tests:**

```sh
python -m unittest discover -s tests -v
```

**Changing the look.** Building positions are in `BLOCK_LAYOUTS` in `sim/scene.py`; colors and drawing are in `sim/render.py`. Keep buildings inside their lot so the walkable cells do not change. Git keeps the history, so edit these files in place rather than copying them.
