# Little Research Lab — UI Development Restart Prompt

**Date:** 2026-01-12
**Focus:** Continue UI development from the correct entry points

---

## Project Architecture

### Stack Overview
| Layer | Technology | Location |
|-------|------------|----------|
| Backend API | FastAPI (Python) | `src/api/routes/` |
| Business Logic | Atomic Components | `src/components/*/component.py` |
| Frontend | Next.js 14 (App Router) | `frontend/` |
| UI Components | shadcn/ui + Tailwind | `frontend/components/ui/` |
| State/API | OpenAPI client | `frontend/lib/api.ts` |

### Key Entry Points

**Backend (Python):**
```
src/
├── api/routes/           # FastAPI endpoints
│   ├── admin_settings.py # Settings API (GET/PUT)
│   ├── admin_assets.py   # Assets API
│   ├── admin_schedule.py # Scheduling API
│   ├── admin_analytics.py# Analytics API
│   └── ...
├── components/           # Atomic business logic
│   ├── settings/         # SettingsService
│   ├── assets/           # AssetService
│   ├── scheduler/        # SchedulerService
│   ├── analytics/        # AnalyticsService
│   └── ...
└── core/entities.py      # Domain models
```

**Frontend (Next.js):**
```
frontend/
├── app/
│   ├── admin/
│   │   ├── layout.tsx       # Admin shell (sidebar, auth)
│   │   ├── page.tsx         # Dashboard
│   │   ├── settings/page.tsx# Settings (PLACEHOLDER)
│   │   ├── content/         # Content management
│   │   ├── assets/          # Asset management
│   │   └── users/           # User management
│   ├── login/page.tsx       # Login page
│   └── p/[slug]/page.tsx    # Public post page
├── components/
│   ├── ui/                  # shadcn/ui primitives
│   ├── content/editor.tsx   # Content editor
│   ├── assets/upload-dialog.tsx
│   └── auth/login-form.tsx
└── lib/
    └── api.ts               # Generated OpenAPI client
```

---

## UI Tasks (Priority Order)

### Ready to Implement

| ID | Task | API Ready | Entry Point |
|----|------|-----------|-------------|
| **T-0013** | Admin Settings UI | `/api/admin/settings` | `frontend/app/admin/settings/page.tsx` |
| **T-0030** | Admin Schedule Calendar API | Need to implement | `src/api/routes/admin_schedule.py` |
| **T-0031** | Admin Calendar UI | After T-0030 | `frontend/app/admin/schedule/page.tsx` |
| **T-0037** | Admin Analytics UI | `/api/admin/analytics/*` | `frontend/app/admin/analytics/page.tsx` |

### Blocked (Require Prerequisites)

| ID | Task | Blocked By | Notes |
|----|------|------------|-------|
| T-0020 | Resource(PDF) Editor UI | T-0013 pattern | Use Settings UI as template |
| T-0024 | Rich Text Editor | T-0013 pattern | TipTap/ProseMirror integration |
| T-0025 | Inline Image Insert | T-0024 | Requires editor foundation |
| T-0022 | PDF Viewer Embed | T-0021 (backend) | iOS/Safari fallback needed |

---

## Recommended Starting Task: T-0013 (Settings UI)

### Why Start Here
1. **API is ready:** `/api/admin/settings` endpoints exist
2. **Establishes patterns:** Form handling, API integration, toast notifications
3. **Unblocks others:** T-0020, T-0024 use this as a template
4. **Visible progress:** Immediate user value

### Current State
`frontend/app/admin/settings/page.tsx` is a placeholder:
```tsx
// Current: placeholder cards with "coming soon"
<Card>
    <CardHeader>
        <CardTitle>Site Configuration</CardTitle>
    </CardHeader>
    <CardContent>
        <p>Site configuration coming soon.</p>
    </CardContent>
</Card>
```

### Implementation Requirements
1. **Fetch settings on mount** via `GET /api/admin/settings`
2. **Form with fields:**
   - `site_title` (string)
   - `site_description` (string)
   - `meta_keywords` (string)
   - `og_image_url` (optional string)
   - `twitter_handle` (optional string)
3. **Submit handler** via `PUT /api/admin/settings`
4. **Toast notifications** for success/error
5. **Loading states** during fetch/submit

### Pattern to Follow
```tsx
"use client"

import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { SettingsService } from "@/lib/api"
// ... shadcn/ui imports

export default function SettingsPage() {
    const [loading, setLoading] = useState(true)
    const form = useForm<SettingsFormData>()

    useEffect(() => {
        // Fetch current settings
        SettingsService.getSettings().then(data => {
            form.reset(data)
            setLoading(false)
        }).catch(err => {
            toast.error("Failed to load settings")
        })
    }, [])

    const onSubmit = async (data: SettingsFormData) => {
        try {
            await SettingsService.updateSettings(data)
            toast.success("Settings saved")
        } catch (err) {
            toast.error("Failed to save settings")
        }
    }

    if (loading) return <Skeleton />

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)}>
                {/* Form fields */}
            </form>
        </Form>
    )
}
```

---

## Quality Gates

Run after each task:

```bash
# Backend
cd "/Users/naidooone/Documents/little research lab"
python scripts/quality_gates.py

# Frontend
cd frontend
npm run lint
npm run build
```

---

## API Reference

### Settings API (T-0013)
```
GET  /api/admin/settings     → SettingsResponse
PUT  /api/admin/settings     → SettingsResponse
```

### Schedule Calendar API (T-0030)
```
GET  /api/admin/schedule/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD
     → list[PublishJobResponse]
```

### Analytics API (T-0037)
```
GET  /api/admin/analytics/totals?period=7d
GET  /api/admin/analytics/timeseries?metric=pageviews&period=30d
GET  /api/admin/analytics/top/content?limit=10
GET  /api/admin/analytics/top/sources?limit=10
GET  /api/admin/analytics/top/referrers?limit=10
```

---

## Component Library

The project uses **shadcn/ui** components. Available at `frontend/components/ui/`:
- `button`, `input`, `label`, `form`
- `card`, `table`, `tabs`
- `dialog`, `sheet`, `dropdown-menu`
- `select`, `skeleton`, `separator`
- `toast` (via sonner)

To add new components:
```bash
cd frontend
npx shadcn@latest add [component-name]
```

---

## Session Checklist

Before starting work:
1. [ ] Read this prompt
2. [ ] Check `little-research-lab-v3_tasklist.md` for current status
3. [ ] Verify backend API exists for your UI task
4. [ ] Run quality gates to confirm clean state

When implementing:
1. [ ] Follow existing patterns in `frontend/app/admin/`
2. [ ] Use shadcn/ui components
3. [ ] Add loading and error states
4. [ ] Test with backend running locally

After completing:
1. [ ] Run frontend lint/build
2. [ ] Run backend quality gates
3. [ ] Update tasklist with evidence
4. [ ] Commit with descriptive message

---

## Quick Start Commands

```bash
# Start backend
cd "/Users/naidooone/Documents/little research lab"
uvicorn src.api.main:app --reload --port 8000

# Start frontend (separate terminal)
cd frontend
npm run dev
# → http://localhost:3000

# Run all quality gates
python scripts/quality_gates.py
```

---

## Lessons Applied

From the atomic refactoring (2026-01-12):
- **Atomic components:** Business logic in `src/components/*/component.py`
- **Deterministic core:** No `datetime.utcnow()` in components; use injected `TimePort`
- **Re-exports:** Import from `src/components/X` not `src/components/X/_impl`
- **Quality gates after every task:** lint, format, types, tests
- **TDD where applicable:** Backend has comprehensive tests; UI uses manual verification

For detailed lessons, see `/Users/naidooone/Documents/development prompts/devlessons.md`
