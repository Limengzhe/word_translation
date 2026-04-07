import sqlite3
import os

db_path = "translate.db"
if not os.path.exists(db_path):
    print("DB not found, fresh start will include the column")
else:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(segment)")
    cols = [row[1] for row in cur.fetchall()]
    print("Current columns:", cols)

    if "source_html" not in cols:
        cur.execute("ALTER TABLE segment ADD COLUMN source_html TEXT")
        con.commit()
        print("Added source_html column")
    else:
        print("source_html already exists")
    con.close()
