# research-lab-bio_decisions.md

### D-0001
- Context: Need a simple, secure link-in-bio microsite with scheduling and collaboration.
- Options:
  1) Use a full CMS (e.g., WordPress/Strapi) and embed links
  2) Custom Python+Flet app with minimal CMS capabilities
- Decision: Option 2.
- Rationale: Fits existing skills, keeps UX tight, enables bespoke chart/canvas blocks.
- Implications: Must implement auth, RBAC, scheduling, asset handling securely.
- Rollback: Pivot to a hosted CMS if maintenance burden becomes too high.

### D-0002
- Context: Persistence layer choice.
- Options: SQLite vs Postgres.
- Decision: Start with SQLite, abstract behind repo ports.
- Rationale: Minimal ops; easy backups.
- Implications: Must manage concurrency carefully; provide Postgres swap path.
- Rollback: Implement Postgres adapter and migrate.

### D-0003
- Context: Scheduling without background workers.
- Options: Always-on worker vs publish-on-access + CLI cron job.
- Decision: publish-on-access + CLI `publish_due`.
- Rationale: Works on simple hosting; reduces moving parts.
- Implications: Must ensure idempotence and correctness on restarts.
- Rollback: Add worker later via adapter.

### D-0004 (needs confirmation)
- Context: Collaboration invites.
- Options: Email-based invites vs manual token sharing.
- Decision: Start with manual invite tokens; email adapter optional later.
- Rationale: Avoid dependency on SMTP/API initially.
- Implications: UX slightly less smooth.
- Rollback: Add email adapter and toggle via rules/env.
