# Little Research Lab (Bio)

A "Link-in-Bio" style public landing page application with rich content authoring, asset management, and a premium responsive UI. Built with Python and Flet.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)

## Features

- **Public Landing Page**: Curated links, featured posts, and bio.
- **Content Management**: Write posts/pages with Markdown, Images, and Charts.
- **Premium UI**: Dark/Light mode, responsive navigation, hover effects, and custom themes ("Science/Tech" aesthetics).
- **Security**: Role-Based Access Control (RBAC), secure authentication, and upload validation.
- **Deployment Ready**: Dockerized and configured for Fly.io.

## Quick Start (Local)

1.  **Clone & Install**:
    ```bash
    git clone https://github.com/yourusername/little-research-lab.git
    cd little-research-lab
    python3 -m venv .venv
    source .venv/bin/activate
    pip install .
    ```

2.  **Initialize & Run**:
    ```bash
    # Run the application
    flet run --web src/ui/main.py
    ```
    Open http://localhost:8550.

3.  **Bootstrap Admin**:
    The first run initializes `lrl.db` and the `filestore`.
    Set `LAB_ADMIN_BOOTSTRAP_EMAIL` and `LAB_ADMIN_BOOTSTRAP_PASSWORD` env vars to auto-create an owner, or follow CLI prompts if implemented.
    *Default dev credentials (if using seeded dev DB)*: `admin@example.com` / `admin123` (check `src/services/bootstrap.py` logic).

## Deployment (Fly.io)

1.  **Install Fly CLI** and login.
2.  **Launch**:
    ```bash
    fly launch --no-deploy
    # Edit fly.toml if needed
    fly deploy
    ```
3.  **Secrets**:
    ```bash
    fly secrets set LAB_SECRET_KEY="your-secure-random-string"
    ```

## Development

- **Run Quality Gates**:
    ```bash
    python scripts/run_quality_gates.py
    ```
    This runs `ruff`, `mypy`, and `pytest`.

- **Architecture**:
    Detailed in `docs/` and `artifacts/`.
    - `src/domain`: Core logic & entities.
    - `src/ui`: Flet views & components.
    - `src/ports`: Interfaces.
    - `src/adapters`: Implementations.

## License

MIT License. See [LICENSE](LICENSE).
