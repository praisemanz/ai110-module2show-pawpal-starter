from datetime import date, time, timedelta

from pawpal_system import Owner, Pet, PreferredTime, Priority, Scheduler, Task

WIDTH = 67


def section(title: str) -> None:
    print(f"\n{'─' * WIDTH}")
    print(f"  {title}")
    print(f"{'─' * WIDTH}")


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
buddy = Pet(name="Buddy", species="Dog", age=3, breed="Golden Retriever",
            special_needs=["joint supplements"])
whiskers = Pet(name="Whiskers", species="Cat", age=5, breed="Siamese",
               special_needs=["hairball control"])

owner = Owner(name="Alex", available_start=time(7, 0), available_end=time(20, 0),
              pets=[buddy, whiskers])

# ---------------------------------------------------------------------------
# Tasks added INTENTIONALLY OUT OF ORDER (proves sorting works)
# Two tasks given exact scheduled_time values that overlap (proves conflict detection)
# ---------------------------------------------------------------------------
all_tasks = [
    # Evening task first
    Task("Evening Playtime",   20, Priority.MEDIUM, "Play",     PreferredTime.EVENING,   buddy),
    # Afternoon tasks
    Task("Vet Check-up",       60, Priority.HIGH,   "Health",   PreferredTime.AFTERNOON, whiskers,
         scheduled_time=time(14, 0)),
    Task("Afternoon Grooming", 15, Priority.MEDIUM, "Grooming", PreferredTime.AFTERNOON, whiskers,
         scheduled_time=time(14, 30)),   # ← starts during Vet Check-up → overlap!
    # Morning tasks last
    Task("Morning Walk",       30, Priority.HIGH,   "Exercise", PreferredTime.MORNING,   buddy,
         scheduled_time=time(7, 0)),
    Task("Feed Buddy",         10, Priority.HIGH,   "Feeding",  PreferredTime.MORNING,   buddy,
         scheduled_time=time(7, 45)),
    Task("Feed Whiskers",       5, Priority.HIGH,   "Feeding",  PreferredTime.MORNING,   whiskers),
    # Recurring daily task
    Task("Joint Supplement",    5, Priority.HIGH,   "Health",   PreferredTime.MORNING,   buddy,
         recurring_days=1, due_date=date.today()),
    # Dependency: brush teeth only after morning walk
    Task("Brush Teeth",         5, Priority.LOW,    "Grooming", PreferredTime.MORNING,   buddy,
         depends_on="Morning Walk"),
    # Already-completed task (filtered out of the plan)
    Task("Yesterday's Walk",   30, Priority.HIGH,   "Exercise", PreferredTime.MORNING,   buddy,
         completed=True),
]

sched_buddy    = Scheduler(owner, buddy,    all_tasks)
sched_whiskers = Scheduler(owner, whiskers, all_tasks)

# ---------------------------------------------------------------------------
# 1. Raw order
# ---------------------------------------------------------------------------
section("1. RAW ORDER  (tasks as entered — deliberately scrambled)")
for t in all_tasks:
    status = "✓" if t.completed else "○"
    recur  = f"  [every {t.recurring_days}d]" if t.recurring_days else ""
    dep    = f"  (after: {t.depends_on})"     if t.depends_on    else ""
    clk    = f"  @{t.scheduled_time}"         if t.scheduled_time else ""
    print(f"  {status} {t.summary()}{recur}{dep}{clk}")

# ---------------------------------------------------------------------------
# 2. Sorted by time slot + priority
# ---------------------------------------------------------------------------
section("2. SORTED BY TIME  (slot: AM → Afternoon → PM, then priority)")
print()
for t in sched_buddy.sort_by_time(all_tasks):
    slot = t.preferred_time.value if t.preferred_time else "none"
    print(f"    [{slot:12s}] {t.priority.value:6s}  {t.title}")

# ---------------------------------------------------------------------------
# 3. Filtering
# ---------------------------------------------------------------------------
section("3. FILTERING")

pending_buddy = sched_buddy.filter_tasks(all_tasks, pet_name="Buddy", completed=False)
print(f"\n  Pending tasks for Buddy ({len(pending_buddy)}):")
for t in pending_buddy:
    print(f"    - {t.title}")

done_tasks = sched_buddy.filter_tasks(all_tasks, completed=True)
print(f"\n  Completed tasks ({len(done_tasks)}):")
for t in done_tasks:
    print(f"    - {t.title}")

whiskers_tasks = sched_buddy.filter_tasks(all_tasks, pet_name="Whiskers")
print(f"\n  All Whiskers tasks ({len(whiskers_tasks)}):")
for t in whiskers_tasks:
    print(f"    - {t.title}")

# ---------------------------------------------------------------------------
# 4. Recurring task — mark complete, auto-spawn next occurrence
# ---------------------------------------------------------------------------
section("4. RECURRING TASKS  (mark_complete + timedelta)")

supplement = next(t for t in all_tasks if t.title == "Joint Supplement")
print(f"\n  Before: '{supplement.title}'  due={supplement.due_date}  completed={supplement.completed}")

next_task = supplement.mark_complete()
print(f"  After:  '{supplement.title}'  completed={supplement.completed}")

if next_task:
    print(f"  Spawned: '{next_task.title}'  due={next_task.due_date}  "
          f"(= today + {supplement.recurring_days}d via timedelta)")
    all_tasks.append(next_task)

# ---------------------------------------------------------------------------
# 5. Conflict detection
# ---------------------------------------------------------------------------
section("5. CONFLICT DETECTION")

print("\n  a) Slot-budget overrun (add a 280-min afternoon task for Buddy):")
conflict_pool = all_tasks + [
    Task("Long Afternoon Run", 280, Priority.MEDIUM, "Exercise", PreferredTime.AFTERNOON, buddy),
]
for w in sched_buddy.detect_conflicts(
    sched_buddy.filter_tasks(conflict_pool, pet_name="Buddy", completed=False)
) or ["  (none)"]:
    print(f"    ⚠  {w}")

print("\n  b) Exact-time overlap (Vet Check-up 14:00–15:00 vs Grooming 14:30–14:45):")
for w in sched_whiskers.detect_conflicts(
    sched_whiskers.filter_tasks(all_tasks, pet_name="Whiskers", completed=False)
) or ["  (none)"]:
    print(f"    ⚠  {w}")

# ---------------------------------------------------------------------------
# 6. Build plans via Scheduler (sorting + filtering + window + dependencies)
# ---------------------------------------------------------------------------
section("6. GENERATED SCHEDULE  (Scheduler.build_plan)")

buddy_plan    = sched_buddy.build_plan()
whiskers_plan = sched_whiskers.build_plan()

SCHEDULE_TITLE = "PawPal+ — Today's Schedule"
print()
print("=" * WIDTH)
print(f"{SCHEDULE_TITLE:^{WIDTH}}")
print("=" * WIDTH)
print()
print(buddy_plan.display())
if buddy_plan.rejected_tasks:
    print(f"  Rejected (over window): {', '.join(t.title for t in buddy_plan.rejected_tasks)}")
print()
print(whiskers_plan.display())
if whiskers_plan.rejected_tasks:
    print(f"  Rejected (over window): {', '.join(t.title for t in whiskers_plan.rejected_tasks)}")
print()
print("=" * WIDTH)
