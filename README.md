# Sidewalk Trash Collection Robot

CSCI 39536 team project. The repository currently contains planning documents and Python dependency setup; the Python/Pygame simulation has not been added yet.

## File guide


| File                                                           | What it is                                                       | How to use it                                                                     |
| -------------------------------------------------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `[README.md](README.md)`                                       | Entry point and file guide                                       | Start here when opening the repository.                                           |
| `[requirements.txt](requirements.txt)`                         | Shared Python dependency versions                                | Install inside a virtual environment on each laptop.                              |
| `[project_specifications.pdf](project_specifications.pdf)`     | Instructor's semester-project handout                            | Authoritative for course deadlines, submission rules, memo lengths, and grading.  |
| `[copy_of_shared_google_doc.md](copy_of_shared_google_doc.md)` | Selina's copy of the team-call notes and assigned pre-demo tasks | Source of truth for who is doing what and the team's initial task list.           |
| `[SPEC.md](SPEC.md)`                                           | Current working behavior and integration specification           | Use for the Checkpoint 1 demo scope and robot behavior.                           |
| `[SPEC_IDEATION.md](SPEC_IDEATION.md)`                         | Earlier LLM-assisted concept draft                               | Reference for possible later features; it does not set Checkpoint 1 requirements. |


When the documents differ, follow the course handout for course obligations, the team notes for assigned tasks, and the working spec for robot behavior. The immediate demo goal is an autonomous sweep of reachable sidewalk, trash detection, and collection while avoiding static obstacles and people. Bin capacity and unloading are optional for Checkpoint 1.

Record scene-specific values, such as sensor range and grid size, alongside the code that uses them.

## 1. Set up once

Install 64-bit Python 3.12 and Git. Then open a terminal in the folder where you keep projects.

**Clone the repository and switch to `dev`:**

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

**Switch to `dev` and get the latest work:**

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

**Stage, check, commit, and push to `dev`:**

```sh
git add README.md
git diff --cached
git commit -m "Describe the change"
git push origin dev
```

Replace `README.md` with the files you changed. Stage only your intended changes. `.venv` is ignored by Git and stays on your laptop. Tell the team after you push so they can pull your work.

## Run the simulation

The simulation entry point has not been added yet. Once the team creates it, this section will give the exact launch command and expected behavior. For now, the import check above verifies the shared dependency setup.