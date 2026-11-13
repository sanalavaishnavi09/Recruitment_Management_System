
import sqlite3
import pandas as pd

DB_PATH = "database/recruitment.db"
GT_PATH = "ground_truth/ground_truth.csv"

conn = sqlite3.connect(DB_PATH)

ground_truth = pd.read_csv(GT_PATH)

print("\n========== ANOMALY DATABASE DEBUG ==========")

for _, row in ground_truth.iterrows():

    issue = row["issue_type"]
    record_id = row["record_id"]
    related_id = row.get("related_record_id")

    print(f"\nANOMALY: {issue}")
    print("Record ID:", record_id)

    if issue == "INVALID_STAGE_TRANSITION":

        result = conn.execute("""
            SELECT application_id, stage
            FROM applications
            WHERE application_id = ?
        """, (record_id,)).fetchall()

        events = conn.execute("""
            SELECT *
            FROM application_events
            WHERE application_id = ?
        """, (record_id,)).fetchall()

        print("Application:", result)
        print("Events:", events)

    elif issue == "INTERVIEWER_DOUBLE_BOOKED":

        result = conn.execute("""
            SELECT interview_id, panel_id,
                   interview_date, start_time,
                   end_time, status
            FROM interviews
            WHERE interview_id IN (?, ?)
        """, (record_id, related_id)).fetchall()

        print("Conflicting interviews:", result)

        members = conn.execute("""
            SELECT pm.panel_id, pm.manager_id
            FROM panel_members pm
            WHERE pm.panel_id IN (
                SELECT panel_id
                FROM interviews
                WHERE interview_id IN (?, ?)
            )
        """, (record_id, related_id)).fetchall()

        print("Panel members:", members)

    elif issue == "OFFER_ABOVE_BAND":

        result = conn.execute("""
            SELECT o.offer_id,
                   o.offered_salary_lpa,
                   r.max_salary_lpa
            FROM offers o
            JOIN applications a
              ON o.application_id = a.application_id
            JOIN requisitions r
              ON a.requisition_id = r.requisition_id
            WHERE o.offer_id = ?
        """, (record_id,)).fetchall()

        print("Offer details:", result)

    elif issue == "WITHDRAWN_CANDIDATE_SCHEDULED":

        result = conn.execute("""
            SELECT a.application_id,
                   a.stage,
                   i.interview_id,
                   i.status
            FROM applications a
            JOIN interviews i
              ON a.application_id = i.application_id
            WHERE a.application_id = ?
        """, (record_id,)).fetchall()

        print("Application and interviews:", result)

    elif issue == "IRRELEVANT_EVALUATION_CRITERION":

        result = conn.execute("""
            SELECT scorecard_id, criterion_name, score
            FROM scorecard_details
            WHERE scorecard_id = ?
        """, (record_id,)).fetchall()

        print("Scorecard details:", result)

conn.close()

print("\n========== DEBUG COMPLETED ==========")
