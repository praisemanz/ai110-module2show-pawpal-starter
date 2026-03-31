"""
Automated test suite for PawPal+ (pawpal_system.py).

Covers:
- Task completion status
- Pet task list management
- Sorting correctness (sort_by_time)
- Recurrence logic (mark_complete with timedelta)
- Conflict detection — slot-budget overrun
- Conflict detection — exact-time overlap
- Dependency resolution in build_plan
- Edge cases: pet with no tasks, duplicate times, one-off task recurrence
"""

import pytest
from datetime import date, time, timedelta

from pawpal_system import (
    DailyPlan,
    Owner,
    Pet,
    PreferredTime,
    Priority,
    Scheduler,
    Task,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def owner():
    return Owner(name="Alex", available_start=time(7, 0), available_end=time(20, 0))


@pytest.fixture
def buddy():
    return Pet(name="Buddy", species="Dog", age=3, breed="Golden Retriever")


@pytest.fixture
def whiskers():
    return Pet(name="Whiskers", species="Cat", age=5, breed="Siamese")


def make_task(title, priority=Priority.MEDIUM, slot=None, duration=10, pet=None,
              completed=False, recurring_days=None, due_date=None, scheduled_time=None,
              depends_on=None):
    """Convenience factory so tests stay readable."""
    return Task(
        title=title,
        duration_minutes=duration,
        priority=priority,
        category="General",
        preferred_time=slot,
        pet=pet,
        completed=completed,
        recurring_days=recurring_days,
        due_date=due_date,
        scheduled_time=scheduled_time,
        depends_on=depends_on,
    )


# ---------------------------------------------------------------------------
# 1. Task completion
# ---------------------------------------------------------------------------

class TestMarkComplete:
    def test_flips_completed_to_true(self):
        task = make_task("Walk")
        assert task.completed is False
        task.mark_complete()
        assert task.completed is True

    def test_one_off_returns_none(self):
        """A task with no recurring_days should return None from mark_complete."""
        task = make_task("Walk")
        result = task.mark_complete()
        assert result is None

    def test_idempotent_on_already_completed(self):
        """Completing an already-completed task should not raise."""
        task = make_task("Walk", completed=True)
        task.mark_complete()
        assert task.completed is True


# ---------------------------------------------------------------------------
# 2. Recurrence logic
# ---------------------------------------------------------------------------

class TestRecurrence:
    def test_daily_task_spawns_next_occurrence(self):
        today = date.today()
        task = make_task("Joint Supplement", recurring_days=1, due_date=today)
        next_task = task.mark_complete()
        assert next_task is not None
        assert next_task.due_date == today + timedelta(days=1)

    def test_weekly_task_advances_by_seven_days(self):
        today = date.today()
        task = make_task("Flea Treatment", recurring_days=7, due_date=today)
        next_task = task.mark_complete()
        assert next_task.due_date == today + timedelta(days=7)

    def test_spawned_task_is_not_completed(self):
        task = make_task("Supplement", recurring_days=1, due_date=date.today())
        next_task = task.mark_complete()
        assert next_task.completed is False

    def test_spawned_task_preserves_metadata(self, buddy):
        task = make_task("Walk", priority=Priority.HIGH, slot=PreferredTime.MORNING,
                         duration=30, pet=buddy, recurring_days=1, due_date=date.today())
        next_task = task.mark_complete()
        assert next_task.title == task.title
        assert next_task.priority == Priority.HIGH
        assert next_task.preferred_time == PreferredTime.MORNING
        assert next_task.duration_minutes == 30
        assert next_task.recurring_days == 1


# ---------------------------------------------------------------------------
# 3. Pet task list
# ---------------------------------------------------------------------------

class TestPetTaskList:
    def test_add_task_increases_count(self, buddy):
        task = make_task("Feed")
        assert len(buddy.tasks) == 0
        buddy.add_task(task)
        assert len(buddy.tasks) == 1

    def test_multiple_tasks_accumulate(self, buddy):
        for i in range(3):
            buddy.add_task(make_task(f"Task {i}"))
        assert len(buddy.tasks) == 3

    def test_pet_with_no_tasks_builds_empty_plan(self, owner, buddy):
        """Edge case: a pet with zero tasks should produce a plan with no scheduled tasks."""
        sched = Scheduler(owner, buddy, [])
        plan = sched.build_plan()
        assert plan.scheduled_tasks == []
        assert plan.total_duration == 0


# ---------------------------------------------------------------------------
# 4. Sorting
# ---------------------------------------------------------------------------

class TestSortByTime:
    def test_slot_order_morning_before_afternoon_before_evening(self, owner, buddy):
        tasks = [
            make_task("Eve",  slot=PreferredTime.EVENING,   pet=buddy),
            make_task("Arvo", slot=PreferredTime.AFTERNOON, pet=buddy),
            make_task("AM",   slot=PreferredTime.MORNING,   pet=buddy),
        ]
        sched = Scheduler(owner, buddy, tasks)
        sorted_tasks = sched.sort_by_time(tasks)
        slots = [t.preferred_time for t in sorted_tasks]
        assert slots == [PreferredTime.MORNING, PreferredTime.AFTERNOON, PreferredTime.EVENING]

    def test_high_priority_before_low_within_same_slot(self, owner, buddy):
        tasks = [
            make_task("Low",  priority=Priority.LOW,  slot=PreferredTime.MORNING, pet=buddy),
            make_task("High", priority=Priority.HIGH, slot=PreferredTime.MORNING, pet=buddy),
        ]
        sched = Scheduler(owner, buddy, tasks)
        sorted_tasks = sched.sort_by_time(tasks)
        assert sorted_tasks[0].title == "High"
        assert sorted_tasks[1].title == "Low"

    def test_no_slot_tasks_fall_to_end(self, owner, buddy):
        tasks = [
            make_task("No slot", slot=None,                  pet=buddy),
            make_task("Morning", slot=PreferredTime.MORNING, pet=buddy),
        ]
        sched = Scheduler(owner, buddy, tasks)
        sorted_tasks = sched.sort_by_time(tasks)
        assert sorted_tasks[0].title == "Morning"
        assert sorted_tasks[-1].title == "No slot"

    def test_empty_list_returns_empty(self, owner, buddy):
        sched = Scheduler(owner, buddy, [])
        assert sched.sort_by_time([]) == []


# ---------------------------------------------------------------------------
# 5. Filtering
# ---------------------------------------------------------------------------

class TestFilterTasks:
    def test_filter_by_pet_name(self, owner, buddy, whiskers):
        tasks = [
            make_task("Buddy task",    pet=buddy),
            make_task("Whiskers task", pet=whiskers),
        ]
        sched = Scheduler(owner, buddy, tasks)
        result = sched.filter_tasks(tasks, pet_name="Buddy")
        assert len(result) == 1
        assert result[0].title == "Buddy task"

    def test_filter_by_completed_false(self, owner, buddy):
        tasks = [
            make_task("Done",    pet=buddy, completed=True),
            make_task("Pending", pet=buddy, completed=False),
        ]
        sched = Scheduler(owner, buddy, tasks)
        result = sched.filter_tasks(tasks, completed=False)
        assert all(not t.completed for t in result)
        assert len(result) == 1

    def test_filter_by_completed_true(self, owner, buddy):
        tasks = [
            make_task("Done",    pet=buddy, completed=True),
            make_task("Pending", pet=buddy, completed=False),
        ]
        sched = Scheduler(owner, buddy, tasks)
        result = sched.filter_tasks(tasks, completed=True)
        assert all(t.completed for t in result)

    def test_filter_is_case_insensitive(self, owner, buddy):
        tasks = [make_task("Walk", pet=buddy)]
        sched = Scheduler(owner, buddy, tasks)
        assert len(sched.filter_tasks(tasks, pet_name="buddy")) == 1
        assert len(sched.filter_tasks(tasks, pet_name="BUDDY")) == 1

    def test_completed_tasks_excluded_from_plan(self, owner, buddy):
        tasks = [make_task("Done walk", pet=buddy, completed=True, slot=PreferredTime.MORNING)]
        sched = Scheduler(owner, buddy, tasks)
        plan = sched.build_plan()
        assert plan.scheduled_tasks == []


# ---------------------------------------------------------------------------
# 6. Conflict detection — slot-budget overrun
# ---------------------------------------------------------------------------

class TestConflictSlotBudget:
    def test_no_conflict_within_budget(self, owner, buddy):
        tasks = [
            make_task("A", slot=PreferredTime.MORNING, duration=30, pet=buddy),
            make_task("B", slot=PreferredTime.MORNING, duration=30, pet=buddy),
        ]
        sched = Scheduler(owner, buddy, tasks)
        assert sched.detect_conflicts(tasks) == []

    def test_conflict_when_slot_overrun(self, owner, buddy):
        """Morning budget is 300 min; 301 min total should trigger a warning."""
        tasks = [
            make_task("Long A", slot=PreferredTime.MORNING, duration=200, pet=buddy),
            make_task("Long B", slot=PreferredTime.MORNING, duration=101, pet=buddy),
        ]
        sched = Scheduler(owner, buddy, tasks)
        warnings = sched.detect_conflicts(tasks)
        assert len(warnings) == 1
        assert "CONFLICT" in warnings[0]
        assert "Morning" in warnings[0]


# ---------------------------------------------------------------------------
# 7. Conflict detection — exact-time overlap
# ---------------------------------------------------------------------------

class TestConflictExactTime:
    def test_overlap_detected(self, owner, whiskers):
        """Vet 14:00–15:00 and Grooming 14:30–14:45 share time."""
        tasks = [
            make_task("Vet",      duration=60, pet=whiskers, scheduled_time=time(14, 0)),
            make_task("Grooming", duration=15, pet=whiskers, scheduled_time=time(14, 30)),
        ]
        sched = Scheduler(owner, whiskers, tasks)
        warnings = sched.detect_conflicts(tasks)
        assert any("OVERLAP" in w for w in warnings)

    def test_no_overlap_when_sequential(self, owner, whiskers):
        """Vet 14:00–15:00 and Grooming 15:00–15:15 are back-to-back, not overlapping."""
        tasks = [
            make_task("Vet",      duration=60, pet=whiskers, scheduled_time=time(14, 0)),
            make_task("Grooming", duration=15, pet=whiskers, scheduled_time=time(15, 0)),
        ]
        sched = Scheduler(owner, whiskers, tasks)
        warnings = sched.detect_conflicts(tasks)
        assert not any("OVERLAP" in w for w in warnings)

    def test_tasks_without_scheduled_time_not_flagged(self, owner, buddy):
        """Two tasks with no scheduled_time should never produce an OVERLAP warning."""
        tasks = [
            make_task("Walk",  slot=PreferredTime.MORNING, pet=buddy),
            make_task("Brush", slot=PreferredTime.MORNING, pet=buddy),
        ]
        sched = Scheduler(owner, buddy, tasks)
        warnings = sched.detect_conflicts(tasks)
        assert not any("OVERLAP" in w for w in warnings)

    def test_duplicate_start_times_flagged(self, owner, buddy):
        """Two tasks at exactly the same start time should overlap."""
        tasks = [
            make_task("Task A", duration=20, pet=buddy, scheduled_time=time(8, 0)),
            make_task("Task B", duration=20, pet=buddy, scheduled_time=time(8, 0)),
        ]
        sched = Scheduler(owner, buddy, tasks)
        warnings = sched.detect_conflicts(tasks)
        assert any("OVERLAP" in w for w in warnings)


# ---------------------------------------------------------------------------
# 8. Dependency resolution in build_plan
# ---------------------------------------------------------------------------

class TestDependencies:
    def test_dependent_task_scheduled_after_its_dependency(self, owner, buddy):
        walk  = make_task("Walk",  slot=PreferredTime.MORNING, pet=buddy)
        brush = make_task("Brush", slot=PreferredTime.MORNING, pet=buddy, depends_on="Walk")
        sched = Scheduler(owner, buddy, [walk, brush])
        plan = sched.build_plan()
        titles = [t.title for t in plan.scheduled_tasks]
        assert titles.index("Walk") < titles.index("Brush")

    def test_unresolvable_dependency_goes_to_rejected(self, owner, buddy):
        """A task whose dependency is never scheduled should end up in rejected_tasks."""
        brush = make_task("Brush", slot=PreferredTime.MORNING, pet=buddy, depends_on="NonExistent")
        sched = Scheduler(owner, buddy, [brush])
        plan = sched.build_plan()
        assert brush in plan.rejected_tasks
        assert brush not in plan.scheduled_tasks


# ---------------------------------------------------------------------------
# 9. Window / capacity
# ---------------------------------------------------------------------------

class TestWindowCheck:
    def test_task_rejected_when_over_window(self):
        """Owner has 60 min; two 40-min tasks means the second is rejected."""
        tight_owner = Owner(name="Jordan", available_start=time(8, 0), available_end=time(9, 0))
        pet = Pet(name="Mochi", species="Cat", age=2, breed="Mixed")
        tasks = [
            make_task("A", duration=40, slot=PreferredTime.MORNING, pet=pet, priority=Priority.HIGH),
            make_task("B", duration=40, slot=PreferredTime.MORNING, pet=pet, priority=Priority.HIGH),
        ]
        sched = Scheduler(tight_owner, pet, tasks)
        plan = sched.build_plan()
        assert len(plan.scheduled_tasks) == 1
        assert len(plan.rejected_tasks) == 1

    def test_fits_in_window_true_when_room(self, owner, buddy):
        task = make_task("Walk", duration=30, pet=buddy)
        plan = DailyPlan(date=date.today(), owner=owner, pet=buddy)
        sched = Scheduler(owner, buddy, [task])
        assert sched.fits_in_window(task, plan) is True

    def test_fits_in_window_false_when_full(self):
        tiny_owner = Owner(name="Sam", available_start=time(8, 0), available_end=time(8, 10))
        pet = Pet(name="X", species="Dog", age=1, breed="Mixed")
        existing = make_task("Fill", duration=10, pet=pet)
        plan = DailyPlan(date=date.today(), owner=tiny_owner, pet=pet,
                         scheduled_tasks=[existing])
        new_task = make_task("Extra", duration=1, pet=pet)
        sched = Scheduler(tiny_owner, pet, [])
        assert sched.fits_in_window(new_task, plan) is False
