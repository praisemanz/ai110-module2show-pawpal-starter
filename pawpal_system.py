from dataclasses import dataclass, field
from datetime import date, time, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
import json
import os


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PreferredTime(Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


@dataclass
class Pet:
    """Represents a pet with basic info and special needs."""
    name: str
    species: str
    age: int
    breed: str
    special_needs: List[str] = field(default_factory=list)
    tasks: List = field(default_factory=list)

    def add_task(self, task) -> None:
        """Adds a task to this pet's task list."""
        self.tasks.append(task)

    def get_profile(self) -> str:
        """Returns a summary string of the pet's details."""
        needs = ", ".join(self.special_needs) if self.special_needs else "none"
        return f"{self.name} ({self.species}, {self.breed}, age {self.age}) | Special needs: {needs}"

    def has_special_need(self, need: str) -> bool:
        """Checks whether a specific need is listed."""
        return need in self.special_needs

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this Pet (without its tasks) to a plain dict."""
        return {
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "breed": self.breed,
            "special_needs": self.special_needs,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pet":
        """Reconstruct a Pet from a serialized dict.

        Tasks are deserialized as Task objects with ``pet`` set to this
        instance after construction (to avoid a forward-reference cycle).
        """
        pet = cls(
            name=data["name"],
            species=data["species"],
            age=data["age"],
            breed=data["breed"],
            special_needs=data.get("special_needs", []),
        )
        for t_data in data.get("tasks", []):
            task = Task(
                title=t_data["title"],
                duration_minutes=t_data["duration_minutes"],
                priority=Priority(t_data["priority"]),
                category=t_data["category"],
                preferred_time=PreferredTime(t_data["preferred_time"]) if t_data.get("preferred_time") else None,
                pet=pet,
                depends_on=t_data.get("depends_on"),
                completed=t_data.get("completed", False),
                recurring_days=t_data.get("recurring_days"),
                due_date=date.fromisoformat(t_data["due_date"]) if t_data.get("due_date") else None,
                scheduled_time=time.fromisoformat(t_data["scheduled_time"]) if t_data.get("scheduled_time") else None,
            )
            pet.tasks.append(task)
        return pet


@dataclass
class Owner:
    """Represents the pet owner with availability and preferences."""
    name: str
    available_start: time
    available_end: time
    preferences: dict = field(default_factory=dict)
    pets: List[Pet] = field(default_factory=list)

    def get_available_minutes(self) -> int:
        """Computes total minutes free in the day."""
        start = self.available_start.hour * 60 + self.available_start.minute
        end = self.available_end.hour * 60 + self.available_end.minute
        return end - start

    def add_preference(self, key: str, value) -> None:
        """Stores a scheduling preference."""
        self.preferences[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this Owner and all its pets to a plain dict."""
        return {
            "name": self.name,
            "available_start": self.available_start.strftime("%H:%M"),
            "available_end": self.available_end.strftime("%H:%M"),
            "preferences": self.preferences,
            "pets": [p.to_dict() for p in self.pets],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Owner":
        """Reconstruct an Owner (and its pets) from a serialized dict."""
        owner = cls(
            name=data["name"],
            available_start=time.fromisoformat(data["available_start"]),
            available_end=time.fromisoformat(data["available_end"]),
            preferences=data.get("preferences", {}),
        )
        owner.pets = [Pet.from_dict(p) for p in data.get("pets", [])]
        return owner

    def save_to_json(self, path: str = "data.json") -> None:
        """Persist the owner and all pets/tasks to a JSON file.

        The file is written atomically by serializing to a string first,
        then writing in a single call, so a crash mid-write does not
        produce a truncated file.

        Args:
            path: File path to write (default ``data.json``).
        """
        payload = self.to_dict()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

    @classmethod
    def load_from_json(cls, path: str = "data.json") -> Optional["Owner"]:
        """Load an Owner from a JSON file created by ``save_to_json``.

        Returns ``None`` (rather than raising) if the file does not exist,
        so callers can use the return value as a simple existence check::

            owner = Owner.load_from_json()
            if owner is None:
                owner = Owner(...)   # first-run default

        Args:
            path: File path to read (default ``data.json``).

        Returns:
            A reconstructed ``Owner`` instance, or ``None``.
        """
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)


@dataclass
class Task:
    """Represents a pet care task."""
    title: str
    duration_minutes: int
    priority: Priority
    category: str
    preferred_time: Optional[PreferredTime] = None
    pet: Optional[Pet] = None
    depends_on: Optional[str] = None  # title of the task that must run before this one
    completed: bool = False
    recurring_days: Optional[int] = None  # repeat every N days; None = one-off
    due_date: Optional[date] = None        # explicit due date; defaults to today when None
    scheduled_time: Optional[time] = None  # exact clock time for overlap detection

    def mark_complete(self) -> Optional["Task"]:
        """Mark this task complete.

        If the task is recurring (``recurring_days`` is set), a new Task is
        returned with ``due_date`` advanced by ``recurring_days`` days using
        ``timedelta`` and ``completed`` reset to ``False``.  The caller is
        responsible for adding the returned task to the relevant pool.

        Returns:
            A new Task for the next occurrence, or ``None`` for one-off tasks.
        """
        self.completed = True
        if self.recurring_days is None:
            return None
        next_due = (self.due_date or date.today()) + timedelta(days=self.recurring_days)
        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            category=self.category,
            preferred_time=self.preferred_time,
            pet=self.pet,
            depends_on=self.depends_on,
            completed=False,
            recurring_days=self.recurring_days,
            due_date=next_due,
        )

    def weighted_score(self) -> float:
        """Compute a numeric urgency score for weighted prioritization.

        The score combines three signals:
        - **Priority weight** (HIGH=3, MEDIUM=2, LOW=1) — the dominant factor.
        - **Due-date urgency** — tasks due today score +2; overdue tasks score
          +3; tasks due in the future are discounted by 0.1 per remaining day
          (capped at -2 so distant tasks never go negative on this component).
        - **Duration penalty** — longer tasks score slightly lower so that
          equally-urgent short tasks are scheduled first and leave more room
          in the window.  The penalty is ``duration_minutes / 120`` (so a
          60-min task loses 0.5 points).

        Returns:
            A float where higher means "schedule this sooner."
        """
        priority_weight = {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1}
        score = float(priority_weight.get(self.priority, 1))

        today = date.today()
        due = self.due_date or today
        days_until = (due - today).days
        if days_until < 0:
            score += 3.0          # overdue
        elif days_until == 0:
            score += 2.0          # due today
        else:
            score += max(-2.0, -0.1 * days_until)  # future discount

        score -= self.duration_minutes / 120.0      # duration penalty
        return score

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this Task to a plain dict for JSON storage."""
        return {
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority.value,
            "category": self.category,
            "preferred_time": self.preferred_time.value if self.preferred_time else None,
            "pet_name": self.pet.name if self.pet else None,
            "depends_on": self.depends_on,
            "completed": self.completed,
            "recurring_days": self.recurring_days,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "scheduled_time": self.scheduled_time.strftime("%H:%M") if self.scheduled_time else None,
        }

    def is_high_priority(self) -> bool:
        """Returns True if priority is HIGH."""
        return self.priority == Priority.HIGH

    def summary(self) -> str:
        """Returns a one-line description of the task."""
        pet_name = self.pet.name if self.pet else "Unassigned"
        time_pref = self.preferred_time.value.capitalize() if self.preferred_time else "Anytime"
        return f"[{self.priority.value.upper()}] {self.title} ({self.duration_minutes} min | {time_pref}) — {pet_name}"


@dataclass
class DailyPlan:
    """Represents a daily schedule of tasks for a pet."""
    date: date
    owner: Owner
    pet: Pet
    task_pool: List[Task] = field(default_factory=list)
    scheduled_tasks: List[Task] = field(default_factory=list)
    rejected_tasks: List[Task] = field(default_factory=list)

    @property
    def total_duration(self) -> int:
        """Computed total duration of all scheduled tasks in minutes."""
        return sum(t.duration_minutes for t in self.scheduled_tasks)

    def add_task(self, task: Task) -> None:
        """Appends a task to scheduled_tasks."""
        self.scheduled_tasks.append(task)

    def display(self) -> str:
        """Formats the plan as a compact Unicode table."""
        SLOT = {
            PreferredTime.MORNING: "AM",
            PreferredTime.AFTERNOON: "Afternoon",
            PreferredTime.EVENING: "PM",
        }
        MAX_TITLE = 26

        rows = []
        for i, task in enumerate(self.scheduled_tasks, 1):
            title = task.title[:MAX_TITLE - 1] + "…" if len(task.title) > MAX_TITLE else task.title
            slot = SLOT.get(task.preferred_time, "Any") if task.preferred_time else "Any"
            rows.append((str(i), task.priority.value.upper(), title, f"{task.duration_minutes} min", slot))

        headers = ("#", "Pri", "Task", "Time", "Slot")
        widths = [
            max(len(headers[c]), max((len(r[c]) for r in rows), default=0))
            for c in range(5)
        ]

        def row_line(cells):
            return "│" + "│".join(f" {c:<{w}} " for c, w in zip(cells, widths)) + "│"

        top = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐"
        mid = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
        bot = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘"

        lines = [
            f"[{self.pet.name}]  Owner: {self.owner.name}   Date: {self.date}",
            top,
            row_line(headers),
            mid,
            *[row_line(r) for r in rows],
            bot,
            f"Total: {self.total_duration} min",
        ]
        return "\n".join(lines)

    def explain(self) -> str:
        """Narrates why each task was included and in what order."""
        lines = [f"Explanation for {self.pet.name}'s plan:"]
        for task in self.scheduled_tasks:
            reason = "high priority" if task.is_high_priority() else f"{task.priority.value} priority"
            lines.append(f"  - '{task.title}' scheduled because it is {reason}.")
        return "\n".join(lines)


class Scheduler:
    """Manages the scheduling logic for creating daily plans."""

    # Canonical slot order: used as a sort key so tasks flow MORNING→AFTERNOON→EVENING.
    _SLOT_ORDER = {PreferredTime.MORNING: 0, PreferredTime.AFTERNOON: 1, PreferredTime.EVENING: 2}
    # Priority order: HIGH tasks scheduled before MEDIUM before LOW.
    _PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
    # Maximum minutes budgeted per slot (used for conflict detection).
    _SLOT_BUDGET = {PreferredTime.MORNING: 300, PreferredTime.AFTERNOON: 300, PreferredTime.EVENING: 240}

    def __init__(self, owner: Owner, pet: Pet, task_pool: List[Task]):
        """Initialize the scheduler with owner, pet, and available tasks."""
        self.owner = owner
        self.pet = pet
        self.task_pool = task_pool

    # Slot start/end times in minutes from midnight — used by next_available_slot.
    _SLOT_WINDOWS = {
        PreferredTime.MORNING:   (7 * 60,  12 * 60),
        PreferredTime.AFTERNOON: (12 * 60, 17 * 60),
        PreferredTime.EVENING:   (17 * 60, 21 * 60),
    }

    # ------------------------------------------------------------------
    # Weighted prioritization (Challenge 1)
    # ------------------------------------------------------------------
    def weighted_sort(self, tasks: List[Task]) -> List[Task]:
        """Return tasks sorted by ``Task.weighted_score()`` descending.

        This goes beyond simple priority ranking by incorporating due-date
        urgency and duration penalty into a single numeric score.  Overdue
        HIGH tasks rise to the top; distant LOW tasks sink to the bottom.
        Ties within the same score are broken by slot order so the result
        is still readable as a day-flow.

        Args:
            tasks: Any list of ``Task`` objects.

        Returns:
            A new list sorted highest-score-first.
        """
        return sorted(
            tasks,
            key=lambda t: (
                -t.weighted_score(),                           # primary: score descending
                self._SLOT_ORDER.get(t.preferred_time, 3),    # secondary: slot order
            ),
        )

    def next_available_slot(self, tasks: List[Task], duration_minutes: int) -> Optional[str]:
        """Find the earliest time slot that can fit a new task of the given duration.

        Scans Morning → Afternoon → Evening.  For each slot it computes how
        many minutes are already consumed by pending tasks in that slot and
        returns the first slot where the remaining capacity is >= the
        requested duration.

        Args:
            tasks:            The current pending task list for this pet.
            duration_minutes: How long the new task will take.

        Returns:
            The slot label (e.g. ``"Morning"``) if one fits, or
            ``"No available slot"`` if every slot is full.
        """
        from collections import defaultdict
        slot_used: Dict = defaultdict(int)
        for t in tasks:
            if not t.completed:
                slot_used[t.preferred_time] += t.duration_minutes

        for slot in (PreferredTime.MORNING, PreferredTime.AFTERNOON, PreferredTime.EVENING):
            start, end = self._SLOT_WINDOWS[slot]
            capacity = end - start
            if slot_used[slot] + duration_minutes <= capacity:
                return slot.value.capitalize()

        return "No available slot"

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------
    def sort_by_time(self, tasks: List[Task]) -> List[Task]:
        """Return tasks sorted by slot (AM→PM→Eve) then by priority (HIGH first).

        Uses a lambda key so tasks with no preferred_time fall to the end.
        """
        return sorted(
            tasks,
            key=lambda t: (
                self._SLOT_ORDER.get(t.preferred_time, 3),   # None slots go last
                self._PRIORITY_ORDER.get(t.priority, 99),
            ),
        )

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------
    def filter_tasks(
        self,
        tasks: List[Task],
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> List[Task]:
        """Return a filtered subset of tasks.

        Args:
            pet_name:  keep only tasks whose pet.name matches (case-insensitive).
            completed: True → only done tasks; False → only pending tasks; None → all.
        """
        result = tasks
        if pet_name is not None:
            result = [t for t in result if t.pet and t.pet.name.lower() == pet_name.lower()]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        return result

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------
    def detect_conflicts(self, tasks: List[Task]) -> List[str]:
        """Return warning strings for two categories of conflict.

        1. **Slot-budget overrun** — tasks in the same ``PreferredTime`` slot
           whose combined duration exceeds the per-slot budget defined in
           ``_SLOT_BUDGET``.  This is a lightweight heuristic: it detects
           over-scheduled slots without needing exact clock times.

        2. **Exact-time overlap** — any two tasks that both have a
           ``scheduled_time`` set and whose ``[start, start+duration)``
           intervals overlap.  Overlap condition (half-open intervals)::

               a.start < b.end  AND  b.start < a.end

           A warning string is returned rather than raising an exception so
           the caller can decide how to handle (skip, warn, reorder).

        Args:
            tasks: The list of ``Task`` objects to check.

        Returns:
            A (possibly empty) list of human-readable warning strings.
        """
        from collections import defaultdict
        warnings: List[str] = []

        # --- 1. Per-slot budget check ---
        slot_minutes: dict = defaultdict(int)
        slot_tasks: dict = defaultdict(list)
        for t in tasks:
            slot_minutes[t.preferred_time] += t.duration_minutes
            slot_tasks[t.preferred_time].append(t.title)

        for slot, total in slot_minutes.items():
            budget = self._SLOT_BUDGET.get(slot, 999)
            if total > budget:
                label = slot.value.capitalize() if slot else "Unslotted"
                warnings.append(
                    f"CONFLICT [{label}]: {total} min scheduled vs {budget} min budget "
                    f"({', '.join(slot_tasks[slot])})"
                )

        # --- 2. Exact-time overlap check ---
        # Only tasks with an explicit scheduled_time participate; others are skipped.
        timed = [t for t in tasks if t.scheduled_time is not None]
        for i, a in enumerate(timed):
            a_start = a.scheduled_time.hour * 60 + a.scheduled_time.minute
            a_end   = a_start + a.duration_minutes
            for b in timed[i + 1:]:
                b_start = b.scheduled_time.hour * 60 + b.scheduled_time.minute
                b_end   = b_start + b.duration_minutes
                if a_start < b_end and b_start < a_end:
                    warnings.append(
                        f"OVERLAP: '{a.title}' "
                        f"({a.scheduled_time.strftime('%H:%M')}–"
                        f"{a_end // 60:02d}:{a_end % 60:02d}) "
                        f"overlaps '{b.title}' "
                        f"({b.scheduled_time.strftime('%H:%M')}–"
                        f"{b_end // 60:02d}:{b_end % 60:02d})"
                    )

        return warnings

    # ------------------------------------------------------------------
    # Window check
    # ------------------------------------------------------------------
    def fits_in_window(self, task: Task, plan: DailyPlan) -> bool:
        """Return True if adding task keeps total duration within owner's available minutes."""
        return plan.total_duration + task.duration_minutes <= self.owner.get_available_minutes()

    # ------------------------------------------------------------------
    # Build plan
    # ------------------------------------------------------------------
    def build_plan(self) -> DailyPlan:
        """Build a DailyPlan by sorting pending tasks, honouring depends_on, and respecting the time window."""
        plan = DailyPlan(date=date.today(), owner=self.owner, pet=self.pet, task_pool=self.task_pool)

        # Only schedule incomplete tasks for this pet.
        pending = self.filter_tasks(self.task_pool, pet_name=self.pet.name, completed=False)
        ordered = self.sort_by_time(pending)

        # Two-pass dependency resolution: tasks whose dependency isn't yet scheduled
        # are deferred to a second pass rather than skipped entirely.
        scheduled_titles: set = set()
        deferred: List[Task] = []

        for task in ordered:
            if task.depends_on and task.depends_on not in scheduled_titles:
                deferred.append(task)
                continue
            if self.fits_in_window(task, plan):
                plan.add_task(task)
                scheduled_titles.add(task.title)
            else:
                plan.rejected_tasks.append(task)

        for task in deferred:
            if task.depends_on in scheduled_titles and self.fits_in_window(task, plan):
                plan.add_task(task)
                scheduled_titles.add(task.title)
            else:
                plan.rejected_tasks.append(task)

        return plan
