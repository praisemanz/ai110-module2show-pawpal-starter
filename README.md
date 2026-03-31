# PawPal+ (Module 2 Project)

A smart pet care scheduling assistant built with Python and Streamlit.

## Challenge Extensions

### How Agent Mode Was Used

Agent Mode (Claude Code) was used to plan and execute multi-file changes that would have been tedious to coordinate by hand:

1. **Challenge 1 — Weighted prioritization and next-slot algorithm:** The agent was given the full `pawpal_system.py` context and asked to design a scoring formula that combined priority weight, due-date urgency, and duration penalty into a single float. It identified that the three signals needed independent caps (duration penalty bounded, future discount bounded at −2) and that the sort needed a secondary tie-breaker (slot order) to remain readable. It then added `weighted_score()` on `Task` and both `weighted_sort()` and `next_available_slot()` on `Scheduler` in a single coordinated edit, followed by updating `app.py` to expose the sort-mode toggle.

2. **Challenge 2 — Data persistence:** The agent was given the prompt: *"Add `save_to_json` and `load_from_json` methods to the `Owner` class in `pawpal_system.py`, then update `app.py` to load this data on startup."* It planned a three-layer serialization chain (`Task.to_dict` → `Pet.to_dict` → `Owner.to_dict`) to avoid the circular reference that would occur if pets serialized their tasks and tasks serialized their pets. It then updated `app.py` in four places: startup load, owner save, pet add, and task add — all in one coordinated session.

3. **Challenge 5 — Test suite edge cases:** The agent was prompted for edge cases for each feature before writing tests, producing the non-obvious scenarios listed in `reflection.md` Section 4a.

### Challenge 1: Weighted Prioritization + Next Available Slot

Two new methods were added to `Scheduler` in `pawpal_system.py`:

**`weighted_sort(tasks)`** — goes beyond simple priority ranking by computing a numeric `weighted_score()` per task that combines three signals:
- **Priority weight** (HIGH=3, MEDIUM=2, LOW=1)
- **Due-date urgency** — overdue tasks +3, due today +2, future tasks discounted by 0.1/day
- **Duration penalty** — longer tasks lose `duration_minutes / 120` points so short urgent tasks schedule first

**`next_available_slot(tasks, duration_minutes)`** — scans Morning → Afternoon → Evening and returns the first slot that still has capacity for a task of the given duration.  Shown as a hint in the UI when adding tasks.

The UI exposes both as a sort-mode radio button ("Time slot + priority" vs "Weighted score") and a hint below each task form.

### Challenge 2: Data Persistence

`Owner` now has four methods for JSON round-tripping:
- `to_dict()` / `from_dict()` — custom dict serialization (no third-party library needed)
- `save_to_json(path)` — writes owner + all pets + all tasks to `data.json`
- `load_from_json(path)` — reconstructs the full object graph; returns `None` if no file exists

The app loads `data.json` on startup and saves automatically after every "Save owner", "Add pet", and "Add task" action, so the session survives browser refreshes.

### Challenge 3 + 4: Priority Emojis and Category Icons

Every task row in the UI now shows:
- 🔴 HIGH / 🟡 MEDIUM / 🟢 LOW priority indicator
- Category icons: 🏃 Exercise, 🍽️ Feeding, 💊 Health, ✂️ Grooming, 🎾 Play, 🎓 Training, 📋 General

## Features

| Feature | How it works |
|---|---|
| **Multi-pet support** | Register any number of pets per owner session; each gets its own task pool and daily plan |
| **Priority scheduling** | Tasks are graded `LOW / MEDIUM / HIGH` using an `Enum`; `build_plan` places HIGH tasks first |
| **Sorting by time slot** | `Scheduler.sort_by_time()` orders tasks `Morning → Afternoon → Evening` using a `lambda` tuple key with `sorted()` |
| **Smart filtering** | `filter_tasks()` isolates tasks by pet name (case-insensitive) or completion status; completed tasks are never re-scheduled |
| **Conflict detection — slot budget** | Warns when the total minutes in a time slot exceed a per-slot limit (Morning: 300 min, Afternoon: 300 min, Evening: 240 min) |
| **Conflict detection — exact overlap** | For tasks with `scheduled_time` set, flags any two whose `[start, start+duration)` intervals intersect using the condition `a_start < b_end AND b_start < a_end` |
| **Recurring tasks** | Set `recurring_days` on a task; `mark_complete()` returns a new `Task` with `due_date` advanced by `timedelta(days=N)` |
| **Dependency ordering** | A task's `depends_on` field names its prerequisite; `build_plan` uses a two-pass loop to enforce sequencing |
| **Window enforcement** | `fits_in_window()` compares cumulative plan duration against the owner's available minutes; over-budget tasks go to `rejected_tasks` |
| **Table display** | `DailyPlan.display()` renders a Unicode box-drawing table with dynamic column widths, truncating long titles at 26 characters |

## 📸 Demo

*Run the app with `streamlit run app.py` and open [http://localhost:8501](http://localhost:8501).*

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Testing PawPal+

Run the full test suite with:

```bash
python -m pytest
```

**30 tests across 9 areas:**

| Group | What it verifies |
|---|---|
| `TestMarkComplete` | `completed` flips to `True`; one-off tasks return `None`; idempotent on repeat calls |
| `TestRecurrence` | Daily/weekly tasks spawn a new instance with `due_date + timedelta(days=N)`; metadata is preserved |
| `TestPetTaskList` | `add_task` grows the pet's list; a pet with no tasks produces an empty plan |
| `TestSortByTime` | Morning → Afternoon → Evening order; HIGH before LOW within a slot; unslotted tasks fall last |
| `TestFilterTasks` | Filter by pet name (case-insensitive), completion status, or both; completed tasks excluded from `build_plan` |
| `TestConflictSlotBudget` | No warning within budget; warning fires when slot total exceeds limit |
| `TestConflictExactTime` | Overlapping intervals flagged; back-to-back intervals safe; tasks without `scheduled_time` never flagged |
| `TestDependencies` | Dependent task placed after its prerequisite; unresolvable dependency goes to `rejected_tasks` |
| `TestWindowCheck` | Task rejected when it would exceed owner's window; `fits_in_window` returns correct bool |

**Confidence: ★★★★☆** — all happy paths and key edge cases are covered. The main untested area is the Streamlit UI layer (`app.py`), which requires browser interaction to test meaningfully.

## Smarter Scheduling

Phase 3 added four algorithmic improvements to `Scheduler` in `pawpal_system.py`:

**Sorting** — `sort_by_time(tasks)` orders any list of tasks by time slot (Morning → Afternoon → Evening) and then by priority (HIGH first) using a `lambda` key with `sorted()`. Tasks with no preferred time fall to the end.

**Filtering** — `filter_tasks(tasks, pet_name, completed)` returns a subset by pet name and/or completion status. `build_plan` uses this internally to skip completed tasks and tasks belonging to other pets.

**Recurring tasks** — `Task.recurring_days` sets a repeat cadence (e.g. `1` = daily). Calling `mark_complete()` on a recurring task returns a new `Task` instance whose `due_date` is advanced by `timedelta(days=recurring_days)`. The caller appends the returned task to the pool for the next day's plan.

**Conflict detection** — `detect_conflicts(tasks)` returns warning strings (never raises) for two scenarios:
- *Slot-budget overrun*: tasks in the same `PreferredTime` slot whose combined duration exceeds the per-slot limit.
- *Exact-time overlap*: any two tasks with `scheduled_time` set whose `[start, start+duration)` intervals intersect, using the condition `a_start < b_end AND b_start < a_end`.

Run `python main.py` to see all four features demonstrated in the terminal.

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
