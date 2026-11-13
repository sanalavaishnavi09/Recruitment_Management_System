
import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "database/recruitment.db"

# ------------------------------------------------
# 1. DATABASE INITIALIZATION
# ------------------------------------------------

def initialize_scheduling():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create bridge table: panels and interviewers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS panel_members (
            panel_id TEXT NOT NULL,
            manager_id TEXT NOT NULL,
            PRIMARY KEY (panel_id, manager_id),
            FOREIGN KEY (panel_id)
                REFERENCES interview_panels(panel_id),
            FOREIGN KEY (manager_id)
                REFERENCES hiring_managers(manager_id)
        )
    """)

    # Add end_time to existing interviews table
    columns = [
        row[1] for row in cursor.execute(
            "PRAGMA table_info(interviews)"
        ).fetchall()
    ]

    if "end_time" not in columns:
        cursor.execute(
            "ALTER TABLE interviews ADD COLUMN end_time TEXT"
        )

    # Existing interviews are assumed to last 60 minutes
    existing = cursor.execute("""
        SELECT interview_id, interview_date, start_time
        FROM interviews
        WHERE end_time IS NULL
    """).fetchall()

    for interview_id, date, start in existing:
        start_dt = datetime.strptime(
            f"{date} {start}", "%Y-%m-%d %H:%M"
        )
        end = (start_dt + timedelta(minutes=60)).strftime("%H:%M")

        cursor.execute("""
            UPDATE interviews
            SET end_time = ?
            WHERE interview_id = ?
        """, (end, interview_id))

    # Assign three interviewers to each panel
    panels = cursor.execute(
        "SELECT panel_id FROM interview_panels ORDER BY panel_id"
    ).fetchall()

    managers = [
        row[0] for row in cursor.execute(
            "SELECT manager_id FROM hiring_managers ORDER BY manager_id"
        ).fetchall()
    ]

    rng = random.Random(20261022)

    for (panel_id,) in panels:
        selected = rng.sample(managers, 3)

        for manager_id in selected:
            cursor.execute("""
                INSERT OR IGNORE INTO panel_members
                (panel_id, manager_id)
                VALUES (?, ?)
            """, (panel_id, manager_id))

    conn.commit()
    conn.close()

    print("Scheduling database initialized!")
    print("Panel members assigned successfully!")


# ------------------------------------------------
# 2. CHECK TIME OVERLAP
# ------------------------------------------------

def time_ranges_overlap(start1, end1, start2, end2):

    return start1 < end2 and start2 < end1


# ------------------------------------------------
# 3. VALIDATE INTERVIEW SCHEDULING
# ------------------------------------------------

def validate_schedule(application_id, panel_id,
                      interview_date, start_time,
                      duration_minutes=60):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:

        # Check application
        app = cursor.execute("""
            SELECT stage
            FROM applications
            WHERE application_id = ?
        """, (application_id,)).fetchone()

        if app is None:
            return False, "Application does not exist"

        if app[0] == "WITHDRAWN":
            return False, "Candidate has withdrawn"

        # Check panel
        panel = cursor.execute("""
            SELECT panel_id
            FROM interview_panels
            WHERE panel_id = ?
        """, (panel_id,)).fetchone()

        if panel is None:
            return False, "Interview panel does not exist"

        # Get panel interviewers
        members = cursor.execute("""
            SELECT manager_id
            FROM panel_members
            WHERE panel_id = ?
        """, (panel_id,)).fetchall()

        if not members:
            return False, "No interviewers assigned to panel"

        start_dt = datetime.strptime(
            f"{interview_date} {start_time}",
            "%Y-%m-%d %H:%M"
        )

        end_dt = start_dt + timedelta(
            minutes=duration_minutes
        )

        proposed_start = start_dt.strftime("%H:%M")
        proposed_end = end_dt.strftime("%H:%M")

        if end_dt.date() != start_dt.date():
            return False, "Interview must finish on the same day"

        # Check every interviewer
        for (manager_id,) in members:

            # Availability check
            availability = cursor.execute("""
                SELECT 1
                FROM availability
                WHERE manager_id = ?
                AND available_date = ?
                AND start_time <= ?
                AND end_time >= ?
            """, (
                manager_id,
                interview_date,
                proposed_start,
                proposed_end
            )).fetchone()

            if not availability:
                return False, (
                    f"{manager_id} is not available "
                    "for the requested time"
                )

            # Check overlapping interviews
            bookings = cursor.execute("""
                SELECT i.start_time, i.end_time
                FROM interviews i
                JOIN panel_members pm
                  ON i.panel_id = pm.panel_id
                WHERE pm.manager_id = ?
                AND i.interview_date = ?
                AND i.status IN (
                    'SCHEDULED', 'RESCHEDULED', 'COMPLETED'
                )
            """, (
                manager_id,
                interview_date
            )).fetchall()

            for old_start, old_end in bookings:

                if time_ranges_overlap(
                    proposed_start,
                    proposed_end,
                    old_start,
                    old_end
                ):
                    return False, (
                        f"Scheduling conflict: {manager_id} "
                        f"already has an interview from "
                        f"{old_start} to {old_end}"
                    )

        return True, "Interview can be scheduled"

    finally:
        conn.close()


# ------------------------------------------------
# 4. CREATE INTERVIEW
# ------------------------------------------------

def schedule_interview(application_id, panel_id,
                       interview_date, start_time,
                       duration_minutes=60):

    valid, message = validate_schedule(
        application_id,
        panel_id,
        interview_date,
        start_time,
        duration_minutes
    )

    print("\nSCHEDULING RESULT")
    print("Decision:", "APPROVED" if valid else "REJECTED")
    print("Message:", message)

    if not valid:
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.cursor()

        # Generate next interview ID
        last_id = cursor.execute("""
            SELECT MAX(CAST(
                SUBSTR(interview_id, 10) AS INTEGER
            ))
            FROM interviews
            WHERE interview_id LIKE 'INT-2026-%'
        """).fetchone()[0]

        next_id = (last_id or 0) + 1
        interview_id = f"INT-2026-{next_id:06d}"

        start_dt = datetime.strptime(
            f"{interview_date} {start_time}",
            "%Y-%m-%d %H:%M"
        )

        end_time = (
            start_dt + timedelta(minutes=duration_minutes)
        ).strftime("%H:%M")

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
            interview_id,
            application_id,
            panel_id,
            interview_date,
            start_time,
            "SCHEDULED",
            end_time
        ))

        conn.commit()

        print("Interview ID:", interview_id)
        print("Interview scheduled successfully!")

    finally:
        conn.close()


# ------------------------------------------------
# 5. TEST CASES
# ------------------------------------------------

if __name__ == "__main__":

    initialize_scheduling()

    print("\nTEST 1: Overlapping time slots")

    print(time_ranges_overlap(
        "10:00", "11:00",
        "10:30", "11:30"
    ))

    print("\nTEST 2: Non-overlapping time slots")

    print(time_ranges_overlap(
        "10:00", "11:00",
        "11:00", "12:00"
    ))

    print("\nTEST 3: Interviewer availability")

    print(validate_schedule(
        "INVALID-APPLICATION",
        "PANEL-0001",
        "2026-11-11",
        "10:00"
    ))