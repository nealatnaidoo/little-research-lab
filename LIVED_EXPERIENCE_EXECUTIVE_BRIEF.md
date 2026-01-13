# Building with AI Agents: A Lived Experience Study

## Executive Summary

This document presents objective data and lessons from building "Little Research Lab" — a production content publishing platform — using AI-assisted development with Claude Code. The project demonstrates how structured AI collaboration can deliver production software in **48 working hours** while maintaining quality gates, capturing institutional knowledge, and enabling rapid iteration.

**Key Business Outcomes:**
- Production deployment in 3 calendar days (48 working hours)
- 25 commits, 26,000+ lines of code across frontend and backend
- 16 atomic components with formal contracts
- 30+ documented lessons preventing future rework
- 100% quality gate compliance at delivery

---

## 1. The Project: What We Built

### Scope
A content publishing platform supporting:
- Rich text editing with TipTap WYSIWYG editor
- PDF resource publishing with versioned assets
- DST-safe scheduling with calendar UI
- Privacy-minimal analytics (no cookies, no PII)
- Admin dashboard with audit logging

### Technical Stack
| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, Tailwind CSS 4, shadcn/ui, TipTap |
| Backend | FastAPI, SQLite, Python |
| Architecture | Ports & Adapters (Hexagonal) |
| Deployment | Fly.io (2 apps: frontend + backend) |
| Testing | Playwright E2E (16 tests), Unit tests (1,265 tests) |

---

## 2. Timeline & Velocity

### Development Phases

```
Day 1 (Jan 11)  [==========] Initial build + Flet UI + first deploy
Day 2 (Jan 12)  [==========] React migration + atomic refactor + E2E tests
Day 3 (Jan 13)  [==========] Integration fixes + QA + production release
```

### Commit Velocity by Phase

| Phase | Duration | Commits | Description |
|-------|----------|---------|-------------|
| Initial Setup | 5 hours | 5 | Dockerfile, deployment, dependencies |
| Framework Migration | 6 hours | 3 | Flet to React/Next.js pivot |
| Atomic Refactor | 4 hours | 4 | 16 components to atomic pattern |
| Integration & QA | 8 hours | 13 | Bug fixes, tests, deployment |

### Objective Metrics

| Metric | Value |
|--------|-------|
| Total development time | ~48 hours |
| Total commits | 25 |
| Code files | 8,691 |
| Lines of code | 26,315 |
| Backend components | 16 (with contracts) |
| Frontend components | 18 |
| E2E tests | 16/16 passing |
| Unit tests | 1,265 passing |
| Deployments | 7 (iterative) |

---

## 3. The Role of Context Window

### What is Context Window?
The "context window" is the amount of information an AI can hold in working memory during a conversation. Like a human developer context-switching, losing context means re-explaining requirements, re-reading code, and losing momentum.

### How We Extended Effective Context

**Strategy: Artifact-Based Memory**

Instead of relying solely on conversational context, we externalized knowledge to files:

| Artifact | Purpose | Update Frequency |
|----------|---------|------------------|
| `devlessons.md` | Lessons learned (30+ entries) | After each major fix |
| `evolution.md` | Drift/scope changes (3 entries) | When requirements change |
| `CLAUDE.md` | Project-specific instructions | On architecture decisions |
| `contract.md` (x16) | Component specifications | On component creation |
| `spec.md` | Full requirements document | Project start |
| `tasklist.md` | Task tracking | Per task completion |

**Result:** New sessions can resume productive work in <5 minutes by reading artifacts instead of reconstructing context from conversation history.

### Context Window Usage Pattern

```
Session 1: Fresh context
├── Read spec.md (requirements)
├── Read devlessons.md (past mistakes)
├── Write code
├── Update artifacts
└── Context exhausted → Session ends

Session 2: Resume with artifacts
├── Read CLAUDE.md (project summary)
├── Read evolution.md (recent changes)
├── Continue where left off
└── No context lost
```

**Key Insight:** Each session produced documentation that enabled the next session. The AI effectively "remembered" across context boundaries through artifacts.

---

## 4. Drift Detection & Guardrails

### What is Drift?
"Drift" occurs when implementation diverges from the plan — adding features that weren't specified, changing architecture mid-stream, or solving the wrong problem. In traditional development, drift is discovered in code review or QA (expensive). With AI agents, drift can accelerate rapidly.

### Our Drift Events (Evolution Log)

| Entry | Date | Trigger | Impact | Resolution |
|-------|------|---------|--------|------------|
| EV-0001 | Jan 12 | Architecture deviation | 36% compliance | Migrated 11 components |
| EV-0002 | Jan 12 | Incomplete migration | Split-brain state | Fixed 36 import paths |
| EV-0003 | Jan 13 | Frontend integration | 5 UI bugs | 6 targeted fixes |

### EV-0001: The 36% Problem

**What Happened:**
The AI wrote code before fully reading the architecture standards document. Result: 11 components implemented with class-based services instead of atomic pattern with `run()` entry points.

**Cost:** 4 hours of remediation (could have been 15 minutes if caught early)

**Guardrail Implemented:**
```
Protocol: "Read coding playbook BEFORE first line of code"
Check: Component compliance audit runs with every quality gate
```

### EV-0002: Split-Brain Architecture

**What Happened:**
After EV-0001 remediation, an external QA review found 5 additional components in a different directory (`src/services/`) that weren't migrated. The codebase had code in two locations doing the same thing.

**Why Internal Checks Missed It:**
- All tests passed (both locations worked)
- No lint errors (both syntactically valid)
- "It still works" bias

**Guardrail Implemented:**
```
Protocol: External QA review after architectural changes
Check: "grep -r 'old_location' src/" must return empty
```

### EV-0003: Integration Mismatch

**What Happened:**
5 frontend bugs discovered during user testing:
1. Published articles showed "Error rendering content"
2. Toolbar buttons didn't respond to clicks
3. Deleted content still appeared (caching)
4. Missing paragraph spacing
5. Data format mismatch

**Pattern:** Each bug was a boundary condition between frontend and backend that wasn't covered by component-level tests.

**Guardrails Implemented:**
- Round-trip integration tests (create → save → fetch → display)
- E2E tests with Playwright
- Dynamic rendering for content pages

---

## 5. Agent Collaboration Model

### Agent Types Used

| Agent | Purpose | When Used |
|-------|---------|-----------|
| **Coding Agent** | Write and modify code | Implementation tasks |
| **QA Reviewer** | Audit code quality | After each phase |
| **Explore Agent** | Search/understand codebase | Research questions |
| **Business Analyst** | Manage artifacts | Spec/tasklist updates |

### Parallel Agent Execution

When multiple independent tasks existed, agents ran in parallel:

```
Example: Create 5 atomic components
├── Agent 1: auth/component.py
├── Agent 2: collab/component.py
├── Agent 3: invite/component.py
├── Agent 4: publish/component.py
└── Agent 5: bootstrap/component.py

Result: 5 components created in ~20 seconds (vs 10+ minutes sequential)
```

### Agent Handoff Protocol

```
Agent A (Coding):
1. Complete task
2. Update tasklist with new paths
3. Run quality gates
4. Document in evolution.md if drift

Agent B (QA):
1. Read evolution.md for context
2. Audit against standards
3. Report issues with file:line references
4. No code changes (report only)

Agent A (Coding):
1. Address QA findings
2. Re-run quality gates
3. Mark task complete
```

---

## 6. Iteration Cycles

### The Task Loop

Every task followed this discipline:

```
1. Mark task "in_progress" in tasklist
2. Read relevant code/contracts
3. Write tests first (TDD)
4. Implement code
5. Run quality gates
   ├── npm run lint (0 errors required)
   ├── npm run build (must succeed)
   └── npx playwright test (all pass)
6. If drift detected → HALT, create EV entry
7. Mark task "done"
8. Commit with evidence
```

### Quality Gate Enforcement

| Gate | Tool | Threshold | Enforcement |
|------|------|-----------|-------------|
| Lint | ESLint | 0 errors | Blocks commit |
| Types | TypeScript | 0 errors | Blocks build |
| E2E Tests | Playwright | 100% pass | Blocks deploy |
| Unit Tests | pytest | 100% pass | Blocks deploy |

### Iteration Statistics

| Metric | Value |
|--------|-------|
| Average commit size | ~1,000 lines |
| Commits with quality gate failures | 0 (blocked) |
| Rework iterations (bug fixes) | 13 commits |
| Feature commits | 12 commits |

---

## 7. Lessons Captured

### Lesson Categories

| Category | Count | Examples |
|----------|-------|----------|
| Framework Selection | 3 | Flet maturity issues, React migration |
| Deployment | 6 | Fly.io volumes, health checks, cold starts |
| Architecture | 8 | Ports/adapters, atomic components, determinism |
| Testing | 4 | TDD per layer, E2E vs unit tests |
| Process | 5 | Task discipline, drift detection |
| Integration | 4 | TipTap, Tailwind v4, Next.js caching |

### Top 5 Lessons by Impact

1. **Read the playbook BEFORE coding**
   - Cost of violation: 4 hours remediation
   - Cost of compliance: 15 minutes upfront

2. **External QA catches what internal checks miss**
   - Split-brain states hide from passing tests
   - Fresh eyes with no context bias

3. **Artifacts extend context window**
   - Documentation enables session handoffs
   - Each session produces knowledge for the next

4. **Different layers need different testing**
   - Domain: Unit tests, property tests
   - Services: Integration tests with fakes
   - UI: E2E tests with Playwright

5. **Force-dynamic for content pages**
   - Static caching shows stale data
   - Content changes need immediate reflection

---

## 8. Quantified Benefits

### Development Velocity

| Approach | Estimated Time | Actual Time | Savings |
|----------|---------------|-------------|---------|
| Traditional development | 2-3 weeks | 48 hours | 70-80% |
| Bug fix cycle | Days | Hours | ~90% |
| Documentation | Often skipped | Integrated | 100% coverage |

### Quality Outcomes

| Metric | Traditional | AI-Assisted |
|--------|-------------|-------------|
| Commits before first deploy | 50+ | 8 |
| Post-deploy bug fixes | Ongoing | 13 (in 8 hours) |
| Architecture documentation | Sparse | 16 contracts |
| Lessons captured | Tribal knowledge | 30+ written |

### Technical Debt

| Measure | Status |
|---------|--------|
| ESLint errors at delivery | 0 |
| TypeScript errors at delivery | 0 |
| E2E test coverage | 16 critical paths |
| Component contracts | 16/16 documented |
| Drift entries resolved | 3/3 |

---

## 9. Implications for Professional Services

### Where This Approach Excels

1. **Greenfield Projects**
   - No existing codebase context to load
   - Can establish conventions from start

2. **Well-Defined Scope**
   - Clear spec enables autonomous execution
   - Ambiguity triggers drift

3. **Rapid Prototyping**
   - Hours to working deployment
   - Iterate with real user feedback

4. **Documentation-First Teams**
   - Artifacts naturally produced
   - Knowledge doesn't live in people's heads

### Where Caution is Needed

1. **Large Existing Codebases**
   - Context window limits how much code AI can "see"
   - Need exploration agents for navigation

2. **Ambiguous Requirements**
   - AI will make assumptions
   - Assumptions may drift from intent

3. **High-Compliance Domains**
   - Security-critical code needs human review
   - AI can introduce subtle vulnerabilities

4. **Team Handoffs**
   - Need artifact hygiene discipline
   - Without docs, next session loses context

### Recommended Team Structure

```
                    ┌─────────────────┐
                    │  Human Lead     │
                    │  (Architect)    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────┴───────┐ ┌────┴────┐ ┌──────┴──────┐
     │ Coding Agents  │ │ QA Agent│ │ BA Agent    │
     │ (Parallel)     │ │ (Audit) │ │ (Artifacts) │
     └────────────────┘ └─────────┘ └─────────────┘
```

**Human Lead Responsibilities:**
- Define success criteria
- Approve architectural decisions
- Review security-sensitive code
- Make scope tradeoffs

**Agent Responsibilities:**
- Execute well-defined tasks
- Maintain quality gates
- Document decisions
- Flag drift for human review

---

## 10. Appendix: Evidence Artifacts

### Project Files
- `little-research-lab-v3_spec.md` - Full specification (377 lines)
- `little-research-lab-v3_evolution.md` - Drift log (3 entries)
- `devlessons.md` - Lessons learned (1,338 lines, 30+ lessons)
- `CLAUDE.md` - Project-specific AI instructions

### Git Evidence
- 25 commits over 3 days
- Each commit references quality gate status
- Commit messages include scope and evidence

### Quality Gate Logs
- E2E: 16/16 tests passing
- Lint: 0 errors, 27 warnings (non-blocking)
- Build: Successful compilation
- Type check: 0 errors

### Live Deployment
- Frontend: https://little-research-lab-web.fly.dev/
- Backend: Fly.io (private API)

---

## 11. Conclusion

This project demonstrates that AI-assisted development with proper guardrails can deliver production software with:

1. **Speed**: 48 hours vs. 2-3 weeks traditional
2. **Quality**: 100% quality gate compliance at delivery
3. **Knowledge**: 30+ lessons captured for future projects
4. **Maintainability**: 16 documented component contracts

The key success factors were:
- **Artifact-based memory** extending effective context
- **Drift detection** catching deviations early
- **Quality gates** enforced at every commit
- **External QA** validating internal assumptions

For professional services teams, this approach offers a path to:
- Faster client delivery
- Higher documentation standards
- Reduced tribal knowledge dependency
- Repeatable quality outcomes

The investment is in **discipline**: reading standards before coding, maintaining artifacts, and respecting quality gates. The return is **velocity without chaos**.

---

*Document generated: 2026-01-13*
*Project: Little Research Lab v3*
*Method: AI-assisted development with Claude Code*
