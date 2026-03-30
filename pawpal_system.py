from dataclasses import dataclass, field
from datetime import date, time
from typing import List, Optional


@dataclass
class Pet:
    """Represents a pet with basic info and special needs."""
    name: str
    species: str
    age: int
    breed: str
    special_needs: List[str] = field(default_factory=list)

    def get_profile(self) -> str:
        """Returns a summary string of the pet's details."""
        pass

    def has_special_need(self, need: str) -> bool:
        """Checks whether a specific need is listed."""
        pass


@dataclass
class Owner:
    """Represents the pet owner with availability and preferences."""
    name: str
    available_start: time
    available_end: time
    preferences: dict = field(default_factory=dict)

    def get_available_minutes(self) -> int:
        """Computes total minutes free in the day."""
        pass

    def add_preference(self, key: str, value) -> None:
        """Stores a scheduling preference."""
        pass


@dataclass
class Task:
    """Represents a pet care task."""
    title: str
    duration_minutes: int
    priority: str  # "low", "medium", "high"
    category: str  # e.g., "walk", "feeding", "medication"
    preferred_time: Optional[str] = None  # "morning", "afternoon", "evening", or None

    def is_high_priority(self) -> bool:
        """Returns True if priority is 'high'."""
        pass

    def summary(self) -> str:
        """Returns a one-line description of the task."""
        pass


@dataclass
class DailyPlan:
    """Represents a daily schedule of tasks for a pet."""
    date: date
    owner: Owner
    pet: Pet
    scheduled_tasks: List[Task] = field(default_factory=list)
    total_duration: int = 0

    def add_task(self, task: Task) -> None:
        """Appends a task and updates total duration."""
        pass

    def display(self) -> str:
        """Formats the plan as a readable list."""
        pass

    def explain(self) -> str:
        """Narrates why each task was included and in what order."""
        pass


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
