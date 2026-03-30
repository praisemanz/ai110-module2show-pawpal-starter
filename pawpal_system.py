from dataclasses import dataclass, field
from datetime import date, time
from typing import List, Optional
from enum import Enum


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

    def mark_complete(self) -> None:
        """Marks the task as completed."""
        self.completed = True

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

    def __init__(self, owner: Owner, pet: Pet, task_pool: List[Task]):
        """Initialize the scheduler with owner, pet, and available tasks."""
        self.owner = owner
        self.pet = pet
        self.task_pool = task_pool

    def build_plan(self) -> DailyPlan:
        """Selects and orders tasks that fit within the owner's time window."""
        pass

    def fits_in_window(self, task: Task, plan: DailyPlan) -> bool:
        """Checks if adding the task would exceed available time."""
        pass
