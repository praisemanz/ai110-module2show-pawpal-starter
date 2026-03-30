from datetime import date, time

from pawpal_system import DailyPlan, Owner, Pet, PreferredTime, Priority, Task

# --- Create Pets ---
buddy = Pet(
    name="Buddy",
    species="Dog",
    age=3,
    breed="Golden Retriever",
    special_needs=["joint supplements"],
)

whiskers = Pet(
    name="Whiskers",
    species="Cat",
    age=5,
    breed="Siamese",
    special_needs=["hairball control"],
)

# --- Create Owner ---
owner = Owner(
    name="Alex",
    available_start=time(7, 0),
    available_end=time(20, 0),
    pets=[buddy, whiskers],
)

# --- Create Tasks (three different preferred times) ---
morning_walk = Task(
    title="Morning Walk",
    duration_minutes=30,
    priority=Priority.HIGH,
    category="Exercise",
    preferred_time=PreferredTime.MORNING,
    pet=buddy,
)

buddy_feeding = Task(
    title="Feed Buddy",
    duration_minutes=10,
    priority=Priority.HIGH,
    category="Feeding",
    preferred_time=PreferredTime.MORNING,
    pet=buddy,
)

evening_playtime = Task(
    title="Evening Playtime",
    duration_minutes=20,
    priority=Priority.MEDIUM,
    category="Play",
    preferred_time=PreferredTime.EVENING,
    pet=buddy,
)

whiskers_feeding = Task(
    title="Feed Whiskers",
    duration_minutes=5,
    priority=Priority.HIGH,
    category="Feeding",
    preferred_time=PreferredTime.MORNING,
    pet=whiskers,
)

afternoon_grooming = Task(
    title="Afternoon Grooming",
    duration_minutes=15,
    priority=Priority.MEDIUM,
    category="Grooming",
    preferred_time=PreferredTime.AFTERNOON,
    pet=whiskers,
)

vet_checkup = Task(
    title="Vet Check-up",
    duration_minutes=60,
    priority=Priority.HIGH,
    category="Health",
    preferred_time=PreferredTime.AFTERNOON,
    pet=whiskers,
)

# --- Build Daily Plans ---
today = date.today()

buddy_plan = DailyPlan(date=today, owner=owner, pet=buddy, task_pool=[morning_walk, buddy_feeding, evening_playtime])
for task in [morning_walk, buddy_feeding, evening_playtime]:
    buddy_plan.add_task(task)

whiskers_plan = DailyPlan(date=today, owner=owner, pet=whiskers, task_pool=[whiskers_feeding, afternoon_grooming, vet_checkup])
for task in [whiskers_feeding, afternoon_grooming, vet_checkup]:
    whiskers_plan.add_task(task)

# --- Print Today's Schedule ---
TITLE = "PawPal+ — Today's Schedule"
WIDTH = 67
print("=" * WIDTH)
print(f"{TITLE:^{WIDTH}}")
print("=" * WIDTH)
print()
print(buddy_plan.display())
print()
print(whiskers_plan.display())
print()
print("=" * WIDTH)
