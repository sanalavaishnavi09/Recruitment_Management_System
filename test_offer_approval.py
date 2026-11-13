
import sqlite3
import shutil
import tempfile
from pathlib import Path

import business_logic.offer_approval as approval


SOURCE_DB = Path("database/recruitment.db")


def run_offer_tests():

    if not SOURCE_DB.exists():
        print("Database not found:", SOURCE_DB)
        return

    with tempfile.TemporaryDirectory() as temp_dir:

        test_db = Path(temp_dir) / "recruitment_test.db"
        shutil.copy2(SOURCE_DB, test_db)

        # Ensure every approval function uses the temporary database
        approval.DB_PATH = str(test_db)

        approval.initialize_approval_system()

        conn = sqlite3.connect(test_db)

        offers = conn.execute("""
            SELECT o.offer_id
            FROM offers o
            JOIN applications a
                ON o.application_id = a.application_id
            JOIN requisitions r
                ON a.requisition_id = r.requisition_id
            WHERE o.status = 'PENDING_APPROVAL'
              AND o.offered_salary_lpa BETWEEN
                  r.min_salary_lpa AND r.max_salary_lpa
            ORDER BY o.offer_id
            LIMIT 2
        """).fetchall()

        conn.close()

        if len(offers) < 2:
            print("Two pending valid offers are required.")
            return

        offer1 = offers[0][0]
        offer2 = offers[1][0]

        # TEST 1: Approve a valid offer
        print("\nTEST 1: Approve valid offer")
        print("Offer ID:", offer1)
        print("Salary check:", approval.validate_salary(offer1))

        approval.process_approval(
            offer1,
            "MGR-0001",
            "APPROVED",
            "Salary within approved band"
        )

        # TEST 2: Release approved offer
        print("\nTEST 2: Release approved offer")

        approval.release_offer(offer1)

        # TEST 3: Reject an offer above the salary band
        print("\nTEST 3: Out-of-band offer")
        print("Offer ID:", offer2)

        conn = sqlite3.connect(test_db)

        result = conn.execute("""
            SELECT o.offered_salary_lpa,
                   r.max_salary_lpa
            FROM offers o
            JOIN applications a
                ON o.application_id = a.application_id
            JOIN requisitions r
                ON a.requisition_id = r.requisition_id
            WHERE o.offer_id = ?
        """, (offer2,)).fetchone()

        conn.close()

        if result is None:
            print("Offer or requisition not found.")
            return

        original_salary, maximum = result

        # Temporarily increase salary beyond the approved band
        conn = sqlite3.connect(test_db)

        conn.execute("""
            UPDATE offers
            SET offered_salary_lpa = ?
            WHERE offer_id = ?
        """, (maximum + 1, offer2))

        conn.commit()
        conn.close()

        print("Salary check:", approval.validate_salary(offer2))

        approval.process_approval(
            offer2,
            "MGR-0001",
            "APPROVED",
            "Testing out-of-band salary"
        )

        print("\nOffer approval tests completed.")
        print("Original database was not modified.")


if __name__ == "__main__":
    run_offer_tests()
