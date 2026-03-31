# PawPal+ (Module 2 Project)

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
