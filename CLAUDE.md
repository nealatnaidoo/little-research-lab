# Little Research Lab - Claude Code Instructions

## Project Overview

A content publishing platform with:
- **Frontend**: Next.js 16 + Tailwind CSS 4 + shadcn/ui + TipTap editor
- **Backend**: FastAPI + SQLite (Python)
- **Deployment**: Fly.io (separate apps for frontend and backend)

## Key Architecture Decisions

### Frontend (Next.js)
- Uses App Router with server components
- TipTap for rich text editing (stores JSON, renders with `@tiptap/html`)
- Content pages use `force-dynamic` for fresh data
- Tailwind v4 with `@plugin` directive for plugins

### Backend (FastAPI)
- Atomic component pattern in `src/components/`
- Ports & Adapters architecture
- Content stored as `blocks` array with `data_json.tiptap`

### Data Flow
Frontend `body` (TipTap JSON) ↔ `ContentService` transforms ↔ Backend `blocks` array

## Common Tasks

### Deploy Frontend
```bash
cd frontend && fly deploy
```

### Deploy Backend
```bash
fly deploy  # from project root
```

### Run Quality Gates
```bash
cd frontend && npm run build && npm run lint
```

## Known Patterns

### Rich Text Editor
- Toolbar uses Button components (not Toggle) for reliability
- Editor in `components/editor/RichTextEditor.tsx`
- Renderer in `components/content/block-renderer.tsx`
- Both need same TipTap extensions (StarterKit, Link, Image)

### Content Service Transformation
```typescript
// ContentService.ts transforms between:
// Frontend: { body: TipTapJSON, description: string }
// Backend:  { blocks: [{block_type, data_json}], summary: string }
```

### Dynamic vs Static Pages
- Homepage (`/`): `force-dynamic` - always fresh
- Admin pages: static with client-side data fetching
- Article pages (`/p/[slug]`): dynamic

## Project Files

| File | Purpose |
|------|---------|
| `little-research-lab-v3_spec.md` | Full specification |
| `little-research-lab-v3_tasklist.md` | Task tracking |
| `little-research-lab-v3_evolution.md` | Drift/change log |
| `little-research-lab-v3_decisions.md` | Architecture decisions |
| `DEPLOY.md` | Deployment instructions |

## Lessons Reference

See `/Users/naidooone/Documents/development prompts/devlessons.md` for:
- Section 15: TipTap integration
- Section 16: Next.js static/dynamic rendering
- Section 17: Tailwind v4 plugins
- Section 18: Frontend-backend schema alignment

## Evolution Log

Current entries:
- EV-0001: Atomic component migration
- EV-0002: Shell layer migration
- EV-0003: Frontend integration fixes (TipTap, toolbar, caching, typography)
