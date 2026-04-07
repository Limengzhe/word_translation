import sqlite3
import os
import sys

db_path = "translate.db"
if not os.path.exists(db_path):
    print("DB not found")
    sys.exit(0)

con = sqlite3.connect(db_path)
cur = con.cursor()

cur.execute("PRAGMA table_info(segment)")
cols = [row[1] for row in cur.fetchall()]
print("Columns:", cols)

if "para_type" not in cols:
    sql = "ALTER TABLE segment ADD COLUMN para_type VARCHAR(16) NOT NULL DEFAULT 'p'"
    cur.execute(sql)
    con.commit()
    print("OK: para_type added")
else:
    print("OK: para_type already exists")

con.close()
