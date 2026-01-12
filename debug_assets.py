
import sqlite3
import os
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class Asset(BaseModel):
    id: UUID
    filename_original: str
    mime_type: str
    size_bytes: int
    sha256: str
    storage_path: str
    visibility: str = "private"
    created_by_user_id: UUID
    created_at: datetime

db_path = "./data/lrl.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

print(f"Inspecting {db_path}...")

try:
    rows = conn.execute("SELECT * FROM assets").fetchall()
    print(f"Found {len(rows)} assets.")
    for row in rows:
        print(f"Row ID: {row['id']}")
        try:
            a = Asset(
                id=UUID(row["id"]),
                filename_original=row["filename_original"],
                mime_type=row["mime_type"],
                size_bytes=row["size_bytes"],
                sha256=row["sha256"],
                storage_path=row["storage_path"],
                visibility=row["visibility"],
                created_by_user_id=UUID(row["created_by_user_id"]) if row["created_by_user_id"] else None,
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.min,
            )
            print("  OK")
        except Exception as e:
            print(f"  ERROR: {e}")
            print(f"  Data: {dict(row)}")
except Exception as e:
    print(f"Query Failed: {e}")
finally:
    conn.close()
