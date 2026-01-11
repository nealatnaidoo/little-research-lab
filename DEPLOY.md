# Deploying Little Research Lab to Fly.io

This guide covers deploying the application to [Fly.io](https://fly.io).

## Prerequisites

1. Install the Fly CLI:
   ```bash
   # macOS
   brew install flyctl

   # Linux
   curl -L https://fly.io/install.sh | sh

   # Windows
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   ```

2. Login to Fly.io:
   ```bash
   fly auth login
   ```

## First-Time Deployment

### 1. Create the App

```bash
# Create app (this reserves the name)
fly apps create little-research-lab

# Or use a different name
fly apps create your-app-name
```

Update `fly.toml` with your app name if different.

### 2. Create Persistent Volume

The database and uploaded files are stored in a persistent volume:

```bash
# Create a 1GB volume in the same region as your app
fly volumes create lrl_data --size 1 --region iad

# Verify
fly volumes list
```

### 3. Set Secrets

Set required secrets (never commit these to git):

```bash
# Generate a secret key for session encryption
fly secrets set FLET_SECRET_KEY=$(openssl rand -hex 32)

# Optional: Set admin bootstrap credentials
fly secrets set LRL_ADMIN_EMAIL=admin@yourdomain.com
fly secrets set LRL_ADMIN_PASSWORD=your-secure-password
```

### 4. Deploy

```bash
fly deploy
```

First deployment takes a few minutes to build the Docker image.

### 5. Open Your App

```bash
fly open
```

## Subsequent Deployments

After the initial setup, deploying updates is simple:

```bash
fly deploy
```

## Useful Commands

```bash
# View logs
fly logs

# View app status
fly status

# SSH into the container
fly ssh console

# View secrets
fly secrets list

# Scale the app
fly scale count 2  # Run 2 instances

# View volumes
fly volumes list
```

## Database Backup

SSH into the container and run the backup command:

```bash
fly ssh console

# Inside the container
cd /app
python -m src.app_shell.cli backup
```

To download a backup:

```bash
# From your local machine
fly ssh sftp get /data/backups/backup_YYYYMMDD_HHMMSS.zip ./local-backup.zip
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LRL_DB_PATH` | SQLite database path | `/data/lrl.db` |
| `LRL_FS_PATH` | Filestore directory | `/data/filestore` |
| `LRL_DATA_DIR` | Data directory root | `/data` |
| `LRL_RULES_PATH` | Rules file path | `rules.yaml` |
| `FLET_SECRET_KEY` | Session encryption key | (required in production) |

## Troubleshooting

### App won't start

Check logs:
```bash
fly logs
```

Common issues:
- Missing `rules.yaml` - ensure it's not in `.dockerignore`
- Volume not mounted - check `fly volumes list`
- Secrets not set - check `fly secrets list`

### Database issues

SSH in and check:
```bash
fly ssh console
ls -la /data/
sqlite3 /data/lrl.db ".tables"
```

### Health check failures

The app must respond to `GET /` within 5 seconds. Check:
```bash
fly logs | grep health
```

## Cost Optimization

The default configuration uses:
- **Shared CPU, 512MB RAM** (~$3-5/month)
- **1GB persistent volume** (~$0.15/month)
- **Auto-stop** when idle (saves money)

For a personal site with low traffic, this is very affordable.

## Custom Domain

```bash
# Add a custom domain
fly certs create yourdomain.com

# View DNS instructions
fly certs show yourdomain.com
```

Then configure your DNS with the provided values.
