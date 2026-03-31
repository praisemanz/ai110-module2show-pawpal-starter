import streamlit as st
from datetime import date, time
from pawpal_system import Owner, Pet, Task, Priority, PreferredTime, DailyPlan, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling — sorted, filtered, and conflict-aware.")

# ---------------------------------------------------------------------------
# Session state vault
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None
if "pets" not in st.session_state:
    st.session_state.pets = []

# ---------------------------------------------------------------------------
# SECTION 1 — Owner Setup
# ---------------------------------------------------------------------------
st.subheader("1. Owner Setup")

with st.form("owner_form"):
    owner_name = st.text_input("Your name", value="Jordan")
    col_a, col_b = st.columns(2)
    with col_a:
        avail_start = st.time_input("Available from", value=time(7, 0))
    with col_b:
        avail_end = st.time_input("Available until", value=time(20, 0))
    submitted_owner = st.form_submit_button("Save owner")

if submitted_owner:
    st.session_state.owner = Owner(
        name=owner_name,
        available_start=avail_start,
        available_end=avail_end,
    )
    st.success(f"Owner saved: **{owner_name}** ({avail_start.strftime('%H:%M')} – {avail_end.strftime('%H:%M')})")

if st.session_state.owner:
    o = st.session_state.owner
    st.caption(
        f"Current owner: **{o.name}** | "
        f"Available {o.available_start.strftime('%H:%M')}–{o.available_end.strftime('%H:%M')} "
        f"({o.get_available_minutes()} min free)"
    )

st.divider()

# ---------------------------------------------------------------------------
# SECTION 2 — Add a Pet
# ---------------------------------------------------------------------------
st.subheader("2. Add a Pet")

with st.form("pet_form"):
    pet_name = st.text_input("Pet name", value="Mochi")
    col1, col2, col3 = st.columns(3)
    with col1:
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "other"])
    with col2:
        breed = st.text_input("Breed", value="Mixed")
    with col3:
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
    special_needs_input = st.text_input("Special needs (comma-separated)", value="")
    submitted_pet = st.form_submit_button("Add pet")

if submitted_pet:
    special_needs = [s.strip() for s in special_needs_input.split(",") if s.strip()]
    new_pet = Pet(name=pet_name, species=species, breed=breed, age=age, special_needs=special_needs)
    st.session_state.pets.append(new_pet)
    st.success(f"Pet added: {new_pet.get_profile()}")

if st.session_state.pets:
    st.caption("Pets in this session:")
    for p in st.session_state.pets:
        st.markdown(f"- {p.get_profile()}")

st.divider()

# ---------------------------------------------------------------------------
# SECTION 3 — Add Tasks
# ---------------------------------------------------------------------------
st.subheader("3. Add Tasks")

PRIORITY_MAP = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH}
SLOT_MAP = {
    "morning": PreferredTime.MORNING,
    "afternoon": PreferredTime.AFTERNOON,
    "evening": PreferredTime.EVENING,
    "none": None,
}

if not st.session_state.pets:
    st.info("Add at least one pet above before adding tasks.")
else:
    pet_names = [p.name for p in st.session_state.pets]

    with st.form("task_form"):
        selected_pet_name = st.selectbox("Assign to pet", pet_names)
        col1, col2 = st.columns(2)
        with col1:
            task_title    = st.text_input("Task title", value="Morning walk")
            duration      = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
            category      = st.text_input("Category", value="General")
        with col2:
            priority_str  = st.selectbox("Priority", ["low", "medium", "high"], index=2)
            time_slot_str = st.selectbox("Preferred time", ["morning", "afternoon", "evening", "none"])
            recurring_days = st.number_input("Repeat every N days (0 = one-off)", min_value=0, max_value=365, value=0)
        submitted_task = st.form_submit_button("Add task")

    if submitted_task:
        target_pet = next(p for p in st.session_state.pets if p.name == selected_pet_name)
        new_task = Task(
            title=task_title,
            duration_minutes=int(duration),
            priority=PRIORITY_MAP[priority_str],
            category=category,
            preferred_time=SLOT_MAP[time_slot_str],
            pet=target_pet,
            recurring_days=int(recurring_days) if recurring_days > 0 else None,
            due_date=date.today(),
        )
        target_pet.add_task(new_task)
        recur_note = f" (repeats every {int(recurring_days)}d)" if recurring_days > 0 else ""
        st.success(f"Task '{task_title}' added to {target_pet.name}{recur_note}.")

    # Show each pet's task list — sorted by slot + priority via Scheduler
    for pet in st.session_state.pets:
        if not pet.tasks:
            continue

        dummy_owner = st.session_state.owner or Owner("_", time(0, 0), time(23, 59))
        sched = Scheduler(dummy_owner, pet, pet.tasks)
        sorted_tasks = sched.sort_by_time(pet.tasks)

        st.markdown(f"**{pet.name}'s tasks** *(sorted by time slot, then priority)*")

        rows = []
        for t in sorted_tasks:
            rows.append({
                "Task": t.title,
                "Priority": t.priority.value.upper(),
                "Slot": t.preferred_time.value.capitalize() if t.preferred_time else "Any",
                "Duration": f"{t.duration_minutes} min",
                "Recurring": f"every {t.recurring_days}d" if t.recurring_days else "one-off",
                "Done": "✓" if t.completed else "○",
            })
        st.table(rows)

        # Conflict warnings for this pet's tasks
        pending = sched.filter_tasks(pet.tasks, completed=False)
        warnings = sched.detect_conflicts(pending)
        if warnings:
            for w in warnings:
                st.warning(f"⚠ {w}")

st.divider()

# ---------------------------------------------------------------------------
# SECTION 4 — Generate Schedule
# ---------------------------------------------------------------------------
st.subheader("4. Generate Schedule")

if not st.session_state.owner:
    st.info("Save an owner first (Section 1).")
elif not st.session_state.pets:
    st.info("Add at least one pet first (Section 2).")
elif not any(p.tasks for p in st.session_state.pets):
    st.info("Add at least one task first (Section 3).")
else:
    if st.button("Generate schedule"):
        owner = st.session_state.owner
        st.markdown(f"### Schedule for {date.today().strftime('%A, %B %d %Y')}")

        for pet in st.session_state.pets:
            if not pet.tasks:
                continue

            sched = Scheduler(owner, pet, pet.tasks)

            # Run conflict detection before displaying the plan
            pending = sched.filter_tasks(pet.tasks, completed=False)
            conflicts = sched.detect_conflicts(pending)
            if conflicts:
                for c in conflicts:
                    st.warning(f"⚠ **Conflict for {pet.name}:** {c}")

            plan = sched.build_plan()

            st.markdown(f"#### 🐾 {pet.name}")

            if not plan.scheduled_tasks:
                st.info(f"No pending tasks for {pet.name}.")
                continue

            # Render scheduled tasks as a styled table
            rows = []
            for i, t in enumerate(plan.scheduled_tasks, 1):
                rows.append({
                    "#": i,
                    "Task": t.title,
                    "Priority": t.priority.value.upper(),
                    "Slot": t.preferred_time.value.capitalize() if t.preferred_time else "Any",
                    "Duration": f"{t.duration_minutes} min",
                    "Recurring": f"every {t.recurring_days}d" if t.recurring_days else "—",
                })
            st.table(rows)
            st.success(f"Total scheduled: **{plan.total_duration} min** of {owner.get_available_minutes()} min available")

            # Show rejected tasks if any
            if plan.rejected_tasks:
                rejected_titles = ", ".join(t.title for t in plan.rejected_tasks)
                st.warning(f"Not scheduled (would exceed daily window): {rejected_titles}")

            # Mark-complete controls — one button per recurring task
            recurring = [t for t in plan.scheduled_tasks if t.recurring_days]
            if recurring:
                st.markdown("**Mark recurring tasks complete:**")
                for t in recurring:
                    btn_key = f"complete_{pet.name}_{t.title}"
                    if st.button(f"✓ Done: {t.title}", key=btn_key):
                        next_task = t.mark_complete()
                        if next_task:
                            pet.add_task(next_task)
                            st.success(
                                f"'{t.title}' marked done. Next occurrence added for {next_task.due_date}."
                            )
                        else:
                            st.success(f"'{t.title}' marked complete.")
