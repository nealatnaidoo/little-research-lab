import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

from src.rules.loader import load_rules
from src.ui.context import ServiceContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cli")

DB_PATH = "lrl.db"
FS_PATH = "filestore"
RULES_PATH = "rules.yaml"


def get_context() -> ServiceContext:
    if not Path(RULES_PATH).exists():
        logger.error(f"Rules file {RULES_PATH} not found.")
        sys.exit(1)

    rules = load_rules(Path(RULES_PATH))
    return ServiceContext.create(DB_PATH, FS_PATH, rules)


def handle_invite(ctx: ServiceContext, args: argparse.Namespace) -> None:
    role = args.role
    email = args.creator_email
    creator = ctx.auth_service.user_repo.get_by_email(email)
    if not creator:
        logger.error(f"Creator {email} not found. Invoke with valid admin email.")
        sys.exit(1)

    token = ctx.invite_service.create_invite(creator, role)
    print(f"Invite created for role '{role}'.")
    print(f"Token: {token}")
    print(f"Link: /invite/{token}")


def handle_publish(ctx: ServiceContext, args: argparse.Namespace) -> None:
    count = ctx.publish_service.process_due_items()
    print(f"Published {count} items.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Little Research Lab CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # invite
    invite_parser = subparsers.add_parser("invite", help="Create an invite token")
    invite_parser.add_argument("role", help="Role to assign (viewer, editor, publisher, admin)")
    invite_parser.add_argument(
        "--creator-email", required=True, help="Email of admin creating the invite"
    )

    # publish_due
    subparsers.add_parser("publish_due", help="Process scheduled items")

    # backup
    subparsers.add_parser("backup", help="Create a backup")

    # restore
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("--list", action="store_true", help="List available backups")
    restore_parser.add_argument("--latest", action="store_true", help="Restore most recent backup")
    restore_parser.add_argument("--file", help="Path to backup zip")

    args = parser.parse_args()

    ctx = get_context()

    if args.command == "invite":
        handle_invite(ctx, args)
    elif args.command == "publish_due":
        handle_publish(ctx, args)
    elif args.command == "backup":
        handle_backup(Path(RULES_PATH))
    elif args.command == "restore":
        handle_restore(Path(RULES_PATH), args)


def handle_backup(rules_path: Path) -> None:
    rules = load_rules(rules_path)
    backup_cfg = rules.ops.backups

    backup_dir = Path(backup_cfg.backup_dir_name)
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = backup_dir / f"backup_{timestamp}"

    # We want to zip 'lrl.db' and 'filestore' (or whatever is in 'include')
    # Use a temp directory to collect files? or zip independently?
    # shutil.make_archive zips a root_dir.
    # We can create a temp dir, copy targets there, then zip temp dir.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        items_included = 0
        for item in backup_cfg.include:
            src = Path(item)
            if src.exists():
                dst = tmp_path / item
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                items_included += 1

        if items_included == 0:
            logger.warning("No files found to backup.")
            return

        archive_path = shutil.make_archive(str(zip_name), "zip", tmp_path)
        print(f"Backup created: {archive_path}")

    # Retention
    backups = sorted(backup_dir.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    limit = backup_cfg.retention_count
    if len(backups) > limit:
        for old in backups[limit:]:
            old.unlink()
            print(f"Pruned old backup: {old.name}")


def handle_restore(rules_path: Path, args: argparse.Namespace) -> None:
    rules = load_rules(rules_path)
    backup_dir = Path(rules.ops.backups.backup_dir_name)

    if args.list:
        backups = sorted(
            backup_dir.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        print("Available Backups:")
        for b in backups:
            print(f" - {b.name} ({b.stat().st_size} bytes)")
        return

    target = None
    if args.latest:
        backups = sorted(
            backup_dir.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not backups:
            logger.error("No backups found.")
            sys.exit(1)
        target = backups[0]
    elif args.file:
        target = Path(args.file)
        if not target.exists():
            logger.error(f"File {target} not found.")
            sys.exit(1)

    if not target:
        logger.error("Specify --latest or --file <path>.")
        sys.exit(1)

    print(f"Restoring from {target}...")
    shutil.unpack_archive(str(target), ".")
    print("Restore complete.")


if __name__ == "__main__":
    main()
