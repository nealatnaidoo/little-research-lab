"""
NewsletterService component (C10).

Functional core for newsletter subscription management.
Implements double opt-in flow with secure token generation.

Spec refs: E16.1, E16.2, E16.3, TA-0074-0083, SM3, I8, I11, R7

Key behaviors:
- Double opt-in (pending → confirmed via email link)
- Cryptographic tokens (secrets.token_urlsafe)
- Token expiry (48h for confirmation)
- Single-use confirmation tokens
- Permanent unsubscribe tokens
- Disposable email rejection
- Rate limiting per IP

Invariants:
- I8: Double opt-in required (status starts as pending)
- I11: No spam (disposable domain + rate limit check)
- R7: Newsletter emails only to confirmed subscribers
"""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.components.newsletter.models import (
    ConfirmInput,
    ConfirmOutput,
    GenerateTokenOutput,
    NewsletterConfig,
    NewsletterSubscriber,
    SubscribeInput,
    SubscribeOutput,
    SubscriberStatus,
    UnsubscribeInput,
    UnsubscribeOutput,
    ValidateEmailOutput,
    ValidationError,
    can_transition,
)
from src.components.newsletter.ports import (
    NewsletterEmailSenderPort,
    NewsletterRepoPort,
    RateLimiterPort,
)

# --- Email Validation Regex (RFC 5322 simplified) ---

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

# Common disposable email domains (default set)
DEFAULT_DISPOSABLE_DOMAINS: set[str] = {
    "10minutemail.com",
    "guerrillamail.com",
    "mailinator.com",
    "tempmail.com",
    "throwaway.email",
    "yopmail.com",
    "temp-mail.org",
    "fakeinbox.com",
    "sharklasers.com",
    "trashmail.com",
}


# --- Pure Functions (Functional Core) ---


def validate_email(
    email: str,
    check_disposable: bool = True,
    disposable_domains: set[str] | None = None,
) -> ValidateEmailOutput:
    """
    Validate email address format and optionally check for disposable domains (TA-0074).

    Args:
        email: Email address to validate
        check_disposable: Whether to check against disposable domains
        disposable_domains: Custom set of disposable domains (optional)

    Returns:
        ValidateEmailOutput with validation results
    """
    errors: list[ValidationError] = []

    # Normalize
    normalized = email.strip().lower() if email else ""

    # Check empty
    if not normalized:
        return ValidateEmailOutput(
            is_valid=False,
            normalized_email=None,
            errors=[ValidationError("EMPTY_EMAIL", "Email address is required", "email")],
        )

    # Check length
    if len(normalized) > 254:
        return ValidateEmailOutput(
            is_valid=False,
            normalized_email=None,
            errors=[ValidationError("EMAIL_TOO_LONG", "Email address is too long", "email")],
        )

    # Check format
    if not EMAIL_REGEX.match(normalized):
        return ValidateEmailOutput(
            is_valid=False,
            normalized_email=None,
            errors=[ValidationError("INVALID_FORMAT", "Invalid email format", "email")],
        )

    # Check disposable domain
    is_disposable = False
    if check_disposable:
        domains = disposable_domains or DEFAULT_DISPOSABLE_DOMAINS
        domain = normalized.split("@")[1] if "@" in normalized else ""
        is_disposable = domain in domains

        if is_disposable:
            errors.append(
                ValidationError(
                    "DISPOSABLE_EMAIL",
                    "Disposable email addresses are not allowed",
                    "email",
                )
            )

    return ValidateEmailOutput(
        is_valid=len(errors) == 0,
        normalized_email=normalized,
        errors=errors,
        is_disposable=is_disposable,
    )


def generate_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure URL-safe token (TA-0077).

    Args:
        length: Number of random bytes (will be base64-encoded)

    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(length)


def generate_confirmation_token(length: int = 32) -> GenerateTokenOutput:
    """
    Generate a confirmation token.

    Args:
        length: Token length in bytes

    Returns:
        GenerateTokenOutput with token
    """
    return GenerateTokenOutput(
        token=generate_token(length),
        expires_at=None,  # Expiry tracked separately
    )


def generate_unsubscribe_token(length: int = 32) -> GenerateTokenOutput:
    """
    Generate an unsubscribe token.

    Unsubscribe tokens don't expire (permanent access).

    Args:
        length: Token length in bytes

    Returns:
        GenerateTokenOutput with token
    """
    return GenerateTokenOutput(
        token=generate_token(length),
        expires_at=None,  # No expiry for unsubscribe tokens
    )


def is_token_expired(
    subscriber: NewsletterSubscriber,
    max_age_hours: int = 48,
    now: datetime | None = None,
) -> bool:
    """
    Check if confirmation token has expired (TA-0078).

    Args:
        subscriber: Subscriber to check
        max_age_hours: Maximum token age in hours
        now: Current time (for testing)

    Returns:
        True if token is expired
    """
    if now is None:
        now = datetime.now(UTC)

    # Token age is based on subscriber creation time
    expiry_time = subscriber.created_at + timedelta(hours=max_age_hours)
    return now > expiry_time


def create_subscriber(
    email: str,
    confirmation_token: str,
    unsubscribe_token: str,
) -> NewsletterSubscriber:
    """
    Create a new subscriber in pending status.

    Args:
        email: Normalized email address
        confirmation_token: One-time confirmation token
        unsubscribe_token: Permanent unsubscribe token

    Returns:
        New NewsletterSubscriber instance
    """
    return NewsletterSubscriber(
        id=uuid4(),
        email=email,
        status=SubscriberStatus.PENDING,
        confirmation_token=confirmation_token,
        unsubscribe_token=unsubscribe_token,
        created_at=datetime.now(UTC),
    )


def confirm_subscriber(
    subscriber: NewsletterSubscriber,
    now: datetime | None = None,
) -> NewsletterSubscriber:
    """
    Confirm a subscriber (transition pending → confirmed).

    Args:
        subscriber: Subscriber to confirm
        now: Current time (for testing)

    Returns:
        Updated subscriber with confirmed status
    """
    if now is None:
        now = datetime.now(UTC)

    return NewsletterSubscriber(
        id=subscriber.id,
        email=subscriber.email,
        status=SubscriberStatus.CONFIRMED,
        confirmation_token=None,  # Clear one-time token
        unsubscribe_token=subscriber.unsubscribe_token,
        created_at=subscriber.created_at,
        confirmed_at=now,
        unsubscribed_at=None,
    )


def unsubscribe_subscriber(
    subscriber: NewsletterSubscriber,
    now: datetime | None = None,
) -> NewsletterSubscriber:
    """
    Unsubscribe a subscriber (transition confirmed → unsubscribed).

    Args:
        subscriber: Subscriber to unsubscribe
        now: Current time (for testing)

    Returns:
        Updated subscriber with unsubscribed status
    """
    if now is None:
        now = datetime.now(UTC)

    return NewsletterSubscriber(
        id=subscriber.id,
        email=subscriber.email,
        status=SubscriberStatus.UNSUBSCRIBED,
        confirmation_token=None,
        unsubscribe_token=subscriber.unsubscribe_token,  # Keep for idempotency
        created_at=subscriber.created_at,
        confirmed_at=subscriber.confirmed_at,
        unsubscribed_at=now,
    )


def build_confirmation_url(
    base_url: str,
    token: str,
    path: str = "/newsletter/confirm",
) -> str:
    """
    Build the confirmation URL for email.

    Args:
        base_url: Site base URL
        token: Confirmation token
        path: URL path for confirmation endpoint

    Returns:
        Full confirmation URL
    """
    base = base_url.rstrip("/")
    return f"{base}{path}?token={token}"


def build_unsubscribe_url(
    base_url: str,
    token: str,
    path: str = "/newsletter/unsubscribe",
) -> str:
    """
    Build the unsubscribe URL for email.

    Args:
        base_url: Site base URL
        token: Unsubscribe token
        path: URL path for unsubscribe endpoint

    Returns:
        Full unsubscribe URL
    """
    base = base_url.rstrip("/")
    return f"{base}{path}?token={token}"


# --- Newsletter Service (Orchestration Layer) ---



# --- Run Handlers (Functional Core) ---


def run_subscribe(
    inp: SubscribeInput,
    repo: NewsletterRepoPort,
    *,
    email_sender: NewsletterEmailSenderPort | None = None,
    rate_limiter: RateLimiterPort | None = None,
    config: NewsletterConfig | None = None,
    disposable_domains: set[str] | None = None,
) -> SubscribeOutput:
    """
    Handle subscription request (Atomic Handler).
    """
    cfg = config or NewsletterConfig()
    
    # Validate email
    validation = validate_email(
        inp.email,
        check_disposable=True,
        disposable_domains=disposable_domains,
    )

    if not validation.is_valid:
        return SubscribeOutput(
            success=False,
            errors=validation.errors,
        )

    email = validation.normalized_email
    if email is None:
        return SubscribeOutput(
            success=False,
            errors=[ValidationError("VALIDATION_ERROR", "Email validation failed", "email")],
        )

    # Check rate limit
    if rate_limiter and inp.ip_address:
        is_allowed, _ = rate_limiter.check_rate_limit(
            key=inp.ip_address,
            limit=cfg.rate_limit_per_ip_per_hour,
            window_seconds=3600,
        )
        if not is_allowed:
            return SubscribeOutput(
                success=False,
                errors=[ValidationError("RATE_LIMIT", "Too many attempts, please try later", None)],
            )
        rate_limiter.record_attempt(inp.ip_address)

    # Check existing subscriber
    existing = repo.get_by_email(email)
    if existing:
        if existing.status == SubscriberStatus.CONFIRMED:
            return SubscribeOutput(
                success=True,  # Idempotent success
                subscriber_id=existing.id,
                needs_confirmation=False,
                already_subscribed=True,
            )
        elif existing.status == SubscriberStatus.PENDING:
            # Resend confirmation
            if email_sender and existing.confirmation_token:
                url = build_confirmation_url(
                    cfg.base_url,
                    existing.confirmation_token,
                    cfg.confirmation_path,
                )
                email_sender.send_confirmation_email(
                    email,
                    url,
                    cfg.site_name,
                )
            return SubscribeOutput(
                success=True,
                subscriber_id=existing.id,
                needs_confirmation=True,
            )

    # Create new subscriber
    confirmation_token = generate_token()
    unsubscribe_token = generate_token()
    subscriber = create_subscriber(email, confirmation_token, unsubscribe_token)
    saved = repo.save(subscriber)

    # Send confirmation email
    if email_sender:
        url = build_confirmation_url(
            cfg.base_url,
            confirmation_token,
            cfg.confirmation_path,
        )
        email_sender.send_confirmation_email(
            email,
            url,
            cfg.site_name,
        )

    return SubscribeOutput(
        success=True,
        subscriber_id=saved.id,
        needs_confirmation=True,
    )


def run_confirm(
    inp: ConfirmInput,
    repo: NewsletterRepoPort,
    *,
    email_sender: NewsletterEmailSenderPort | None = None,
    config: NewsletterConfig | None = None,
) -> ConfirmOutput:
    """
    Handle confirmation request (Atomic Handler).
    """
    cfg = config or NewsletterConfig()

    if not inp.token:
        return ConfirmOutput(
            success=False,
            errors=[ValidationError("MISSING_TOKEN", "Confirmation token is required", None)],
        )

    # Find subscriber by token
    subscriber = repo.get_by_confirmation_token(inp.token)
    if not subscriber:
        return ConfirmOutput(
            success=False,
            errors=[ValidationError("INVALID_TOKEN", "Invalid or expired confirmation link", None)],
        )

    # Check if already confirmed (idempotent)
    if subscriber.status == SubscriberStatus.CONFIRMED:
        return ConfirmOutput(
            success=True,
            subscriber_id=subscriber.id,
            already_confirmed=True,
        )

    # Check token expiry
    if is_token_expired(subscriber, cfg.confirmation_token_expiry_hours):
        return ConfirmOutput(
            success=False,
            errors=[ValidationError("TOKEN_EXPIRED", "Confirmation link has expired", None)],
        )

    # Validate state transition
    if not can_transition(subscriber.status, SubscriberStatus.CONFIRMED):
        return ConfirmOutput(
            success=False,
            errors=[
                ValidationError(
                    "INVALID_STATE",
                    "Cannot confirm subscription in current state",
                    None,
                )
            ],
        )

    # Confirm subscriber
    confirmed = confirm_subscriber(subscriber)
    repo.save(confirmed)

    # Send welcome email
    if email_sender and confirmed.unsubscribe_token:
        url = build_unsubscribe_url(
            cfg.base_url,
            confirmed.unsubscribe_token,
            cfg.unsubscribe_path,
        )
        email_sender.send_welcome_email(
            confirmed.email,
            url,
            cfg.site_name,
        )

    return ConfirmOutput(
        success=True,
        subscriber_id=confirmed.id,
    )


def run_unsubscribe(
    inp: UnsubscribeInput,
    repo: NewsletterRepoPort,
) -> UnsubscribeOutput:
    """
    Handle unsubscribe request (Atomic Handler).
    """
    if not inp.token:
        return UnsubscribeOutput(
            success=False,
            errors=[ValidationError("MISSING_TOKEN", "Unsubscribe token is required", None)],
        )

    # Find subscriber by unsubscribe token
    subscriber = repo.get_by_unsubscribe_token(inp.token)
    if not subscriber:
        return UnsubscribeOutput(
            success=False,
            errors=[ValidationError("INVALID_TOKEN", "Invalid unsubscribe link", None)],
        )

    # Check if already unsubscribed (idempotent)
    if subscriber.status == SubscriberStatus.UNSUBSCRIBED:
        return UnsubscribeOutput(
            success=True,
            already_unsubscribed=True,
        )

    # Validate state transition
    if not can_transition(subscriber.status, SubscriberStatus.UNSUBSCRIBED):
        return UnsubscribeOutput(
            success=False,
            errors=[ValidationError("INVALID_STATE", "Cannot unsubscribe in current state", None)],
        )

    # Unsubscribe
    unsubscribed = unsubscribe_subscriber(subscriber)
    repo.save(unsubscribed)

    return UnsubscribeOutput(success=True)


def run(
    inp: SubscribeInput | ConfirmInput | UnsubscribeInput,
    *,
    repo: NewsletterRepoPort,
    email_sender: NewsletterEmailSenderPort | None = None,
    rate_limiter: RateLimiterPort | None = None,
    config: NewsletterConfig | None = None,
    disposable_domains: set[str] | None = None,
) -> SubscribeOutput | ConfirmOutput | UnsubscribeOutput:
    """
    Main component entry point (Atomic Component Pattern).

    Args:
        inp: Input command
        repo: Repository port (Required)
        email_sender: Email sender port (Optional)
        rate_limiter: Rate limiter port (Optional)
        config: Configuration (Optional)
        disposable_domains: Custom disposable domains (Optional)

    Returns:
        Operation result
    """
    if isinstance(inp, SubscribeInput):
        return run_subscribe(
            inp,
            repo,
            email_sender=email_sender,
            rate_limiter=rate_limiter,
            config=config,
            disposable_domains=disposable_domains,
        )
    elif isinstance(inp, ConfirmInput):
        return run_confirm(
            inp,
            repo,
            email_sender=email_sender,
            config=config,
        )
    elif isinstance(inp, UnsubscribeInput):
        return run_unsubscribe(inp, repo)
    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
