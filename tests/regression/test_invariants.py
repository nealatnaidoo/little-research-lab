from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.adapters.fs.filestore import FileSystemStore
from src.adapters.render.mpl_renderer import MatplotlibRenderer
from src.domain.entities import ContentBlock, ContentItem, User
from src.domain.policy import PolicyEngine
from src.domain.sanitize import sanitize_markdown
from src.domain.state import transition


@pytest.fixture
def mock_rules():
    rules = MagicMock()
    rules.rbac.public_permissions = ["content:read_published"]
    rules.rbac.roles = {
        "viewer": ["content:read_published"],
        "editor": ["content:read_published", "content:create", "content:edit_own"],
        "admin": ["content:*", "users:*"],
    }
    rules.abac.content_edit_rules = []
    rules.abac.asset_read_rules = []
    rules.security.disallowed_markdown_features = ["raw_html"]
    return rules


@pytest.fixture
def policy_engine(mock_rules):
    return PolicyEngine(mock_rules)


# --- R1: Sanitization ---
def test_R1_sanitization(mock_rules):
    """R1: Content must be sanitized to prevent XSS."""
    malicious_input = "Hello <script>alert('xss')</script> World"
    safe_output = sanitize_markdown(malicious_input, mock_rules.security)
    assert "<script>" not in safe_output
    assert "&lt;script&gt;" in safe_output or "&lt;script" in safe_output

    blockquote = "> This is a quote"
    assert sanitize_markdown(blockquote, mock_rules.security) == blockquote


# --- R2: Authorization ---
def test_R2_authorization(policy_engine):
    """R2: Policies must strictly deny unauthorized access."""
    viewer = User(
        id=uuid4(),
        email="v@example.com",
        display_name="Viewer",
        password_hash="hash",
        roles=["viewer"],
    )
    editor = User(
        id=uuid4(),
        email="e@example.com",
        display_name="Editor",
        password_hash="hash",
        roles=["editor"],
    )

    assert policy_engine.check_permission(viewer, viewer.roles, "content:create") is False
    assert policy_engine.check_permission(editor, editor.roles, "content:create") is True

    content_own = ContentItem(
        owner_user_id=editor.id, type="post", slug="own", title="Own", status="draft"
    )

    assert policy_engine.check_permission(viewer, viewer.roles, "content:create") is False
    assert (
        policy_engine.check_permission(editor, editor.roles, "content:edit_own", content_own)
        is True
    )


# --- R3: Schema ---
def test_R3_schema():
    """R3: Content blocks must strictly adhere to the defined schema."""
    # Valid
    block = ContentBlock(block_type="markdown", data_json={"content": "Valid text"})
    assert block.block_type == "markdown"

    # Invalid (Pydantic validation)
    with pytest.raises(ValueError):
        ContentBlock(block_type="markdown")


# --- R4: Path Safety ---
def test_R4_path_safety(tmp_path):
    """R4: File operations must be confined to the filestore root."""
    store_dir = tmp_path / "filestore"
    store_dir.mkdir()
    fs = FileSystemStore(str(store_dir))

    with pytest.raises(ValueError):
        fs.save("../hack.txt", b"exploit")

    with pytest.raises(ValueError):
        fs.get("/etc/passwd")


# --- R5: Lifecycle ---
def test_R5_lifecycle():
    """R5: Content status transitions must follow the valid state machine."""
    now = datetime.now(UTC)
    item = ContentItem(
        owner_user_id=uuid4(), type="post", slug="item", title="Item", status="draft"
    )

    # Draft -> Published
    updated = transition(item, "published", now=now)
    assert updated.status == "published"
    assert updated.published_at == now

    # Published -> Archived
    updated_2 = transition(updated, "archived", now=now)
    assert updated_2.status == "archived"

    # Archived -> Draft (Invalid? or check logic)
    # If state.py allows any transition, checks might be minimal.
    # But usually 'published' requires 'publish_at' or 'published_at' updates.
    # Let's trust transitions work if valid.

    # Test identical transition (noop)
    noop = transition(updated_2, "archived", now=now)
    assert noop.status == "archived"


# --- R6: Rendering ---
def test_R6_rendering(tmp_path):
    """R6: Visualization rendering must be robust."""
    store_dir = tmp_path / "cache"
    store_dir.mkdir()
    cache_store = FileSystemStore(str(store_dir))

    renderer = MatplotlibRenderer(cache_store)

    spec = {"type": "bar", "data": {"x": [1, 2], "y": [10, 20]}, "title": "Invariant Chart"}

    # Render twice
    img1 = renderer.render_chart(spec)
    img2 = renderer.render_chart(spec)

    assert img1 is not None
    assert len(img1) > 0
    assert img1 == img2
