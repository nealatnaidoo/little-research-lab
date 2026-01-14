# Operations Manual

This document outlines the standard operating procedures for the Little Research Lab application, focusing on Data Safety and Disaster Recovery.

**Spec refs**: NFR-R2, T-0048, TA-0050

## Data Safety

### Backup Architecture

The application uses standalone backup scripts that archive:

1. **Database**: SQLite file (`data/lrl.db`) using SQLite online backup API for consistency
2. **Assets**: User-uploaded files (`data/assets/`) compressed as `.tar.gz`

Backups include:
- Timestamped files (e.g., `lrl_db_20260114_120000.sqlite`, `lrl_assets_20260114_120000.tar.gz`)
- SHA256 hashes for integrity verification
- JSON manifest with metadata

Default output directory: `./backups/`

### Performing a Manual Backup

To create an immediate backup of the current state:

```bash
python scripts/backup.py
```

**Options**:
```bash
python scripts/backup.py --out /path/to/backups    # Custom output directory
python scripts/backup.py --db-only                  # Database only
python scripts/backup.py --assets-only              # Assets only
python scripts/backup.py --data-dir /path/to/data   # Custom data directory
```

**Expected Output**:
```
============================================================
Little Research Lab: Backup
============================================================

Backing up database: ./data/lrl.db
  -> ./backups/lrl_db_20260114_120000.sqlite (118784 bytes)
Backing up assets: ./data/assets
  -> ./backups/lrl_assets_20260114_120000.tar.gz (15 files, 245760 bytes)

Manifest: ./backups/backup_manifest_20260114_120000.json

Backup completed successfully!
Backup directory: ./backups
```

### Backup Manifest

Each backup creates a JSON manifest with metadata:

```json
{
  "timestamp_utc": "20260114_120000",
  "created_at": "2026-01-14T12:00:00+00:00",
  "version": "1.0",
  "backups": [
    {
      "type": "database",
      "source": "./data/lrl.db",
      "backup": "./backups/lrl_db_20260114_120000.sqlite",
      "size_bytes": 118784,
      "sha256": "abc123..."
    },
    {
      "type": "assets",
      "source": "./data/assets",
      "backup": "./backups/lrl_assets_20260114_120000.tar.gz",
      "file_count": 15,
      "total_source_size_bytes": 512000,
      "archive_size_bytes": 245760,
      "sha256": "def456..."
    }
  ]
}
```

## Disaster Recovery

### Verify Backup Integrity (Restore Drill)

Before relying on a backup for recovery, verify its integrity with a non-destructive restore drill:

```bash
python scripts/restore_drill.py --backup ./backups
```

**Options**:
```bash
python scripts/restore_drill.py --manifest ./backups/backup_manifest_*.json
python scripts/restore_drill.py --json   # Output as JSON for automation
```

**Expected Output**:
```
============================================================
Little Research Lab: Restore Drill
============================================================

Using manifest: ./backups/backup_manifest_20260114_120000.json
Backup timestamp: 20260114_120000
Backups to verify: 2

Verifying database: lrl_db_20260114_120000.sqlite
  [PASS] hash_verification
  [PASS] sqlite_open
  [PASS] schema_valid

Verifying assets: lrl_assets_20260114_120000.tar.gz
  [PASS] hash_verification
  [PASS] extract_archive
  [PASS] files_extracted

============================================================
RESTORE DRILL PASSED: All backups verified successfully!
```

The restore drill:
- Verifies SHA256 hashes match
- Opens database and validates schema (checks for `users`, `content`, `assets` tables)
- Extracts assets archive to temp directory
- Does NOT modify production data

### Restore Procedures

> [!WARNING]
> Restoring a backup is a destructive operation. It will **overwrite** the current database and filestore. Any data created since the backup will be lost.

#### Manual Database Restore

```bash
# Stop the application
# Backup current state first (optional)
cp data/lrl.db data/lrl.db.pre-restore

# Restore from backup
cp backups/lrl_db_20260114_120000.sqlite data/lrl.db

# Restart the application
```

#### Manual Assets Restore

```bash
# Backup current assets first (optional)
mv data/assets data/assets.pre-restore

# Extract backup
mkdir data/assets
tar -xzf backups/lrl_assets_20260114_120000.tar.gz -C data/

# Restart the application
```

### Total System Recovery

If the server is lost or the application directory is corrupted:

1. **Re-install**: Clone the repository and install dependencies
   ```bash
   git clone <repo-url>
   cd little-research-lab
   pip install -r requirements.txt
   ```

2. **Configure**: Set up environment variables
   ```bash
   export LAB_DATA_DIR=./data
   ```

3. **Create data directory**:
   ```bash
   mkdir -p data/assets
   ```

4. **Restore database**: Copy from off-site backup
   ```bash
   cp /path/to/backup/lrl_db_*.sqlite data/lrl.db
   ```

5. **Restore assets**: Extract from backup
   ```bash
   tar -xzf /path/to/backup/lrl_assets_*.tar.gz -C data/
   ```

6. **Run migrations** (if schema changed):
   ```bash
   python -m src.adapters.sqlite.migrator data/lrl.db
   ```

7. **Verify**: Run restore drill on local copy
   ```bash
   python scripts/restore_drill.py --backup /path/to/backup
   ```

8. **Start application**

## Scheduled Backups

For production deployments, configure scheduled backups:

### Using cron (Linux/macOS)

```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/little-research-lab && python scripts/backup.py --out /backups/lrl
```

### Off-site Storage

For disaster recovery, copy backups to off-site storage:

```bash
# After backup, sync to cloud storage
python scripts/backup.py && aws s3 sync ./backups s3://my-bucket/lrl-backups/
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LAB_DATA_DIR` | `./data` | Location of database and assets |
| `STORAGE_PATH` | `./storage` | Alternative asset storage path |
