# Operations Manual

This document outlines the standard operating procedures for the Little Research Lab application, focusing on Data Safety and Disaster Recovery.

## Data Safety

### Backup Architecture
The application uses a CLI-driven backup system that archives:
1. **Database**: The SQLite file (`lrl.db`).
2. **Filestore**: The directory containing uploaded assets and generated artifacts.

Backups are compressed into a `.zip` archive and stored in the `backups/` directory relative to the application root.

### performing a Manual Backup
To create an immediate backup of the current state:

```bash
python -m src.app_shell.cli backup
```

**Expected Output**:
```
Backup created: backups/backup_20231027_103000.zip (Size: 1.2MB)
```

### Retention Policy
The system automatically rotates backups based on `rules.yaml` configuration.
- **Default Retention**: Keep last 5 backups.
- Older backups are deleted automatically during the `backup` command execution.

## Disaster Recovery

### List Available Backups
To see what restoration points are available:

```bash
python -m src.app_shell.cli restore --list
```

### Restore Procedures

> [!WARNING]
> Restoring a backup is a destructive operation. It will **overwrite** the current database and filestore with the contents of the archive. Any data created since the backup will be lost.

#### Restore Latest
To revert to the most recent backup:

```bash
python -m src.app_shell.cli restore --latest
```

#### Restore Specific Point
To restore a specific file:

```bash
python -m src.app_shell.cli restore --file backups/backup_20231027_103000.zip
```

### Total System Recovery
If the server is lost or the application directory is corrupted:
1. **Re-install**: Clone the repository and install dependencies.
2. **Configure**: Ensure `rules.yaml` is present.
3. **Place Backup**: Copy your off-site backup zip file to `backups/`.
4. **Restore**: Run the restore command targeted at that file.
