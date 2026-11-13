
import sqlite3

conn = sqlite3.connect("database/recruitment.db")
cursor = conn.cursor()

print("DATABASE INTEGRITY:")
print(cursor.execute("PRAGMA integrity_check").fetchone()[0])

print("\nFOREIGN KEY CHECK:")
errors = cursor.execute("PRAGMA foreign_key_check").fetchall()
print("No foreign key errors" if not errors else errors)

conn.close()
