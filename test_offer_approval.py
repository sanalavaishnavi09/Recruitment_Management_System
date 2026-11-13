import sqlite3

from business_logic.offer_approval import (
    initialize_approval_system,
    validate_salary,
    process_approval,
    release_offer
)

DB_PATH = "database/recruitment_test.db"

# Initialize approval history
initialize_approval_system()

conn = sqlite3.connect(DB_PATH)

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
    print("Two pending offers are required for testing.")

else:

    offer1 = offers[0][0]
    offer2 = offers[1][0]

    # TEST 1: Valid offer approval
    print("\nTEST 1: Approve valid offer")

    print("Salary check:", validate_salary(offer1))

    process_approval(
        offer1,
        "MGR-0001",
        "APPROVED",
        "Salary within approved band"
    )

    # TEST 2: Release approved offer
    print("\nTEST 2: Release approved offer")

    release_offer(offer1)

    # TEST 3: Out-of-band salary
    print("\nTEST 3: Out-of-band offer")

    conn = sqlite3.connect(DB_PATH)

    original_salary, maximum = conn.execute("""
        SELECT o.offered_salary_lpa,
               r.max_salary_lpa
        FROM offers o
        JOIN applications a
          ON o.application_id = a.application_id
        JOIN requisitions r
          ON a.requisition_id = r.requisition_id
        WHERE o.offer_id = ?
    """, (offer2,)).fetchone()

    # Temporarily increase salary beyond the approved band
    conn.execute("""
        UPDATE offers
        SET offered_salary_lpa = ?
        WHERE offer_id = ?
    """, (maximum + 1, offer2))

    conn.commit()
    conn.close()

    print("Salary check:", validate_salary(offer2))

    process_approval(
        offer2,
        "MGR-0001",
        "APPROVED",
        "Testing out-of-band salary"
    )

    # Restore original salary
    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        UPDATE offers
        SET offered_salary_lpa = ?
        WHERE offer_id = ?
    """, (original_salary, offer2))

    conn.commit()
    conn.close()

    print("\nOriginal salary restored.")
    print("Offer approval tests completed!")
