# Little Research Lab v2.0 - Retrospective Document

**Date:** January 11, 2026
**Version:** 2.0
**Status:** Deployed to Production

---

## Executive Summary

Little Research Lab has been successfully migrated from a Flet-based monolithic application to a modern, decoupled architecture featuring a **FastAPI REST backend** and **React/Next.js frontend**. Both components are deployed to fly.io and are fully operational.

| Component | Technology | Production URL |
|-----------|------------|----------------|
| Backend API | FastAPI + SQLite | https://little-research-lab.fly.dev |
| Frontend | Next.js 16 + React | https://little-research-lab-web.fly.dev |

---

## Architecture Overview

### Previous Architecture (v1.x)
- Monolithic Flet application
- Server-side rendering with Flet controls
- Session-based authentication
- Tightly coupled UI and business logic

### New Architecture (v2.0)
```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│              https://little-research-lab-web.fly.dev             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Public UI  │  │  Admin UI   │  │  API Client (Generated) │  │
│  │  (SSR/SSG)  │  │  (Client)   │  │  OpenAPI TypeScript     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTPS + JWT Cookies
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend API (FastAPI)                       │
│                https://little-research-lab.fly.dev               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      API Layer                            │   │
│  │  /api/auth  /api/content  /api/assets  /api/users        │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Service Layer                           │   │
│  │  AuthService  ContentService  AssetService  UserService  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Adapter Layer                           │   │
│  │  SQLiteRepository  JWTAuthAdapter  PolicyEngine          │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Persistence                             │   │
│  │  SQLite Database  │  File Storage (Assets)               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principles
- **Ports & Adapters (Hexagonal Architecture)**: Clean separation between domain logic and infrastructure
- **Dependency Injection**: Services receive dependencies via constructor injection
- **RBAC/ABAC Authorization**: Policy-based access control via PolicyEngine
- **Type Safety**: Full type hints in Python, TypeScript on frontend

---

## Features Delivered

### Authentication & Authorization
- [x] JWT token-based authentication with HttpOnly cookies
- [x] OAuth2 password flow (`/api/auth/login`)
- [x] Secure logout with cookie clearing (`/api/auth/logout`)
- [x] Current user endpoint (`/api/auth/me`)
- [x] Development login for testing (`/api/auth/dev/login`)
- [x] Role-based access control (admin, author, viewer)
- [x] Policy-based permissions via YAML rules file

### Content Management
- [x] CRUD operations for content items
- [x] Block-based content structure (text, heading, image, code, quote)
- [x] Content types: post, page, link
- [x] Draft/published status workflow
- [x] Slug-based public URLs
- [x] Publish date scheduling

### Asset Management
- [x] File upload with validation
- [x] Image storage and retrieval
- [x] Asset metadata tracking
- [x] Content-type detection

### User Management
- [x] User CRUD operations
- [x] Role assignment
- [x] Password hashing with Argon2
- [x] Email-based identification

### Public API
- [x] Public home endpoint with posts and links
- [x] Public content by slug
- [x] No authentication required for public endpoints

### Admin Dashboard
- [x] Responsive sidebar navigation
- [x] Dashboard overview page
- [x] Content list with create/edit/delete
- [x] Asset gallery with upload
- [x] User management interface
- [x] Settings page (placeholder)

### Frontend Features
- [x] Server-side rendering for public pages (SEO)
- [x] Client-side rendering for admin (interactivity)
- [x] shadcn/ui component library
- [x] Dark/light mode support via Tailwind
- [x] Toast notifications
- [x] Form validation with Zod
- [x] Block-based content renderer

---

## Technical Implementation

### Backend Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12 | Runtime |
| FastAPI | 0.111.x | Web framework |
| Uvicorn | 0.34.x | ASGI server |
| Pydantic | 2.12.x | Data validation |
| SQLite | 3.x | Database |
| python-jose | 3.5.x | JWT handling |
| Argon2-cffi | 25.x | Password hashing |
| PyYAML | 6.x | Rules configuration |

### Frontend Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| Node.js | 20.x | Runtime |
| Next.js | 16.1.x | React framework |
| React | 19.x | UI library |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Styling |
| shadcn/ui | Latest | Component library |
| Sonner | Latest | Toast notifications |
| Zod | Latest | Schema validation |

### API Endpoints

#### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login with email/password |
| POST | `/api/auth/logout` | Logout and clear cookie |
| GET | `/api/auth/me` | Get current user |
| GET | `/api/auth/dev/login` | Dev-only auto-login |

#### Content
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/content` | List all content |
| GET | `/api/content/{id}` | Get content by ID |
| POST | `/api/content` | Create content |
| PUT | `/api/content/{id}` | Update content |
| DELETE | `/api/content/{id}` | Delete content |

#### Assets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/assets` | List all assets |
| POST | `/api/assets` | Upload asset |
| GET | `/api/assets/{id}/content` | Get asset file |

#### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | List all users |
| GET | `/api/users/{id}` | Get user by ID |
| POST | `/api/users` | Create user |
| PUT | `/api/users/{id}` | Update user |

#### Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/public/home` | Get public posts/links |
| GET | `/api/public/content/{slug}` | Get content by slug |

---

## Deployment Configuration

### Backend (fly.io)
```toml
app = "little-research-lab"
primary_region = "iad"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true

[[mounts]]
  source = "lrl_data"
  destination = "/data"

[env]
  LAB_DATA_DIR = "/data"
  LAB_RULES_PATH = "/app/research-lab-bio_rules.yaml"

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
```

### Frontend (fly.io)
```toml
app = "little-research-lab-web"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"
  [build.args]
    NEXT_PUBLIC_API_URL = "https://little-research-lab.fly.dev"

[http_service]
  internal_port = 3000
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true

[env]
  NEXT_PUBLIC_API_URL = "https://little-research-lab.fly.dev"

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
```

### Environment Variables

#### Backend (Secrets)
| Variable | Description |
|----------|-------------|
| `LAB_SECRET_KEY` | JWT signing key (32+ bytes) |
| `LAB_BASE_URL` | Public URL of the API |

#### Frontend (Build Args)
| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |

---

## Quality Assurance

### Code Quality Tools
- **Ruff**: Linting and formatting (rules: E, F, I, B, UP)
- **Mypy**: Static type checking (strict mode)
- **Pytest**: Unit and integration testing

### Test Coverage
```
tests/
├── unit/
│   ├── test_asset_service.py
│   ├── test_content_service.py
│   ├── test_policy_engine.py
│   └── test_user_service.py
└── integration/
    └── api/
        ├── test_content_routes.py
        └── test_users_routes.py
```

### Quality Gates Passed
- [x] `ruff check src/ tests/` - No lint errors
- [x] `mypy src/` - No type errors
- [x] `pytest tests/` - All tests passing

---

## File Structure

### Backend
```
src/
├── adapters/
│   ├── auth/
│   │   └── crypto.py          # JWTAuthAdapter
│   ├── persistence/
│   │   └── sqlite.py          # SQLiteContentRepository
│   └── policy/
│       └── engine.py          # PolicyEngine (RBAC/ABAC)
├── api/
│   ├── main.py                # FastAPI app entry
│   ├── deps.py                # Dependency injection
│   ├── schemas.py             # Pydantic models
│   └── routes/
│       ├── auth.py
│       ├── content.py
│       ├── assets.py
│       ├── users.py
│       └── public.py
├── app_shell/
│   └── config.py              # Settings & validation
├── domain/
│   └── models.py              # Domain entities
└── services/
    ├── auth.py                # AuthService
    ├── content.py             # ContentService
    ├── asset.py               # AssetService
    └── user.py                # UserService
```

### Frontend
```
frontend/
├── app/
│   ├── layout.tsx             # Root layout
│   ├── page.tsx               # Public home
│   ├── login/
│   │   └── page.tsx           # Login page
│   ├── p/[slug]/
│   │   └── page.tsx           # Public content
│   └── admin/
│       ├── layout.tsx         # Admin layout + nav
│       ├── page.tsx           # Dashboard
│       ├── content/
│       ├── assets/
│       ├── users/
│       └── settings/
├── components/
│   ├── ui/                    # shadcn components
│   ├── auth/
│   │   └── login-form.tsx
│   ├── content/
│   │   └── block-renderer.tsx
│   └── api-config.tsx
├── lib/
│   └── api/                   # Generated API client
├── Dockerfile
├── fly.toml
└── next.config.ts
```

---

## Git History (v2.0)

```
cc4521e Add fly.io deployment for Next.js frontend
b99f943 Add python-jose dependency for JWT auth
9a1ca42 Update deployment config for FastAPI backend
cc76c3b v2.0: Complete React/Next.js migration with FastAPI backend
132bdb1 Configure hatch build to include src directory
e883719 Fix Dockerfile to include README.md for pip install
f137b72 Initial commit: Little Research Lab
```

---

## Access & Credentials

### Production URLs
- **Frontend**: https://little-research-lab-web.fly.dev
- **Backend API**: https://little-research-lab.fly.dev
- **Health Check**: https://little-research-lab.fly.dev/health

### Default Admin Account
| Field | Value |
|-------|-------|
| Email | `admin@example.com` |
| Password | `changeme` |

**⚠️ Change this password immediately in production!**

---

## Known Limitations & Future Work

### Current Limitations
1. **Single SQLite database** - Not suitable for horizontal scaling
2. **No email verification** - Users created without email confirmation
3. **No password reset** - Manual password reset only
4. **Settings page** - Placeholder, not functional
5. **No image optimization** - Assets served as-is
6. **No caching layer** - All requests hit the database

### Recommended Next Steps
1. Add password reset flow with email
2. Implement site settings (title, description, etc.)
3. Add image optimization/thumbnails
4. Consider PostgreSQL for production scale
5. Add Redis caching for frequently accessed content
6. Implement content versioning/history
7. Add analytics/view counting
8. Implement RSS feed for posts

---

## Conclusion

Little Research Lab v2.0 represents a complete architectural overhaul, moving from a monolithic Flet application to a modern, maintainable, and scalable decoupled architecture. The system is now:

- **Maintainable**: Clean separation of concerns with Ports & Adapters
- **Testable**: Dependency injection enables easy unit testing
- **Scalable**: Frontend and backend can scale independently
- **Modern**: React/Next.js frontend with TypeScript
- **Secure**: JWT authentication, RBAC authorization, CORS protection
- **Deployable**: Containerized with Docker, deployed to fly.io

The platform is ready for content creation and can be extended with additional features as needed.

---

*Document generated: January 11, 2026*
*Generated with assistance from Claude Opus 4.5*
