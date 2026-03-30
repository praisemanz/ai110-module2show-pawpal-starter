import pytest
from pawpal_system import Pet, Task, Priority, PreferredTime


def test_mark_complete_changes_status():
    """Calling mark_complete() should flip completed from False to True."""
    task = Task(
        title="Morning Walk",
        duration_minutes=30,
        priority=Priority.HIGH,
        category="Exercise",
    )
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a pet should increase its task list by one."""
    pet = Pet(name="Buddy", species="Dog", age=3, breed="Golden Retriever")
    task = Task(
        title="Feed Buddy",
        duration_minutes=10,
        priority=Priority.HIGH,
        category="Feeding",
    )
    assert len(pet.tasks) == 0
    pet.add_task(task)
    assert len(pet.tasks) == 1
