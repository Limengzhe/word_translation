"""一次性迁移：向 document 表添加 full_source_html 和 full_translated_html 列。"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "translate.db"

def main():
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}, skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(document)")
    existing = {row[1] for row in cur.fetchall()}

    added = []
    for col in ("full_source_html", "full_translated_html"):
        if col not in existing:
            cur.execute(f"ALTER TABLE document ADD COLUMN {col} TEXT")
            added.append(col)

    conn.commit()
    conn.close()

    if added:
        print(f"Migration OK: added columns {added}")
    else:
        print("Columns already exist, nothing to do.")

if __name__ == "__main__":
    main()
