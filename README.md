# Little Research Lab

A modern landing page and content management system built with **React/Next.js** frontend and **FastAPI** backend. Features a premium responsive UI (shadcn/ui + Tailwind CSS), rich content authoring, and secure administration.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![React](https://img.shields.io/badge/react-19+-61dafb.svg)
![Next.js](https://img.shields.io/badge/next.js-16+-black.svg)
![Deploy](https://img.shields.io/badge/deploy-fly.io-blueviolet.svg)

## Features

### Public-Facing
- **Landing Page** - Curated links, featured posts, and about section
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
| Frontend | React 19, Next.js 16, TypeScript, Tailwind CSS 4, shadcn/ui |
| Backend | Python 3.12+, FastAPI (REST API) |
| Database | SQLite |
| Validation | Pydantic v2 |
| Auth | Argon2-cffi, JWT (python-jose), passlib |
| Charts | Matplotlib |
| Deployment | Docker, Fly.io |

## Architecture

```
src/                  # Python backend
├── api/              # FastAPI routes & request/response schemas
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
└── rules/            # Configuration loading

frontend/             # React/Next.js frontend
├── app/              # Next.js App Router pages
├── components/       # shadcn/ui + custom components
├── lib/              # API client, utilities
└── styles/           # Tailwind CSS
```

**Design Pattern**: Ports & Adapters (Hexagonal Architecture)
- Domain logic is pure Python with no I/O dependencies
- Services orchestrate domain logic with adapters
- FastAPI provides REST API consumed by React frontend

## Quick Start

### Prerequisites
- Python 3.12+
- pip

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/little-research-lab.git
cd little-research-lab

# Backend setup
python3 -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -e ".[dev]"

# Set required environment variables
export LAB_SECRET_KEY="your-secret-key-for-jwt"
export LAB_BASE_URL="http://localhost:8000"
export LAB_DATA_DIR="./data"

# Initialize database and seed admin user
python seed_db.py

# Run API server
uvicorn src.api.main:app --reload

# Frontend setup (in another terminal)
cd frontend
npm install
npm run dev
```

- API: http://localhost:8000 (Swagger docs at /docs)
- Frontend: http://localhost:3000

### Default Admin Account

After running `seed_db.py`:
- Email: `admin@example.com`
- Password: `changeme`

**Important:** Change the password after first login in production.

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
fly secrets set LAB_SECRET_KEY="your-secure-secret-key"
fly secrets set LAB_BASE_URL="https://your-app-name.fly.dev"

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

Built with [React](https://react.dev) + [Next.js](https://nextjs.org) + [FastAPI](https://fastapi.tiangolo.com) | Deployed on [Fly.io](https://fly.io)
