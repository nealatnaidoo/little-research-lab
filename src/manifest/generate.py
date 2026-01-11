import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

IGNORE_DIRS = {"__pycache__", ".DS_Store", ".git"}
SRC_ROOT = Path("src")


def get_file_hash(path: Path) -> str:
    """Compute basic SHA256 hash."""
    try:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return "error"

def generate_manifest(root: Path = SRC_ROOT) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "modules": {}
    }
    
    if not root.exists():
        return manifest

    for entry in root.iterdir():
        if entry.name in IGNORE_DIRS:
            continue
            
        if entry.is_dir():
            files = []
            for r, _, fs in os.walk(entry):
                for f in fs:
                    if f in IGNORE_DIRS or f.endswith(".pyc"):
                        continue
                    file_path = Path(r) / f
                    rel_path = file_path.relative_to(root)
                    files.append({
                        "path": str(rel_path),
                        "size": file_path.stat().st_size,
                        "hash": get_file_hash(file_path)
                    })
            files.sort(key=lambda x: str(x["path"]))
            manifest["modules"][entry.name] = files
            
    return manifest

if __name__ == "__main__":
    print(json.dumps(generate_manifest(), indent=2))
