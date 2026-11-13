
import sqlite3
import shutil
import tempfile
from pathlib import Path

import business_logic.scheduling as scheduling


SOURCE_DB = Path("database/recruitment.db")


def run_scheduling_test():
    if not SOURCE_DB.exists():
        print("Database not found:", SOURCE_DB)
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        test_db = Path(temp_dir) / "recruitment_test.db"
        shutil.copy2(SOURCE_DB, test_db)

        # Make the scheduling module use the temporary database
        scheduling.DB_PATH = str(test_db)

        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        try:
            # Select two non-withdrawn applications without existing interviews
            apps = cursor.execute("""
                SELECT a.application_id
                FROM applications a
                LEFT JOIN interviews i
                    ON a.application_id = i.application_id
                WHERE a.stage != 'WITHDRAWN'
                  AND i.application_id IS NULL
                ORDER BY a.application_id
                LIMIT 2
            """).fetchall()

            dates = cursor.execute("""
                SELECT DISTINCT available_date
                FROM availability
                ORDER BY available_date
            """).fetchall()

            panels = cursor.execute("""
                SELECT panel_id
                FROM interview_panels
                ORDER BY panel_id
            """).fetchall()

        finally:
            conn.close()

        if len(apps) < 2:
            print("Not enough eligible applications.")
            return

        if not dates or not panels:
            print("No availability dates or interview panels found.")
            return

        app1, app2 = apps[0][0], apps[1][0]

        # Find a slot accepted by the scheduling validator
        available_slot = None

        for (date,) in dates:
            for (panel_id,) in panels:
                for hour in range(9, 17):
                    start_time = f"{hour:02d}:00"

                    valid, message = scheduling.validate_schedule(
                        app1,
                        panel_id,
                        date,
                        start_time
                    )

                    if valid:
                        available_slot = (panel_id, date, start_time)
                        break

                if available_slot:
                    break

            if available_slot:
                break

        if not available_slot:
            print("No available slot found for the first application.")
            return

        panel_id, date, start_time = available_slot

        print("\nTEST 1: First interview booking")
        print("Application:", app1)
        print("Panel:", panel_id)
        print("Date:", date)
        print("Time:", start_time)

        scheduling.schedule_interview(
            app1, panel_id, date, start_time
        )

        # Verify the first booking was actually inserted
        conn = sqlite3.connect(test_db)
        first_booking = conn.execute("""
            SELECT interview_id
            FROM interviews
            WHERE application_id = ?
              AND panel_id = ?
              AND interview_date = ?
              AND start_time = ?
              AND status = 'SCHEDULED'
        """, (app1, panel_id, date, start_time)).fetchone()
        conn.close()

        if not first_booking:
            print("First booking was not created. Test stopped.")
            return

        print("\nTEST 2: Second interview at the same time")
        print("Application:", app2)

        valid, message = scheduling.validate_schedule(
            app2, panel_id, date, start_time
        )

        if valid:
            print("TEST FAILED: The overlapping booking was allowed.")
        else:
            print("TEST PASSED: Second booking correctly rejected.")
            print("Reason:", message)

        print("\nScheduling tests completed.")
        print("Original database was not modified.")


if __name__ == "__main__":
    run_scheduling_test()
