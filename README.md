# Little Research Lab

A modern "Link-in-Bio" style landing page and content management system built with Python and [Flet](https://flet.dev). Features a premium responsive UI, rich content authoring, and secure administration.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Flet](https://img.shields.io/badge/flet-0.28.x-purple.svg)
![Deploy](https://img.shields.io/badge/deploy-fly.io-blueviolet.svg)

## Features

### Public-Facing
- **Landing Page** - Curated links, featured posts, and bio section
- **Content Pages** - Blog posts and static pages with Markdown support
- **Tag Filtering** - Browse content by tags
- **Link Redirects** - Trackable short links
- **Responsive Design** - Works on desktop and mobile

### Admin Dashboard
- **Content Management** - Create, edit, schedule, and publish posts/pages
- **Asset Management** - Upload and manage images and files
- **User Management** - Invite users, assign roles, manage permissions
- **Schedule Publishing** - Set future publish dates for content

### Technical
- **Dark/Light Mode** - Theme toggle with "Science/Tech" aesthetics
- **Role-Based Access Control** - Owner, Admin, Publisher, Editor, Viewer roles
- **Secure Authentication** - Argon2 password hashing, session management
- **Rate Limiting** - Protection against abuse
- **SQLite Database** - Simple, portable data storage

## Tech Stack

| Layer | Technology |
|-------|------------|
| UI Framework | [Flet](https://flet.dev) (Python → Flutter Web) |
| Backend | Python 3.12+ |
| Database | SQLite |
| Validation | Pydantic |
| Auth | Argon2-cffi |
| Charts | Matplotlib |
| Deployment | Docker, Fly.io |

## Architecture

```
src/
├── domain/           # Core business logic & entities (pure Python)
│   ├── entities.py   # User, ContentItem, Asset, etc.
│   └── policies.py   # RBAC policy rules
├── ports/            # Interfaces/abstractions
│   └── repositories.py
├── adapters/         # Implementations
│   └── sqlite/       # SQLite repository implementations
├── services/         # Application services
│   ├── auth_service.py
│   ├── content_service.py
│   └── asset_service.py
├── app_shell/        # Route handlers & admin views
│   ├── router.py
│   ├── admin/        # Admin dashboard views
│   └── public_*.py   # Public page handlers
├── ui/               # UI components & layout
│   ├── main.py       # App entry point
│   ├── layout.py     # MainLayout with navigation
│   ├── theme.py      # Theme configuration
│   └── components/   # Reusable UI components
└── rules/            # Configuration loading
```

**Design Pattern**: Ports & Adapters (Hexagonal Architecture)
- Domain logic is pure Python with no I/O dependencies
- Services orchestrate domain logic with adapters
- UI layer consumes services through a `ServiceContext`

## Quick Start

### Prerequisites
- Python 3.12+
- pip

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/little-research-lab.git
cd little-research-lab

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Run the application
flet run --web src/ui/main.py
```

Open http://localhost:8550 in your browser.

### Bootstrap Admin Account

Set environment variables before first run:
```bash
export LRL_ADMIN_EMAIL="admin@example.com"
export LRL_ADMIN_PASSWORD="your-secure-password"
```

Or the system will prompt you on first run.

## Deployment

See [DEPLOY.md](DEPLOY.md) for detailed Fly.io deployment instructions.

### Quick Deploy to Fly.io

```bash
# Install Fly CLI and login
fly auth login

# Create app and volume
fly apps create your-app-name
fly volumes create lrl_data --size 1 --region iad

# Set secrets
fly secrets set LRL_ADMIN_EMAIL=admin@yourdomain.com
fly secrets set LRL_ADMIN_PASSWORD=your-secure-password

# Deploy
fly deploy
```

## Configuration

Configuration is managed through `rules.yaml`:

```yaml
site:
  title: "My Research Lab"
  tagline: "Exploring ideas"

security:
  allowed_upload_types:
    - image/png
    - image/jpeg
    - application/pdf
  max_upload_size_mb: 10
  rate_limits:
    uploads_per_hour: 20
```

## Development

### Run Quality Gates

```bash
python scripts/run_quality_gates.py
```

This runs:
- **Ruff** - Linting and formatting
- **Mypy** - Type checking (strict mode)
- **Pytest** - Unit and integration tests

### Run Tests Only

```bash
pytest tests/
```

### Project Structure

| Directory | Purpose |
|-----------|---------|
| `src/` | Application source code |
| `tests/` | Test suite |
| `migrations/` | Database migrations |
| `scripts/` | Development utilities |
| `docs/` | Additional documentation |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with [Flet](https://flet.dev) | Deployed on [Fly.io](https://fly.io)
