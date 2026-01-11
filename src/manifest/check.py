
import sys
from pathlib import Path

ALLOWED_ROOTS = {
    "adapters",
    "app_shell",
    "components",
    "domain",
    "manifest",
    "ports",
    "rules",
    "services",
    "ui"
}

IGNORE = {"__pycache__", ".DS_Store", "__init__.py"}

def check_structure(root_path: Path = Path("src")) -> list[str]:
    errors = []
    
    if not root_path.exists():
        return ["src directory not found!"]

    # 1. Check Top-Level Directories
    for entry in root_path.iterdir():
        if entry.name in IGNORE:
            continue
        
        if entry.is_dir():
            if entry.name not in ALLOWED_ROOTS:
                errors.append(
                    f"Illegal dir in src/: '{entry.name}'. Allowed: {sorted(list(ALLOWED_ROOTS))}"
                )
            else:
                # 2. Check for __init__.py in allowed dirs (packages)
                init_file = entry / "__init__.py"
                if not init_file.exists():
                    errors.append(f"Missing __init__.py in package: '{entry.name}'")
        elif entry.is_file():
             if entry.name not in IGNORE:
                 errors.append(
                     f"Illegal file in src/ root: '{entry.name}'. Should be in component packages."
                 )

    return errors

if __name__ == "__main__":
    violations = check_structure()
    if violations:
        print("Architectural Violations Found:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("Architecture Integrity Check: PASS")
        sys.exit(0)
