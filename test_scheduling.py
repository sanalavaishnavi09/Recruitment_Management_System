
import sqlite3
from business_logic.scheduling import schedule_interview

conn = sqlite3.connect("database/recruitment.db")
cursor = conn.cursor()

# Get two valid applications
apps = cursor.execute("""
    SELECT application_id
    FROM applications
    WHERE stage != 'WITHDRAWN'
    LIMIT 2
""").fetchall()

conn.close()

if len(apps) < 2:
    print("Not enough valid applications")
else:
    app1 = apps[0][0]
    app2 = apps[1][0]

    print("\nTEST 1: First interview booking")

    schedule_interview(
        app1,
        "PANEL-0002",
        "2026-11-16",
        "14:00"
    )

    print("\nTEST 2: Second interview at same time")

    schedule_interview(
        app2,
        "PANEL-0002",
        "2026-11-16",
        "14:00"
    )
