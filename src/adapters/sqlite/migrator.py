import os
import sqlite3


class SQLiteMigrator:
    def __init__(self, db_path: str, migrations_dir: str):
        self.db_path = db_path
        self.migrations_dir = migrations_dir

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _ensure_migration_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

    def _get_applied_migrations(self, conn: sqlite3.Connection) -> set[str]:
        cursor = conn.execute("SELECT filename FROM _migrations")
        return {row[0] for row in cursor.fetchall()}

    def run_migrations(self) -> None:
        """Apply all pending migrations."""
        conn = self._get_connection()
        try:
            self._ensure_migration_table(conn)
            applied = self._get_applied_migrations(conn)

            # Get list of .sql files
            files = sorted([f for f in os.listdir(self.migrations_dir) if f.endswith(".sql")])

            for filename in files:
                if filename not in applied:
                    print(f"Applying migration: {filename}")
                    self._apply_migration(conn, filename)
            
            print("All migrations applied.")

        finally:
            conn.close()

    def _read_up_script(self, filename: str) -> str:
        path = os.path.join(self.migrations_dir, filename)
        with open(path) as f:
            content = f.read()
        
        # Split by '-- Down' effectively taking the first part
        # Or look for '-- Up'?
        # Simple convention: File starts with Up.
        if "-- Down" in content:
            up_part = content.split("-- Down")[0]
            return up_part
        return content

    def _apply_migration(self, conn: sqlite3.Connection, filename: str) -> None:
        script = self._read_up_script(filename)
        try:
            conn.executescript(script)
            conn.execute("INSERT INTO _migrations (filename) VALUES (?)", (filename,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Migration {filename} failed: {e}") from e
