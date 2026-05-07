import sqlite3
import os

DB_PATH = "chat_history.db"
if os.path.exists(DB_PATH):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("ALTER TABLE sessions ADD COLUMN user_email VARCHAR(150) DEFAULT 'anonymous'")
        conn.commit()
        conn.close()
        print("Migration successful.")
    except Exception as e:
        print("Migration skipped or failed:", e)
else:
    print("DB does not exist yet.")
