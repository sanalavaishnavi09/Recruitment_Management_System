
import sqlite3
from datetime import datetime

DB_PATH = "database/recruitment_test.db"


# ---------------------------------------
# 1. CREATE APPROVAL HISTORY TABLE
# ---------------------------------------

def initialize_approval_system():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS offer_approval_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id TEXT NOT NULL,
            approver_id TEXT,
            decision TEXT NOT NULL,
            comments TEXT,
            approval_time TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

    print("Approval history table created!")


# ---------------------------------------
# 2. VALIDATE SALARY BAND
# ---------------------------------------

def validate_salary(offer_id):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    record = cursor.execute("""
        SELECT
            o.offered_salary_lpa,
            r.min_salary_lpa,
            r.max_salary_lpa
        FROM offers o
        JOIN applications a
            ON o.application_id = a.application_id
        JOIN requisitions r
            ON a.requisition_id = r.requisition_id
        WHERE o.offer_id = ?
    """, (offer_id,)).fetchone()

    conn.close()

    if record is None:
        return False, "Offer or requisition not found"

    salary, minimum, maximum = record

    if salary < minimum:
        return False, "Offer is below approved salary band"

    if salary > maximum:
        return False, "Offer exceeds approved salary band"

    return True, "Offer is within approved salary band"


# ---------------------------------------
# 3. RECORD APPROVAL DECISION
# ---------------------------------------

def process_approval(
    offer_id,
    approver_id,
    decision,
    comments=""
):

    if decision not in ["APPROVED", "REJECTED"]:
        print("Invalid approval decision")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:

        offer = cursor.execute("""
            SELECT status
            FROM offers
            WHERE offer_id = ?
        """, (offer_id,)).fetchone()

        if offer is None:
            print("Offer not found!")
            return

        if offer[0] in ["APPROVED", "RELEASED", "REJECTED"]:
            print("Offer is already in a final state")
            return

        valid, message = validate_salary(offer_id)

        # Out-of-band offers cannot be normally approved
        if not valid and decision == "APPROVED":
            print("Approval blocked:", message)
            return

        cursor.execute("""
            INSERT INTO offer_approval_history (
                offer_id,
                approver_id,
                decision,
                comments,
                approval_time
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            offer_id,
            approver_id,
            decision,
            comments,
            datetime.now().isoformat()
        ))

        new_status = (
            "APPROVED" if decision == "APPROVED"
            else "REJECTED"
        )

        cursor.execute("""
            UPDATE offers
            SET status = ?
            WHERE offer_id = ?
        """, (new_status, offer_id))

        conn.commit()

        print("Offer ID:", offer_id)
        print("Decision:", decision)
        print("Salary validation:", message)
        print("Offer status:", new_status)

    finally:
        conn.close()


# ---------------------------------------
# 4. RELEASE APPROVED OFFER
# ---------------------------------------

def release_offer(offer_id):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:

        offer = cursor.execute("""
            SELECT status
            FROM offers
            WHERE offer_id = ?
        """, (offer_id,)).fetchone()

        if offer is None:
            print("Offer not found!")
            return

        if offer[0] != "APPROVED":
            print("Offer cannot be released without approval!")
            return

        cursor.execute("""
            UPDATE offers
            SET status = 'RELEASED'
            WHERE offer_id = ?
        """, (offer_id,))

        conn.commit()

        print("Offer released successfully!")

    finally:
        conn.close()


# ---------------------------------------
# 5. TEST CASES
# ---------------------------------------

if __name__ == "__main__":

    initialize_approval_system()

    print("\nTEST 1: Find a valid offer")

    conn = sqlite3.connect(DB_PATH)

    offer = conn.execute("""
        SELECT offer_id
        FROM offers
        LIMIT 1
    """).fetchone()

    conn.close()

    if offer:

        offer_id = offer[0]

        print("\nTEST 2: Salary validation")
        print(validate_salary(offer_id))

        print("\nTEST 3: Approval history")
        print("Approval table initialized successfully")

    else:
        print("No offers available for testing")
