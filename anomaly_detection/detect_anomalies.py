
import sqlite3
import pandas as pd
import os

DB_PATH = "database/recruitment.db"

os.makedirs("data", exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

detected = []

def add_detection(entity, record_id, issue_type, decision, details):
    detected.append({
        "entity_type": entity,
        "record_id": record_id,
        "issue_type": issue_type,
        "detected_decision": decision,
        "details": details
    })


# --------------------------------------
# 1. INVALID STAGE TRANSITION
# --------------------------------------

valid_transitions = {
    "APPLIED": ["SCREENING", "WITHDRAWN"],
    "SCREENING": ["TECHNICAL", "REJECTED", "WITHDRAWN"],
    "TECHNICAL": ["MANAGERIAL", "REJECTED", "WITHDRAWN"],
    "MANAGERIAL": ["SELECTED", "REJECTED", "WITHDRAWN"],
    "SELECTED": ["REJECTED", "WITHDRAWN"],
    "REJECTED": [],
    "WITHDRAWN": []
}

events = cursor.execute("""
    SELECT application_id, previous_stage, new_stage
    FROM application_events
""").fetchall()

for app_id, old_stage, new_stage in events:

    allowed = valid_transitions.get(old_stage, [])

    if new_stage not in allowed:
        add_detection(
            "Application",
            app_id,
            "INVALID_STAGE_TRANSITION",
            "REJECT",
            f"Invalid transition: {old_stage} to {new_stage}"
        )


# --------------------------------------
# 2. INTERVIEWER DOUBLE-BOOKING
# --------------------------------------

conflicts = cursor.execute("""
    SELECT
        i1.interview_id,
        i2.interview_id,
        i1.panel_id,
        i1.interview_date,
        i1.start_time,
        i1.end_time
    FROM interviews i1
    JOIN interviews i2
      ON i1.panel_id = i2.panel_id
     AND i1.interview_date = i2.interview_date
     AND i1.interview_id > i2.interview_id
    WHERE i1.status IN ('SCHEDULED', 'RESCHEDULED')
      AND i2.status IN ('SCHEDULED', 'RESCHEDULED')
      AND i1.start_time < i2.end_time
      AND i2.start_time < i1.end_time
""").fetchall()

for new_id, old_id, panel, date, start, end in conflicts:
    add_detection(
        "Interview",
        new_id,
        "INTERVIEWER_DOUBLE_BOOKED",
        "FLAG_CONFLICT",
        f"Panel {panel} overlaps with interview {old_id}"
    )


# --------------------------------------
# 3. OFFER ABOVE SALARY BAND
# --------------------------------------

offers = cursor.execute("""
    SELECT
        o.offer_id,
        o.offered_salary_lpa,
        r.max_salary_lpa
    FROM offers o
    JOIN applications a
      ON o.application_id = a.application_id
    JOIN requisitions r
      ON a.requisition_id = r.requisition_id
    WHERE o.offered_salary_lpa > r.max_salary_lpa
""").fetchall()

for offer_id, salary, maximum in offers:
    add_detection(
        "Offer",
        offer_id,
        "OFFER_ABOVE_BAND",
        "ESCALATE",
        f"Offered {salary} LPA; maximum is {maximum} LPA"
    )


# --------------------------------------
# 4. WITHDRAWN CANDIDATE STILL SCHEDULED
# --------------------------------------

withdrawn = cursor.execute("""
    SELECT a.application_id, i.interview_id
    FROM applications a
    JOIN interviews i
      ON a.application_id = i.application_id
    WHERE a.stage = 'WITHDRAWN'
      AND i.status IN ('SCHEDULED', 'RESCHEDULED')
""").fetchall()

for app_id, interview_id in withdrawn:
    add_detection(
        "Application",
        app_id,
        "WITHDRAWN_CANDIDATE_SCHEDULED",
        "CANCEL_INTERVIEW",
        f"Interview {interview_id} remains scheduled"
    )


# --------------------------------------
# 5. IRRELEVANT SCORECARD CRITERION
# --------------------------------------

role_criteria = {
    "Python Developer": [
        "python_knowledge",
        "problem_solving",
        "communication",
        "technical_fundamentals"
    ],
    "Data Analyst": [
        "sql_knowledge",
        "data_analysis",
        "communication",
        "problem_solving"
    ],
    "AI Engineer": [
        "machine_learning",
        "python_knowledge",
        "problem_solving",
        "communication"
    ],
    "Java Developer": [
        "java_knowledge",
        "oops_concepts",
        "problem_solving",
        "communication"
    ],
    "Cloud Engineer": [
        "cloud_knowledge",
        "networking",
        "problem_solving",
        "communication"
    ]
}

criteria = cursor.execute("""
    SELECT
        sd.scorecard_id,
        sd.criterion_name,
        r.job_title
    FROM scorecard_details sd
    JOIN scorecards s
      ON sd.scorecard_id = s.scorecard_id
    JOIN interviews i
      ON s.interview_id = i.interview_id
    JOIN applications a
      ON i.application_id = a.application_id
    JOIN requisitions r
      ON a.requisition_id = r.requisition_id
""").fetchall()

for scorecard_id, criterion, role in criteria:

    allowed = role_criteria.get(role, [])

    if criterion not in allowed:
        add_detection(
            "Scorecard",
            scorecard_id,
            "IRRELEVANT_EVALUATION_CRITERION",
            "REJECT_SCORECARD",
            f"{criterion} is irrelevant for {role}"
        )


conn.close()


# --------------------------------------
# EXPORT DETECTION RESULTS
# --------------------------------------

detected_df = pd.DataFrame(detected)

detected_df.to_csv(
    "data/detected_anomalies.csv",
    index=False
)

print("\nANOMALY DETECTION RESULTS")
print("-" * 45)

for item in detected:
    print(
        item["record_id"],
        "|",
        item["issue_type"],
        "|",
        item["detected_decision"]
    )

print("-" * 45)
print("Total detected anomalies:", len(detected))


# --------------------------------------
# COMPARE WITH GROUND TRUTH
# --------------------------------------

ground_truth = pd.read_csv(
    "ground_truth/ground_truth.csv"
)

# Compare only issue type and affected record.
# Ground truth is used only after detection.

detected_keys = set(
    zip(
        detected_df["issue_type"],
        detected_df["record_id"]
    )
)

truth_keys = set(
    zip(
        ground_truth["issue_type"],
        ground_truth["record_id"]
    )
)

true_positives = len(detected_keys & truth_keys)
false_positives = len(detected_keys - truth_keys)
false_negatives = len(truth_keys - detected_keys)

precision = (
    true_positives / (true_positives + false_positives)
    if true_positives + false_positives else 0
)

recall = (
    true_positives / (true_positives + false_negatives)
    if true_positives + false_negatives else 0
)

f1 = (
    2 * precision * recall / (precision + recall)
    if precision + recall else 0
)

print("\nDETECTION EVALUATION")
print("-" * 45)
print("True positives:", true_positives)
print("False positives:", false_positives)
print("False negatives:", false_negatives)
print("Precision:", round(precision, 3))
print("Recall:", round(recall, 3))
print("F1 score:", round(f1, 3))

pd.DataFrame([{
    "true_positives": true_positives,
    "false_positives": false_positives,
    "false_negatives": false_negatives,
    "precision": precision,
    "recall": recall,
    "f1_score": f1
}]).to_csv(
    "data/detection_metrics.csv",
    index=False
)

print("\nDetection results and metrics exported!")
