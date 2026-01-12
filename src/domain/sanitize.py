import html

from src.rules.models import SecurityRules


def sanitize_markdown(text: str, rules: SecurityRules) -> str:
    """
    Sanitize markdown text based on security rules.
    If 'raw_html' is in disallowed_features, all HTML tags are escaped.
    """
    if "raw_html" in rules.disallowed_markdown_features:
        # We use html.escape to neutralize tags.
        # However, html.escape also escapes '>', which can break markdown blockquotes.
        # Since we are escaping '<', strict HTML tags cannot start, so '>' is generally safe
        # to leave unescaped to preserve blockquotes.
        escaped = html.escape(text, quote=False)
        return escaped.replace("&gt;", ">")

    return text
