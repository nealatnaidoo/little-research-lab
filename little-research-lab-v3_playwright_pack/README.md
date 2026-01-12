# little-research-lab-v3 — Playwright UI Tests (pack)

This pack is generated from the BA v3 artifacts and is designed to be **traceable** to:
- Epics (E#.#)
- Test Assertions (TA-####)
- Regression invariants (R1–R6)

## 1) Prereqs
- Node 20+
- Your app running locally or in a test environment

## 2) Install
```bash
npm i
npm run pw:install
```

## 3) Configure environment
Copy `.env.example` to `.env` and fill in values.

```bash
cp .env.example .env
```

Key vars:
- `BASE_URL` (e.g. http://localhost:3000)
- `ADMIN_EMAIL`, `ADMIN_PASSWORD`

## 4) Run tests
```bash
npm test
npm run test:smoke
npm run test:headed
npm run report
```

## 5) Required `data-testid`s (recommended)
These tests strongly prefer stable test IDs. See:
- `docs/recommended-testids.md`

If your UI does not yet have these, you can either:
- add the test IDs (best), or
- update the locator fallbacks in `tests/fixtures/locators.ts`.

## 6) Notes on determinism
- Tests are written to be parallel-safe.
- Where seeding/cleanup APIs are not confirmed, the tests use unique prefixes and leave TODOs.

