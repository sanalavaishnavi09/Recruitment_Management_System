
import os
import random
import pandas as pd
import numpy as np
from faker import Faker

# Fixed seed for reproducibility
SEED = 20261022
random.seed(SEED)
np.random.seed(SEED)
fake = Faker("en_IN")
Faker.seed(SEED)

# Create output folders
os.makedirs("data", exist_ok=True)
os.makedirs("ground_truth", exist_ok=True)

# -----------------------------
# 1. HIRING MANAGERS
# -----------------------------
managers = []

for i in range(1, 51):
    managers.append({
        "manager_id": f"MGR-{i:04d}",
        "manager_name": fake.name(),
        "email": f"manager{i}@company.com",
        "department": random.choice(
            ["IT", "HR", "Finance", "Engineering", "Analytics"]
        )
    })

managers_df = pd.DataFrame(managers)

# -----------------------------
# 2. REQUISITIONS
# -----------------------------
requisitions = []

roles = [
    "Python Developer",
    "Data Analyst",
    "AI Engineer",
    "Java Developer",
    "Cloud Engineer"
]

for i in range(1, 201):
    requisitions.append({
        "requisition_id": f"REQ-2026-{i:06d}",
        "manager_id": random.choice(managers_df["manager_id"]),
        "job_title": random.choice(roles),
        "department": random.choice(
            ["IT", "Engineering", "Analytics"]
        ),
        "status": "APPROVED",
        "min_salary_lpa": random.randint(4, 6),
        "max_salary_lpa": random.randint(8, 12),
        "created_date": fake.date_between(
            start_date="-180d", end_date="today"
        ).isoformat()
    })

requisitions_df = pd.DataFrame(requisitions)

# -----------------------------
# 3. CANDIDATES
# -----------------------------
candidates = []

for i in range(1, 5001):
    candidates.append({
        "candidate_id": f"CAND-{i:06d}",
        "candidate_name": fake.name(),
        "email": f"candidate{i}@example.com",
        "experience_years": random.randint(0, 10),
        "location": fake.city(),
        "education": random.choice(
            ["B.Tech", "M.Tech", "B.Sc", "MCA", "MBA"]
        )
    })

candidates_df = pd.DataFrame(candidates)

# -----------------------------
# 4. SKILL REQUIREMENTS
# -----------------------------
skill_requirements = []

for _, req in requisitions_df.iterrows():
    for skill in random.sample(
        ["Python", "SQL", "Java", "Machine Learning",
         "AWS", "Communication", "React", "Docker"],
        3
    ):
        skill_requirements.append({
            "skill_requirement_id": f"SKILL-{len(skill_requirements)+1:05d}",
            "requisition_id": req["requisition_id"],
            "skill_name": skill,
            "minimum_level": random.randint(2, 5),
            "is_mandatory": random.choice([True, False])
        })

skills_df = pd.DataFrame(skill_requirements)

# -----------------------------
# 5. APPLICATIONS
# -----------------------------
applications = []

candidate_ids = candidates_df["candidate_id"].tolist()
req_ids = requisitions_df["requisition_id"].tolist()

for i in range(1, 8001):
    candidate_id = random.choice(candidate_ids)
    req_id = random.choice(req_ids)

    applications.append({
        "application_id": f"APP-{candidate_id}-{req_id}",
        "candidate_id": candidate_id,
        "requisition_id": req_id,
        "stage": random.choice([
            "APPLIED", "SCREENING", "TECHNICAL",
            "MANAGERIAL", "SELECTED", "REJECTED",
            "WITHDRAWN"
        ]),
        "application_date": fake.date_between(
            start_date="-150d", end_date="today"
        ).isoformat()
    })

applications_df = pd.DataFrame(applications).drop_duplicates(
    subset=["application_id"]
)

# -----------------------------
# 6. INTERVIEW PANELS
# -----------------------------
panels = []

for i in range(1, 101):
    panels.append({
        "panel_id": f"PANEL-{i:04d}",
        "panel_name": f"Interview Panel {i}",
        "department": random.choice(
            ["IT", "Engineering", "Analytics"]
        )
    })

panels_df = pd.DataFrame(panels)

# -----------------------------
# 7. AVAILABILITY
# -----------------------------

availability = []

# Generate 25 working days instead of only 5 days
available_dates = pd.bdate_range(
    start="2026-11-11",
    periods=25
)

for manager in managers:
    for date in available_dates:
        availability.append({
            "availability_id": f"AVL-{len(availability)+1:06d}",
            "manager_id": manager["manager_id"],
            "available_date": date.strftime("%Y-%m-%d"),
            "start_time": "10:00",
            "end_time": "17:00"
        })

availability_df = pd.DataFrame(availability)


# -----------------------------
# 7A. PANEL MEMBER ASSIGNMENT
# -----------------------------

# IMPORTANT:
# Use the same seed and assignment logic as
# initialize_scheduling() in scheduling.py.

panel_rng = random.Random(20261022)

panel_members = []

manager_ids = managers_df["manager_id"].tolist()

for panel_id in panels_df["panel_id"]:

    selected_managers = panel_rng.sample(
        manager_ids,
        3
    )

    for manager_id in selected_managers:
        panel_members.append({
            "panel_id": panel_id,
            "manager_id": manager_id
        })

panel_members_df = pd.DataFrame(panel_members)

# Create a lookup for fast scheduling
panel_manager_map = {}

for panel_id, group in panel_members_df.groupby("panel_id"):
    panel_manager_map[panel_id] = group["manager_id"].tolist()

print("Panel members assigned:", len(panel_members_df))


# -----------------------------
# 8. INTERVIEWS - CONFLICT-FREE GENERATION
# -----------------------------

interviews = []

eligible_apps = applications_df[
    applications_df["stage"].isin(
        ["TECHNICAL", "MANAGERIAL", "SELECTED"]
    )
]

selected_apps = eligible_apps.sample(
    n=min(2000, len(eligible_apps)),
    random_state=SEED
)

# Convert selected applications into records
pending_apps = selected_apps.to_dict("records")

random.shuffle(pending_apps)

# Seven one-hour slots per working day
time_slots = [
    "10:00", "11:00", "12:00", "13:00",
    "14:00", "15:00", "16:00"
]

panel_ids = panels_df["panel_id"].tolist()

# Create all possible panel/date/time combinations
available_slots = []

for date in available_dates:
    interview_date = date.strftime("%Y-%m-%d")

    for start_time in time_slots:

        for panel_id in panel_ids:

            available_slots.append({
                "panel_id": panel_id,
                "interview_date": interview_date,
                "start_time": start_time
            })

# Shuffle slots for balanced distribution
random.shuffle(available_slots)

# Track interviewer and candidate bookings
manager_bookings = set()
candidate_bookings = set()

for slot in available_slots:

    if not pending_apps:
        break

    panel_id = slot["panel_id"]
    interview_date = slot["interview_date"]
    start_time = slot["start_time"]

    members = panel_manager_map[panel_id]

    # Check whether any interviewer is already booked
    manager_conflict = any(
        (manager_id, interview_date, start_time)
        in manager_bookings
        for manager_id in members
    )

    if manager_conflict:
        continue

    # Find an application whose candidate is free
    app_index = None

    for index, app in enumerate(pending_apps):

        candidate_id = app["candidate_id"]

        if (
            candidate_id,
            interview_date,
            start_time
        ) not in candidate_bookings:

            app_index = index
            break

    if app_index is None:
        continue

    # Assign application
    app = pending_apps.pop(app_index)

    candidate_id = app["candidate_id"]

    # Reserve all three interviewers
    for manager_id in members:

        manager_bookings.add((
            manager_id,
            interview_date,
            start_time
        ))

    # Reserve candidate
    candidate_bookings.add((
        candidate_id,
        interview_date,
        start_time
    ))

    # Generate interview
    interview_id = f"INT-2026-{len(interviews)+1:06d}"

    interviews.append({
        "interview_id": interview_id,
        "application_id": app["application_id"],
        "panel_id": panel_id,
        "interview_date": interview_date,
        "start_time": start_time,
        "status": random.choice([
            "SCHEDULED",
            "COMPLETED",
            "RESCHEDULED",
            "CANCELLED"
        ])
    })


interviews_df = pd.DataFrame(interviews)

print("\nINTERVIEW GENERATION SUMMARY")
print("Eligible applications:", len(eligible_apps))
print("Requested interviews:", 2000)
print("Successfully scheduled:", len(interviews_df))
print("Unscheduled applications:", len(pending_apps))

if len(interviews_df) != min(2000, len(eligible_apps)):
    raise RuntimeError(
        "Could not schedule all requested interviews. "
        "Increase availability days or review panel assignments."
    )

print("Conflict-free interview generation completed!")


# -----------------------------
# 9. SCORECARDS
# -----------------------------
scorecards = []

for _, interview in interviews_df.iterrows():
    if interview["status"] == "COMPLETED":
        reviewer = random.choice(managers_df["manager_id"])
        scores = [
            random.randint(1, 5) for _ in range(3)
        ]

        scorecards.append({
            "scorecard_id": (
                f"SCORE-{interview['interview_id']}-{reviewer}"
            ),
            "interview_id": interview["interview_id"],
            "reviewer_id": reviewer,
            "technical_score": scores[0],
            "problem_solving_score": scores[1],
            "communication_score": scores[2],
            "overall_score": round(sum(scores) / 3, 2),
            "status": "SUBMITTED"
        })

scorecards_df = pd.DataFrame(scorecards)

# -----------------------------
# 10. OFFERS
# -----------------------------
offers = []

for i, (_, app) in enumerate(
    applications_df[
        applications_df["stage"] == "SELECTED"
    ].iterrows(), 1
):
    req = requisitions_df[
        requisitions_df["requisition_id"] == app["requisition_id"]
    ].iloc[0]

    salary = round(
        random.uniform(
            req["min_salary_lpa"],
            req["max_salary_lpa"]
        ), 2
    )

    offers.append({
        "offer_id": f"OFF-2026-{i:06d}",
        "application_id": app["application_id"],
        "offered_salary_lpa": salary,
        "status": "PENDING_APPROVAL"
    })

offers_df = pd.DataFrame(offers)

# -----------------------------
# 11. APPROVALS
# -----------------------------
approvals = []

for _, offer in offers_df.iterrows():
    approvals.append({
        "approval_id": f"APR-{len(approvals)+1:06d}",
        "offer_id": offer["offer_id"],
        "approver_id": random.choice(managers_df["manager_id"]),
        "decision": random.choice(
            ["APPROVED", "REJECTED", "PENDING"]
        )
    })

approvals_df = pd.DataFrame(approvals)

# -----------------------------
# EXPORT ALL DATASETS
# -----------------------------
datasets = {
    "hiring_managers": managers_df,
    "requisitions": requisitions_df,
    "candidates": candidates_df,
    "skill_requirements": skills_df,
    "applications": applications_df,
    "interview_panels": panels_df,
    "availability": availability_df,
    "interviews": interviews_df,
    "scorecards": scorecards_df,
    "offers": offers_df,
    "approvals": approvals_df
}

for name, df in datasets.items():
    df.to_csv(f"data/{name}.csv", index=False)

    # Also export JSON
    df.to_json(
        f"data/{name}.json",
        orient="records",
        indent=4
    )

print("\nDATA GENERATION COMPLETED!")
for name, df in datasets.items():
    print(f"{name}: {len(df)} records")
