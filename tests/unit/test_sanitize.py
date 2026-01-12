import pytest

from src.domain.sanitize import sanitize_markdown
from src.rules.models import CsrfRules, SecurityRules


@pytest.fixture
def strict_rules():
    return SecurityRules(
        fail_fast_on_invalid_rules=True,
        allowed_link_protocols=["https"],
        disallowed_markdown_features=["raw_html"],
        csrf=CsrfRules(enabled=True, mode="token"),
    )


@pytest.fixture
def loose_rules():
    return SecurityRules(
        fail_fast_on_invalid_rules=True,
        allowed_link_protocols=["https"],
        disallowed_markdown_features=[],
        csrf=CsrfRules(enabled=True, mode="token"),
    )


def test_sanitize_no_html_allowed(strict_rules):
    dangerous = "<script>alert('xss')</script>"
    safe = sanitize_markdown(dangerous, strict_rules)
    assert "&lt;script>" in safe
    assert "<script>" not in safe


def test_sanitize_preserves_markdown_bold(strict_rules):
    md = "**bold**"
    safe = sanitize_markdown(md, strict_rules)
    assert safe == "**bold**"


def test_sanitize_preserves_blockquote(strict_rules):
    # This ensures our `replace("&gt;", ">")` hack works
    md = "> quote"
    safe = sanitize_markdown(md, strict_rules)
    assert safe == "> quote"


def test_sanitize_allows_html_if_rule_missing(loose_rules):
    dangerous = "<b>bold</b>"
    safe = sanitize_markdown(dangerous, loose_rules)
    assert safe == "<b>bold</b>"
