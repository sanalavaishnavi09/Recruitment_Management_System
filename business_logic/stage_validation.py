
import sqlite3
from datetime import datetime

DB_PATH = "database/recruitment.db"

# Define allowed stage transitions
VALID_TRANSITIONS = {
    "APPLIED": ["SCREENING", "WITHDRAWN"],
    "SCREENING": ["TECHNICAL", "REJECTED", "WITHDRAWN"],
    "TECHNICAL": ["MANAGERIAL", "REJECTED", "WITHDRAWN"],
    "MANAGERIAL": ["SELECTED", "REJECTED", "WITHDRAWN"],
    "SELECTED": ["REJECTED", "WITHDRAWN"],
    "REJECTED": [],
    "WITHDRAWN": []
}


def validate_transition(current_stage, next_stage,
                        review_completed=False):

    if current_stage not in VALID_TRANSITIONS:
        return False, "Invalid current stage"

    if next_stage not in VALID_TRANSITIONS[current_stage]:
        return False, "Invalid stage transition"

    # Mandatory review gates
    if current_stage == "SCREENING" and next_stage == "TECHNICAL":
        if not review_completed:
            return False, "Screening review is incomplete"

    if current_stage == "TECHNICAL" and next_stage == "MANAGERIAL":
        if not review_completed:
            return False, "Technical review is incomplete"

    if current_stage == "MANAGERIAL" and next_stage == "SELECTED":
        if not review_completed:
            return False, "Managerial review is incomplete"

    return True, "Transition allowed"


def create_event_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS application_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT NOT NULL,
            previous_stage TEXT,
            new_stage TEXT NOT NULL,
            decision TEXT NOT NULL,
            reason TEXT,
            event_time TEXT NOT NULL
        )
    """)
    conn.commit()


def change_candidate_stage(application_id, next_stage,
                           review_completed=False):

    conn = sqlite3.connect(DB_PATH)

    try:
        create_event_table(conn)

        cursor = conn.cursor()

        cursor.execute("""
            SELECT stage
            FROM applications
            WHERE application_id = ?
        """, (application_id,))

        result = cursor.fetchone()

        if result is None:
            print("Application not found!")
            return

        current_stage = result[0]

        allowed, message = validate_transition(
            current_stage,
            next_stage,
            review_completed
        )

        decision = "APPROVED" if allowed else "REJECTED"

        cursor.execute("""
            INSERT INTO application_events
            (application_id, previous_stage, new_stage,
             decision, reason, event_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            application_id,
            current_stage,
            next_stage,
            decision,
            message,
            datetime.now().isoformat()
        ))

        if allowed:
            cursor.execute("""
                UPDATE applications
                SET stage = ?
                WHERE application_id = ?
            """, (next_stage, application_id))

        conn.commit()

        print("Application:", application_id)
        print("Previous stage:", current_stage)
        print("Requested stage:", next_stage)
        print("Decision:", decision)
        print("Reason:", message)

    finally:
        conn.close()


# Test the business logic
if __name__ == "__main__":

    print("\nTEST 1: Invalid stage transition")
    valid, message = validate_transition(
        "APPLIED", "TECHNICAL"
    )
    print(valid, message)

    print("\nTEST 2: Valid stage transition")
    valid, message = validate_transition(
        "APPLIED", "SCREENING"
    )
    print(valid, message)

    print("\nTEST 3: Missing screening review")
    valid, message = validate_transition(
        "SCREENING", "TECHNICAL", False
    )
    print(valid, message)

    print("\nTEST 4: Completed screening review")
    valid, message = validate_transition(
        "SCREENING", "TECHNICAL", True
    )
    print(valid, message)
