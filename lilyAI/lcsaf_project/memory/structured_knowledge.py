import sqlite3


class StructuredKnowledge:
    def __init__(self, db_path="/tmp/lily_knowledge.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS facts (key TEXT PRIMARY KEY, value TEXT)"
        )

    def set(self, key, value):
        self.conn.execute("REPLACE INTO facts (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()

    def query(self, key):
        cur = self.conn.execute("SELECT value FROM facts WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else None
