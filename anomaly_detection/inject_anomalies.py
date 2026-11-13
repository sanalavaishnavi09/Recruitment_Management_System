
import sqlite3
import pandas as pd
import os

DB_PATH = "database/recruitment.db"
GROUND_TRUTH_PATH = "ground_truth/ground_truth.csv"

os.makedirs("ground_truth", exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Prevent accidental duplicate injection
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anomaly_injection_log (
            issue_id TEXT PRIMARY KEY,
            entity_type TEXT,
            record_id TEXT,
            original_value TEXT,
            injected_value TEXT
        )
    """)

    if cursor.execute(
        "SELECT COUNT(*) FROM anomaly_injection_log"
    ).fetchone()[0] > 0:
        raise RuntimeError(
            "Anomalies have already been injected. "
            "Restore the database before running again."
        )

    # Create normalized scorecard detail table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_details (
            detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
            scorecard_id TEXT NOT NULL,
            criterion_name TEXT NOT NULL,
            score INTEGER,
            FOREIGN KEY(scorecard_id)
                REFERENCES scorecards(scorecard_id)
        )
    """)

    ground_truth = []

    def log_anomaly(issue_id, entity, record_id,
                    issue_type, decision, description,
                    original, injected, related=None):

        cursor.execute("""
            INSERT INTO anomaly_injection_log
            VALUES (?, ?, ?, ?, ?)
        """, (
            issue_id,
            entity,
            record_id,
            str(original),
            str(injected)
        ))

        ground_truth.append({
            "issue_id": issue_id,
            "entity_type": entity,
            "record_id": record_id,
            "issue_type": issue_type,
            "expected_decision": decision,
            "description": description,
            "original_value": str(original),
            "injected_value": str(injected),
            "related_record_id": related
        })

    # -----------------------------------------
    # ANOMALY 1: INVALID STAGE TRANSITION
    # -----------------------------------------

    app = cursor.execute("""
        SELECT a.application_id, a.stage
        FROM applications a
        WHERE a.stage = 'APPLIED'
        AND NOT EXISTS (
            SELECT 1 FROM interviews i
            WHERE i.application_id = a.application_id
        )
        LIMIT 1
    """).fetchone()

    if not app:
        raise RuntimeError("No suitable application for anomaly 1")

    app_id, old_stage = app
    new_stage = "TECHNICAL"

    cursor.execute("""
        UPDATE applications
        SET stage = ?
        WHERE application_id = ?
    """, (new_stage, app_id))

    log_anomaly(
        "ANOM-2026-001",
        "Application",
        app_id,
        "INVALID_STAGE_TRANSITION",
        "REJECT",
        "Candidate moved directly from APPLIED to TECHNICAL",
        old_stage,
        new_stage
    )

    # -----------------------------------------
    # ANOMALY 2: INTERVIEWER DOUBLE-BOOKING
    # -----------------------------------------

    existing = cursor.execute("""
        SELECT interview_id, panel_id, interview_date,
               start_time, end_time
        FROM interviews
        WHERE status = 'SCHEDULED'
        LIMIT 1
    """).fetchone()

    if not existing:
        raise RuntimeError("No scheduled interview for anomaly 2")

    old_id, panel, date, start, end = existing

    second_app = cursor.execute("""
        SELECT application_id
        FROM applications a
        WHERE a.stage != 'WITHDRAWN'
        AND NOT EXISTS (
            SELECT 1 FROM interviews i
            WHERE i.application_id = a.application_id
        )
        LIMIT 1
    """).fetchone()

    if not second_app:
        raise RuntimeError("No suitable application for anomaly 2")

   
    # Generate a unique interview ID safely
    existing_ids = cursor.execute("""
        SELECT interview_id
        FROM interviews
        WHERE interview_id LIKE 'INT-2026-%'
    """).fetchall()

    numbers = [
        int(row[0].split("-")[-1])
        for row in existing_ids
    ]

    next_number = max(numbers, default=0) + 1

    new_interview_id = f"INT-2026-{next_number:06d}"

    # Insert conflicting interview
    cursor.execute("""
        INSERT INTO interviews (
            interview_id,
            application_id,
            panel_id,
            interview_date,
            start_time,
            status,
            end_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        new_interview_id,
        second_app[0],
        panel,
        date,
        start,
        "SCHEDULED",
        end
    ))

    # Verify insertion
    inserted = cursor.execute("""
        SELECT interview_id
        FROM interviews
        WHERE interview_id = ?
    """, (new_interview_id,)).fetchone()

    if not inserted:
        raise RuntimeError("Interview insertion failed")

    print("Interview inserted:", new_interview_id)


    log_anomaly(
        "ANOM-2026-002",
        "Interview",
        new_interview_id,
        "INTERVIEWER_DOUBLE_BOOKED",
        "FLAG_CONFLICT",
        "Two interviews use the same panel at overlapping times",
        "No conflicting interview",
        f"{date} {start}-{end}",
        old_id
    )

    # -----------------------------------------
    # ANOMALY 3: OFFER EXCEEDS SALARY BAND
    # -----------------------------------------

    offer = cursor.execute("""
        SELECT o.offer_id, o.offered_salary_lpa,
               r.max_salary_lpa
        FROM offers o
        JOIN applications a
          ON o.application_id = a.application_id
        JOIN requisitions r
          ON a.requisition_id = r.requisition_id
        WHERE o.status = 'PENDING_APPROVAL'
        LIMIT 1
    """).fetchone()

    if not offer:
        raise RuntimeError("No pending offer for anomaly 3")

    offer_id, old_salary, max_salary = offer
    new_salary = round(max_salary + 1, 2)

    cursor.execute("""
        UPDATE offers
        SET offered_salary_lpa = ?
        WHERE offer_id = ?
    """, (new_salary, offer_id))

    log_anomaly(
        "ANOM-2026-003",
        "Offer",
        offer_id,
        "OFFER_ABOVE_BAND",
        "ESCALATE",
        "Offered salary exceeds the approved maximum",
        old_salary,
        new_salary
    )

    # -----------------------------------------
    # ANOMALY 4: WITHDRAWN CANDIDATE SCHEDULED
    # -----------------------------------------

    withdrawn = cursor.execute("""
        SELECT a.application_id, a.stage, i.interview_id
        FROM applications a
        JOIN interviews i
          ON a.application_id = i.application_id
        WHERE a.stage != 'WITHDRAWN'
        AND i.status = 'SCHEDULED'
        LIMIT 1
    """).fetchone()

    if not withdrawn:
        raise RuntimeError("No suitable record for anomaly 4")

    withdrawn_app, old_stage, interview_id = withdrawn

    cursor.execute("""
        UPDATE applications
        SET stage = 'WITHDRAWN'
        WHERE application_id = ?
    """, (withdrawn_app,))

    log_anomaly(
        "ANOM-2026-004",
        "Application",
        withdrawn_app,
        "WITHDRAWN_CANDIDATE_SCHEDULED",
        "CANCEL_INTERVIEW",
        "Withdrawn candidate still has a scheduled interview",
        old_stage,
        "WITHDRAWN",
        interview_id
    )

    # -----------------------------------------
    # ANOMALY 5: IRRELEVANT SCORECARD CRITERION
    # -----------------------------------------

    scorecard = cursor.execute("""
        SELECT scorecard_id
        FROM scorecards
        LIMIT 1
    """).fetchone()

    if not scorecard:
        raise RuntimeError("No scorecard available for anomaly 5")

    scorecard_id = scorecard[0]

    cursor.execute("""
        INSERT INTO scorecard_details (
            scorecard_id, criterion_name, score
        )
        VALUES (?, ?, ?)
    """, (
        scorecard_id,
        "cooking_skills",
        5
    ))

    log_anomaly(
        "ANOM-2026-005",
        "Scorecard",
        scorecard_id,
        "IRRELEVANT_EVALUATION_CRITERION",
        "REJECT_SCORECARD",
        "Cooking skills is irrelevant to the technical evaluation",
        "No cooking_skills criterion",
        "cooking_skills:5"
    )

    # Commit all changes together
    conn.commit()

    # Export separate ground truth
    pd.DataFrame(ground_truth).to_csv(
        GROUND_TRUTH_PATH,
        index=False
    )

    print("\nANOMALY INJECTION COMPLETED")
    print("-" * 45)

    for item in ground_truth:
        print(
            item["issue_id"],
            "|",
            item["issue_type"],
            "|",
            item["expected_decision"]
        )

    print("-" * 45)
    print("Total anomalies injected:", len(ground_truth))
    print("Ground truth saved:", GROUND_TRUTH_PATH)

except Exception:
    conn.rollback()
    raise

finally:
    conn.close()
