import sqlite3
import pandas as pd
import os

os.makedirs("database", exist_ok=True)

conn = sqlite3.connect("database/recruitment.db")

tables = [
    "hiring_managers",
    "requisitions",
    "candidates",
    "skill_requirements",
    "applications",
    "interview_panels",
    "availability",
    "interviews",
    "scorecards",
    "offers",
    "approvals"
]

for table in tables:
    df = pd.read_csv(f"data/{table}.csv")

    df.to_sql(
        table,
        conn,
        if_exists="replace",
        index=False
    )

    print(f"{table} inserted successfully")

conn.close()

print("Database created successfully!")