
import sqlite3
from pathlib import Path

# Locate database from project root
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "recruitment.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\nINTERVIEWER CONFLICT AUDIT")
print("=" * 60)

# Find overlapping interviews involving the same manager
query = """
SELECT
    i1.interview_id AS interview_1,
    i2.interview_id AS interview_2,
    i1.panel_id AS panel_1,
    i2.panel_id AS panel_2,
    i1.interview_date,
    i1.start_time AS start_1,
    i1.end_time AS end_1,
    i2.start_time AS start_2,
    i2.end_time AS end_2,
    i1.status AS status_1,
    i2.status AS status_2,
    GROUP_CONCAT(DISTINCT pm1.manager_id) AS shared_interviewers

FROM interviews i1

JOIN interviews i2
    ON i1.interview_date = i2.interview_date
    AND i1.interview_id < i2.interview_id

JOIN panel_members pm1
    ON pm1.panel_id = i1.panel_id

JOIN panel_members pm2
    ON pm2.panel_id = i2.panel_id
    AND pm1.manager_id = pm2.manager_id

WHERE
    i1.start_time < i2.end_time
    AND i2.start_time < i1.end_time

    AND UPPER(i1.status) NOT IN ('CANCELLED', 'CANCELED')
    AND UPPER(i2.status) NOT IN ('CANCELLED', 'CANCELED')

GROUP BY
    i1.interview_id,
    i2.interview_id,
    i1.panel_id,
    i2.panel_id,
    i1.interview_date,
    i1.start_time,
    i1.end_time,
    i2.start_time,
    i2.end_time,
    i1.status,
    i2.status

ORDER BY i1.interview_date, i1.start_time
"""

conflicts = cursor.execute(query).fetchall()

print("Total conflicting interview pairs:", len(conflicts))

print("\nSAMPLE CONFLICTS")
print("-" * 60)

for row in conflicts[:20]:
    print("\nInterview 1:", row[0])
    print("Interview 2:", row[1])
    print("Panel 1:", row[2])
    print("Panel 2:", row[3])
    print("Date:", row[4])
    print("Shared interviewers:", row[11])

# Count unique affected interview IDs
affected = set()

for row in conflicts:
    affected.add(row[0])
    affected.add(row[1])

print("\nSUMMARY")
print("-" * 60)
print("Conflicting interview pairs:", len(conflicts))
print("Unique affected interviews:", len(affected))

conn.close()

print("\nAudit completed!")
