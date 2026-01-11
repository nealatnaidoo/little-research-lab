# Contributing to Little Research Lab

We welcome contributions! Please follow these guidelines to ensure a smooth process.

## Standards

1.  **Quality Gates**: All PRs must pass `python scripts/run_quality_gates.py`. This checks:
    - Linting (`ruff`)
    - Type Safety (`mypy` strict)
    - Tests (`pytest`)

2.  **Architecture**:
    - Follow the Ports & Adapters architecture.
    - Domain logic goes in `src/domain` (pure Python, no IO).
    - UI logic goes in `src/ui`.
    - I/O goes in `src/adapters`.

3.  **Testing**:
    - Write unit tests for new Domain/Service logic.
    - Integration tests for Adapters.
    - Do not worry about Selenium/UI automation; Manual verification is accepted for Views.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Pull Requests

- Open a PR with a clear description.
- Ensure CI passes.
