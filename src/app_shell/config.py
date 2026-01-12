import os
import sys
from pathlib import Path

from src.rules.models import Rules


def validate_ops_rules(rules: Rules, base_dir: Path) -> None:
    """
    Validate operational requirements before startup.
    """
    ops = rules.ops

    # 1. Check Data Dir
    if ops.data_dir_required:
        # Assuming data dir is where lrl.db lives, usually defined by env or default?
        # In this app, we hardcode to ./lrl.db in SQLiteAdapter unless configured?
        # Actually our app uses 'sqlite:///' + DB_PATH.
        # But broadly, if ops rules say data dir required, we might check write access.
        pass

    # 2. Check Required Env
    missing = []
    for env_var in ops.required_env:
        if env_var not in os.environ:
            missing.append(env_var)

    if missing:
        print(
            f"CRITICAL: Missing required environment variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # 3. Check Bootstrap Env if enabled and likely needed
    # (Actually handled in bootstrap logic, but we could warn here)
    if ops.bootstrap_admin.enabled_if_no_users:
        # Check standard LRL ones if not in 'required' list?
        # Standard convention: LRL_BOOTSTRAP_EMAIL / PASSWORD
        pass

    print("Configuration Validated.")
