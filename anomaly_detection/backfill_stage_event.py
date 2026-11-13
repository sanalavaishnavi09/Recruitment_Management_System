
import sqlite3
from datetime import datetime

conn = sqlite3.connect("database/recruitment.db")
cursor = conn.cursor()

cursor.execute("""
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

anomaly = cursor.execute("""
    SELECT record_id, original_value, injected_value
    FROM anomaly_injection_log
    WHERE issue_id = 'ANOM-2026-001'
""").fetchone()

if anomaly:
    app_id, old_stage, new_stage = anomaly

    exists = cursor.execute("""
        SELECT 1 FROM application_events
        WHERE application_id = ?
          AND previous_stage = ?
          AND new_stage = ?
    """, (app_id, old_stage, new_stage)).fetchone()

    if not exists:
        cursor.execute("""
            INSERT INTO application_events (
                application_id,
                previous_stage,
                new_stage,
                decision,
                reason,
                event_time
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            app_id,
            old_stage,
            new_stage,
            "REJECTED",
            "Invalid stage transition recorded",
            datetime.now().isoformat()
        ))

        conn.commit()
        print("Stage history event created!")
    else:
        print("Stage history event already exists!")

else:
    print("Stage injection audit record not found!")

conn.close()
