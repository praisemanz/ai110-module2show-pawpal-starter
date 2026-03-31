import streamlit as st
from datetime import date, time
from pawpal_system import Owner, Pet, Task, Priority, PreferredTime, DailyPlan, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling — sorted, filtered, and conflict-aware.")

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
PRIORITY_EMOJI = {Priority.HIGH: "🔴", Priority.MEDIUM: "🟡", Priority.LOW: "🟢"}

CATEGORY_ICON = {
    "exercise": "🏃", "walk": "🏃", "feeding": "🍽️", "feed": "🍽️",
    "health": "💊", "medication": "💊", "grooming": "✂️", "play": "🎾",
    "training": "🎓", "general": "📋",
}

def category_icon(category: str) -> str:
    return CATEGORY_ICON.get(category.lower(), "📋")

DATA_FILE = "data.json"
PRIORITY_MAP  = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH}
SLOT_MAP = {
    "morning": PreferredTime.MORNING,
    "afternoon": PreferredTime.AFTERNOON,
    "evening": PreferredTime.EVENING,
    "none": None,
}

# ---------------------------------------------------------------------------
# Session state vault — try to restore from data.json on first run
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    saved = Owner.load_from_json(DATA_FILE)
    st.session_state.owner = saved          # None if file doesn't exist yet

if "pets" not in st.session_state:
    if st.session_state.owner and st.session_state.owner.pets:
        st.session_state.pets = st.session_state.owner.pets
    else:
        st.session_state.pets = []

# ---------------------------------------------------------------------------
# SECTION 1 — Owner Setup
# ---------------------------------------------------------------------------
st.subheader("1. Owner Setup")

with st.form("owner_form"):
    default_name = st.session_state.owner.name if st.session_state.owner else "Jordan"
    default_start = st.session_state.owner.available_start if st.session_state.owner else time(7, 0)
    default_end   = st.session_state.owner.available_end   if st.session_state.owner else time(20, 0)
    owner_name  = st.text_input("Your name", value=default_name)
    col_a, col_b = st.columns(2)
    with col_a:
        avail_start = st.time_input("Available from", value=default_start)
    with col_b:
        avail_end = st.time_input("Available until", value=default_end)
    submitted_owner = st.form_submit_button("Save owner")

if submitted_owner:
    st.session_state.owner = Owner(
        name=owner_name,
        available_start=avail_start,
        available_end=avail_end,
        pets=st.session_state.pets,
    )
    st.session_state.owner.save_to_json(DATA_FILE)
    st.success(f"Owner saved and persisted: **{owner_name}** ({avail_start.strftime('%H:%M')} – {avail_end.strftime('%H:%M')})")

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
    if st.session_state.owner:
        st.session_state.owner.pets = st.session_state.pets
        st.session_state.owner.save_to_json(DATA_FILE)
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

        # Challenge 1 — suggest the best slot before adding
        dummy_owner = st.session_state.owner or Owner("_", time(0, 0), time(23, 59))
        sched = Scheduler(dummy_owner, target_pet, target_pet.tasks)
        suggested_slot = sched.next_available_slot(target_pet.tasks, int(duration))
        if time_slot_str == "none":
            st.info(f"💡 No slot selected — best available slot for {int(duration)} min: **{suggested_slot}**")

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
        if st.session_state.owner:
            st.session_state.owner.pets = st.session_state.pets
            st.session_state.owner.save_to_json(DATA_FILE)
        recur_note = f" (repeats every {int(recurring_days)}d)" if recurring_days > 0 else ""
        st.success(f"Task '{task_title}' added to {target_pet.name}{recur_note}.")

    # Sort toggle
    sort_mode = st.radio(
        "Sort tasks by:",
        ["Time slot + priority", "Weighted score (urgency)"],
        horizontal=True,
    )

    for pet in st.session_state.pets:
        if not pet.tasks:
            continue

        dummy_owner = st.session_state.owner or Owner("_", time(0, 0), time(23, 59))
        sched = Scheduler(dummy_owner, pet, pet.tasks)

        if sort_mode == "Weighted score (urgency)":
            display_tasks = sched.weighted_sort(pet.tasks)
            sort_label = "weighted urgency score"
        else:
            display_tasks = sched.sort_by_time(pet.tasks)
            sort_label = "time slot + priority"

        st.markdown(f"**{pet.name}'s tasks** *(sorted by {sort_label})*")

        rows = []
        for t in display_tasks:
            emoji = PRIORITY_EMOJI.get(t.priority, "")
            icon  = category_icon(t.category)
            score_str = f"{t.weighted_score():.1f}" if sort_mode == "Weighted score (urgency)" else "—"
            rows.append({
                "": f"{emoji} {icon}",
                "Task": t.title,
                "Priority": f"{emoji} {t.priority.value.upper()}",
                "Slot": t.preferred_time.value.capitalize() if t.preferred_time else "Any",
                "Duration": f"{t.duration_minutes} min",
                "Recurring": f"every {t.recurring_days}d" if t.recurring_days else "one-off",
                "Score": score_str,
                "Done": "✓" if t.completed else "○",
            })
        st.table(rows)

        # Conflict warnings
        pending = sched.filter_tasks(pet.tasks, completed=False)
        for w in sched.detect_conflicts(pending):
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
    use_weighted = st.checkbox("Use weighted prioritization (urgency-aware)", value=False)

    if st.button("Generate schedule"):
        owner = st.session_state.owner
        st.markdown(f"### Schedule for {date.today().strftime('%A, %B %d %Y')}")

        for pet in st.session_state.pets:
            if not pet.tasks:
                continue

            sched = Scheduler(owner, pet, pet.tasks)
            pending = sched.filter_tasks(pet.tasks, completed=False)

            # Run conflict detection first
            for c in sched.detect_conflicts(pending):
                st.warning(f"⚠ **Conflict for {pet.name}:** {c}")

            # Next available slot hint
            slot_hint = sched.next_available_slot(pending, 30)
            st.caption(f"💡 Next available 30-min slot for {pet.name}: **{slot_hint}**")

            plan = sched.build_plan()
            st.markdown(f"#### 🐾 {pet.name}")

            if not plan.scheduled_tasks:
                st.info(f"No pending tasks for {pet.name}.")
                continue

            # Apply weighted sort for display if requested
            display_tasks = (
                sched.weighted_sort(plan.scheduled_tasks) if use_weighted
                else plan.scheduled_tasks
            )

            rows = []
            for i, t in enumerate(display_tasks, 1):
                emoji = PRIORITY_EMOJI.get(t.priority, "")
                icon  = category_icon(t.category)
                rows.append({
                    "#": i,
                    "": f"{emoji} {icon}",
                    "Task": t.title,
                    "Priority": f"{emoji} {t.priority.value.upper()}",
                    "Slot": t.preferred_time.value.capitalize() if t.preferred_time else "Any",
                    "Duration": f"{t.duration_minutes} min",
                    "Score": f"{t.weighted_score():.1f}" if use_weighted else "—",
                    "Recurring": f"every {t.recurring_days}d" if t.recurring_days else "—",
                })
            st.table(rows)
            st.success(
                f"Total scheduled: **{plan.total_duration} min** "
                f"of {owner.get_available_minutes()} min available"
            )

            if plan.rejected_tasks:
                st.warning(
                    f"Not scheduled (would exceed daily window): "
                    f"{', '.join(t.title for t in plan.rejected_tasks)}"
                )

            # Mark recurring tasks complete
            recurring = [t for t in plan.scheduled_tasks if t.recurring_days]
            if recurring:
                st.markdown("**Mark recurring tasks complete:**")
                for t in recurring:
                    if st.button(f"✓ Done: {t.title}", key=f"complete_{pet.name}_{t.title}"):
                        next_task = t.mark_complete()
                        if next_task:
                            pet.add_task(next_task)
                            st.success(
                                f"'{t.title}' marked done. "
                                f"Next occurrence added for {next_task.due_date}."
                            )
                        else:
                            st.success(f"'{t.title}' marked complete.")
                        if st.session_state.owner:
                            st.session_state.owner.save_to_json(DATA_FILE)
