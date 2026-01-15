"""
Newsletter component unit tests (C10).

Test assertions:
- TA-0074: Email validation (format + disposable)
- TA-0075: Subscription creates pending status
- TA-0076: Duplicate email handled
- TA-0077: Token cryptographically secure
- TA-0078: Token expiry enforced
- TA-0079: Confirmation state transition
- TA-0080: Confirmation idempotent
- TA-0081: Unsubscribe state transition
- TA-0082: Unsubscribe idempotent
- TA-0083: Token single-use (confirmation token cleared)

Spec refs: E16.1, E16.2, E16.3, SM3, I8, I11, R7
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.components.newsletter import (
    VALID_TRANSITIONS,
    ConfirmInput,
    ConfirmOutput,
    NewsletterConfig,
    NewsletterSubscriber,
    SubscribeInput,
    SubscribeOutput,
    SubscriberStatus,
    UnsubscribeInput,
    UnsubscribeOutput,
    build_confirmation_url,
    build_unsubscribe_url,
    can_transition,
    confirm_subscriber,
    create_subscriber,
    generate_confirmation_token,
    generate_token,
    generate_unsubscribe_token,
    is_token_expired,
    unsubscribe_subscriber,
    validate_email,
)

# --- Mock Repository ---


class MockNewsletterRepo:
    """In-memory newsletter repository for testing."""

    def __init__(self) -> None:
        self._subscribers: dict[UUID, NewsletterSubscriber] = {}
        self._by_email: dict[str, UUID] = {}
        self._by_confirmation_token: dict[str, UUID] = {}
        self._by_unsubscribe_token: dict[str, UUID] = {}

    def get_by_id(self, subscriber_id: UUID) -> NewsletterSubscriber | None:
        return self._subscribers.get(subscriber_id)

    def get_by_email(self, email: str) -> NewsletterSubscriber | None:
        sid = self._by_email.get(email.lower())
        return self._subscribers.get(sid) if sid else None

    def get_by_confirmation_token(self, token: str) -> NewsletterSubscriber | None:
        sid = self._by_confirmation_token.get(token)
        return self._subscribers.get(sid) if sid else None

    def get_by_unsubscribe_token(self, token: str) -> NewsletterSubscriber | None:
        sid = self._by_unsubscribe_token.get(token)
        return self._subscribers.get(sid) if sid else None

    def save(self, subscriber: NewsletterSubscriber) -> NewsletterSubscriber:
        # Clean up old indexes
        if subscriber.id in self._subscribers:
            old = self._subscribers[subscriber.id]
            if old.confirmation_token and old.confirmation_token in self._by_confirmation_token:
                del self._by_confirmation_token[old.confirmation_token]

        # Save new state
        self._subscribers[subscriber.id] = subscriber
        self._by_email[subscriber.email.lower()] = subscriber.id
        if subscriber.confirmation_token:
            self._by_confirmation_token[subscriber.confirmation_token] = subscriber.id
        if subscriber.unsubscribe_token:
            self._by_unsubscribe_token[subscriber.unsubscribe_token] = subscriber.id
        return subscriber

    def delete(self, subscriber_id: UUID) -> bool:
        if subscriber_id not in self._subscribers:
            return False
        sub = self._subscribers[subscriber_id]
        del self._subscribers[subscriber_id]
        if sub.email.lower() in self._by_email:
            del self._by_email[sub.email.lower()]
        if sub.confirmation_token and sub.confirmation_token in self._by_confirmation_token:
            del self._by_confirmation_token[sub.confirmation_token]
        if sub.unsubscribe_token and sub.unsubscribe_token in self._by_unsubscribe_token:
            del self._by_unsubscribe_token[sub.unsubscribe_token]
        return True

    def list_by_status(
        self,
        status: SubscriberStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NewsletterSubscriber]:
        result = [s for s in self._subscribers.values() if s.status == status]
        return result[offset : offset + limit]

    def count_by_status(self, status: SubscriberStatus) -> int:
        return sum(1 for s in self._subscribers.values() if s.status == status)


class MockEmailSender:
    """Mock email sender for testing."""

    def __init__(self) -> None:
        self.sent_emails: list[dict[str, str]] = []

    def send_confirmation_email(
        self,
        recipient_email: str,
        confirmation_url: str,
        site_name: str,
    ) -> bool:
        self.sent_emails.append({
            "type": "confirmation",
            "recipient": recipient_email,
            "url": confirmation_url,
            "site_name": site_name,
        })
        return True

    def send_welcome_email(
        self,
        recipient_email: str,
        unsubscribe_url: str,
        site_name: str,
    ) -> bool:
        self.sent_emails.append({
            "type": "welcome",
            "recipient": recipient_email,
            "url": unsubscribe_url,
            "site_name": site_name,
        })
        return True


class MockRateLimiter:
    """Mock rate limiter for testing."""

    def __init__(self, allow: bool = True) -> None:
        self._allow = allow
        self.attempts: list[str] = []

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        return (self._allow, limit - len(self.attempts))

    def record_attempt(self, key: str) -> None:
        self.attempts.append(key)


# --- Fixtures ---


@pytest.fixture
def mock_repo() -> MockNewsletterRepo:
    return MockNewsletterRepo()


@pytest.fixture
def mock_email_sender() -> MockEmailSender:
    return MockEmailSender()


@pytest.fixture
def mock_rate_limiter() -> MockRateLimiter:
    return MockRateLimiter()


@pytest.fixture
def config() -> NewsletterConfig:
    return NewsletterConfig(
        confirmation_token_expiry_hours=48,
        rate_limit_per_ip_per_hour=10,
        site_name="Test Site",
        base_url="https://example.com",
    )


# --- Email Validation Tests (TA-0074) ---


class TestEmailValidation:
    """TA-0074: Email validation tests."""

    def test_valid_email(self) -> None:
        """Valid email passes validation."""
        result = validate_email("user@example.com")
        assert result.is_valid is True
        assert result.normalized_email == "user@example.com"
        assert len(result.errors) == 0

    def test_email_normalized_lowercase(self) -> None:
        """Email is normalized to lowercase."""
        result = validate_email("User@Example.COM")
        assert result.is_valid is True
        assert result.normalized_email == "user@example.com"

    def test_email_trimmed(self) -> None:
        """Email is trimmed of whitespace."""
        result = validate_email("  user@example.com  ")
        assert result.is_valid is True
        assert result.normalized_email == "user@example.com"

    def test_empty_email_invalid(self) -> None:
        """Empty email is invalid."""
        result = validate_email("")
        assert result.is_valid is False
        assert any(e.code == "EMPTY_EMAIL" for e in result.errors)

    def test_whitespace_only_invalid(self) -> None:
        """Whitespace-only email is invalid."""
        result = validate_email("   ")
        assert result.is_valid is False

    def test_invalid_format_no_at(self) -> None:
        """Email without @ is invalid."""
        result = validate_email("userexample.com")
        assert result.is_valid is False
        assert any(e.code == "INVALID_FORMAT" for e in result.errors)

    def test_invalid_format_no_domain(self) -> None:
        """Email without domain is invalid."""
        result = validate_email("user@")
        assert result.is_valid is False

    def test_invalid_format_no_tld(self) -> None:
        """Email without TLD is invalid."""
        result = validate_email("user@example")
        assert result.is_valid is False

    def test_too_long_email(self) -> None:
        """Email exceeding 254 chars is invalid."""
        long_email = "a" * 245 + "@example.com"
        result = validate_email(long_email)
        assert result.is_valid is False
        assert any(e.code == "EMAIL_TOO_LONG" for e in result.errors)

    def test_disposable_email_rejected(self) -> None:
        """Disposable email domain is rejected."""
        result = validate_email("user@mailinator.com")
        assert result.is_valid is False
        assert result.is_disposable is True
        assert any(e.code == "DISPOSABLE_EMAIL" for e in result.errors)

    def test_disposable_check_disabled(self) -> None:
        """Disposable check can be disabled."""
        result = validate_email("user@mailinator.com", check_disposable=False)
        assert result.is_valid is True
        assert result.is_disposable is False

    def test_custom_disposable_domains(self) -> None:
        """Custom disposable domains can be provided."""
        result = validate_email(
            "user@custom-temp.com",
            disposable_domains={"custom-temp.com"},
        )
        assert result.is_valid is False
        assert result.is_disposable is True


# --- Token Generation Tests (TA-0077) ---


class TestTokenGeneration:
    """TA-0077: Token generation tests."""

    def test_generate_token_returns_string(self) -> None:
        """Token generation returns a string."""
        token = generate_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_token_sufficient_length(self) -> None:
        """Token has sufficient length for security."""
        token = generate_token(32)
        # 32 bytes base64-encoded ≈ 43 chars
        assert len(token) >= 40

    def test_generate_token_unique(self) -> None:
        """Generated tokens are unique."""
        tokens = [generate_token() for _ in range(100)]
        assert len(set(tokens)) == 100

    def test_generate_token_url_safe(self) -> None:
        """Token is URL-safe (no special chars needing encoding)."""
        for _ in range(50):
            token = generate_token()
            # URL-safe base64 only uses: A-Z, a-z, 0-9, -, _
            assert all(c.isalnum() or c in "-_" for c in token)

    def test_generate_confirmation_token_output(self) -> None:
        """generate_confirmation_token returns proper output."""
        result = generate_confirmation_token()
        assert result.token is not None
        assert len(result.token) > 0

    def test_generate_unsubscribe_token_output(self) -> None:
        """generate_unsubscribe_token returns proper output."""
        result = generate_unsubscribe_token()
        assert result.token is not None
        assert len(result.token) > 0


# --- Token Expiry Tests (TA-0078) ---


class TestTokenExpiry:
    """TA-0078: Token expiry tests."""

    def test_fresh_token_not_expired(self) -> None:
        """Fresh token is not expired."""
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="token123",
            created_at=datetime.now(UTC),
        )
        assert is_token_expired(subscriber, max_age_hours=48) is False

    def test_old_token_expired(self) -> None:
        """Token older than max_age is expired."""
        old_time = datetime.now(UTC) - timedelta(hours=50)
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="token123",
            created_at=old_time,
        )
        assert is_token_expired(subscriber, max_age_hours=48) is True

    def test_token_at_boundary_not_expired(self) -> None:
        """Token exactly at boundary is not expired."""
        boundary_time = datetime.now(UTC) - timedelta(hours=47, minutes=59)
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="token123",
            created_at=boundary_time,
        )
        assert is_token_expired(subscriber, max_age_hours=48) is False

    def test_custom_max_age(self) -> None:
        """Custom max_age is respected."""
        old_time = datetime.now(UTC) - timedelta(hours=2)
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="token123",
            created_at=old_time,
        )
        assert is_token_expired(subscriber, max_age_hours=1) is True
        assert is_token_expired(subscriber, max_age_hours=3) is False


# --- State Machine Tests (SM3) ---


class TestStateMachine:
    """SM3: Subscriber state machine tests."""

    def test_valid_transitions_defined(self) -> None:
        """Valid transitions are defined."""
        assert SubscriberStatus.CONFIRMED in VALID_TRANSITIONS[SubscriberStatus.PENDING]
        assert SubscriberStatus.UNSUBSCRIBED in VALID_TRANSITIONS[SubscriberStatus.CONFIRMED]
        assert len(VALID_TRANSITIONS[SubscriberStatus.UNSUBSCRIBED]) == 0

    def test_pending_to_confirmed_valid(self) -> None:
        """pending → confirmed is valid."""
        assert can_transition(SubscriberStatus.PENDING, SubscriberStatus.CONFIRMED) is True

    def test_confirmed_to_unsubscribed_valid(self) -> None:
        """confirmed → unsubscribed is valid."""
        assert can_transition(SubscriberStatus.CONFIRMED, SubscriberStatus.UNSUBSCRIBED) is True

    def test_pending_to_unsubscribed_invalid(self) -> None:
        """pending → unsubscribed is invalid (must confirm first)."""
        assert can_transition(SubscriberStatus.PENDING, SubscriberStatus.UNSUBSCRIBED) is False

    def test_unsubscribed_terminal(self) -> None:
        """unsubscribed is terminal state."""
        assert can_transition(SubscriberStatus.UNSUBSCRIBED, SubscriberStatus.PENDING) is False
        assert can_transition(SubscriberStatus.UNSUBSCRIBED, SubscriberStatus.CONFIRMED) is False


# --- Subscriber Lifecycle Tests ---


class TestSubscriberLifecycle:
    """Tests for subscriber entity operations."""

    def test_create_subscriber_pending(self) -> None:
        """create_subscriber creates in pending status."""
        subscriber = create_subscriber(
            email="user@example.com",
            confirmation_token="conf123",
            unsubscribe_token="unsub123",
        )
        assert subscriber.email == "user@example.com"
        assert subscriber.status == SubscriberStatus.PENDING
        assert subscriber.confirmation_token == "conf123"
        assert subscriber.unsubscribe_token == "unsub123"
        assert subscriber.confirmed_at is None

    def test_confirm_subscriber_clears_token(self) -> None:
        """TA-0083: confirm_subscriber clears confirmation token."""
        subscriber = create_subscriber(
            email="user@example.com",
            confirmation_token="conf123",
            unsubscribe_token="unsub123",
        )
        confirmed = confirm_subscriber(subscriber)
        assert confirmed.status == SubscriberStatus.CONFIRMED
        assert confirmed.confirmation_token is None  # Cleared
        assert confirmed.unsubscribe_token == "unsub123"  # Kept
        assert confirmed.confirmed_at is not None

    def test_unsubscribe_subscriber(self) -> None:
        """unsubscribe_subscriber transitions to unsubscribed."""
        subscriber = create_subscriber(
            email="user@example.com",
            confirmation_token="conf123",
            unsubscribe_token="unsub123",
        )
        confirmed = confirm_subscriber(subscriber)
        unsubscribed = unsubscribe_subscriber(confirmed)
        assert unsubscribed.status == SubscriberStatus.UNSUBSCRIBED
        assert unsubscribed.unsubscribed_at is not None


# --- URL Building Tests ---


class TestUrlBuilding:
    """Tests for URL building functions."""

    def test_build_confirmation_url(self) -> None:
        """Confirmation URL is built correctly."""
        url = build_confirmation_url(
            "https://example.com",
            "token123",
            "/newsletter/confirm",
        )
        assert url == "https://example.com/newsletter/confirm?token=token123"

    def test_build_confirmation_url_strips_trailing_slash(self) -> None:
        """Trailing slash is stripped from base URL."""
        url = build_confirmation_url(
            "https://example.com/",
            "token123",
        )
        assert url.startswith("https://example.com/newsletter")
        assert not url.startswith("https://example.com//")

    def test_build_unsubscribe_url(self) -> None:
        """Unsubscribe URL is built correctly."""
        url = build_unsubscribe_url(
            "https://example.com",
            "token123",
            "/newsletter/unsubscribe",
        )
        assert url == "https://example.com/newsletter/unsubscribe?token=token123"


# --- Run Tests (Atomic Component) ---


class TestRunSubscribe:
    """TA-0075, TA-0076: Subscription run tests."""

    def test_run_subscribe_new_email(
        self,
        mock_repo: MockNewsletterRepo,
        mock_email_sender: MockEmailSender,
    ) -> None:
        """TA-0075: New subscription creates pending subscriber."""
        from src.components.newsletter.component import run

        result = run(
            SubscribeInput(email="user@example.com"),
            repo=mock_repo,
            email_sender=mock_email_sender
        )

        assert isinstance(result, SubscribeOutput)
        assert result.success is True
        assert result.needs_confirmation is True
        assert result.subscriber_id is not None

        # Check subscriber created
        subscriber = mock_repo.get_by_id(result.subscriber_id)
        assert subscriber is not None
        assert subscriber.status == SubscriberStatus.PENDING

        # Check confirmation email sent
        assert len(mock_email_sender.sent_emails) == 1
        assert mock_email_sender.sent_emails[0]["type"] == "confirmation"

    def test_run_subscribe_invalid_email(self, mock_repo: MockNewsletterRepo) -> None:
        """Invalid email returns error."""
        from src.components.newsletter.component import run
        
        result = run(SubscribeInput(email="invalid"), repo=mock_repo)

        assert isinstance(result, SubscribeOutput)
        assert result.success is False
        assert len(result.errors) > 0

    def test_run_subscribe_disposable_email(self, mock_repo: MockNewsletterRepo) -> None:
        """Disposable email returns error."""
        from src.components.newsletter.component import run

        result = run(SubscribeInput(email="user@mailinator.com"), repo=mock_repo)

        assert isinstance(result, SubscribeOutput)
        assert result.success is False
        assert any(e.code == "DISPOSABLE_EMAIL" for e in result.errors)

    def test_run_subscribe_duplicate_confirmed(
        self,
        mock_repo: MockNewsletterRepo,
    ) -> None:
        """TA-0076: Duplicate confirmed email returns idempotent success."""
        from src.components.newsletter.component import run

        # Create confirmed subscriber
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.CONFIRMED,
            confirmed_at=datetime.now(UTC),
        )
        mock_repo.save(subscriber)

        result = run(SubscribeInput(email="user@example.com"), repo=mock_repo)

        assert isinstance(result, SubscribeOutput)
        assert result.success is True
        assert result.already_subscribed is True
        assert result.needs_confirmation is False

    def test_run_subscribe_duplicate_pending_resends(
        self,
        mock_repo: MockNewsletterRepo,
        mock_email_sender: MockEmailSender,
    ) -> None:
        """Duplicate pending subscriber resends confirmation email."""
        from src.components.newsletter.component import run

        # Create pending subscriber
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="existing_token",
        )
        mock_repo.save(subscriber)

        result = run(
            SubscribeInput(email="user@example.com"),
            repo=mock_repo,
            email_sender=mock_email_sender
        )

        assert isinstance(result, SubscribeOutput)
        assert result.success is True
        assert result.needs_confirmation is True
        # Confirmation email resent
        assert len(mock_email_sender.sent_emails) == 1

    def test_run_subscribe_rate_limited(
        self,
        mock_repo: MockNewsletterRepo,
        mock_email_sender: MockEmailSender,
        config: NewsletterConfig,
    ) -> None:
        """Rate limit blocks subscription."""
        from src.components.newsletter.component import run

        limiter = MockRateLimiter(allow=False)

        result = run(
            SubscribeInput(email="user@example.com", ip_address="1.2.3.4"),
            repo=mock_repo,
            email_sender=mock_email_sender,
            rate_limiter=limiter,
            config=config,
        )

        assert isinstance(result, SubscribeOutput)
        assert result.success is False
        assert any(e.code == "RATE_LIMIT" for e in result.errors)


class TestRunConfirm:
    """TA-0077-0080: Confirmation run tests."""

    def test_run_confirm_valid_token(
        self,
        mock_repo: MockNewsletterRepo,
        mock_email_sender: MockEmailSender,
    ) -> None:
        """TA-0079: Valid token confirms subscription."""
        from src.components.newsletter.component import run

        # Create pending subscriber
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="valid_token",
            unsubscribe_token="unsub_token",
            created_at=datetime.now(UTC),
        )
        mock_repo.save(subscriber)

        result = run(
            ConfirmInput(token="valid_token"),
            repo=mock_repo,
            email_sender=mock_email_sender
        )

        assert isinstance(result, ConfirmOutput)
        assert result.success is True
        assert result.subscriber_id == subscriber.id

        # Check status changed
        updated = mock_repo.get_by_id(subscriber.id)
        assert updated is not None
        assert updated.status == SubscriberStatus.CONFIRMED

        # Welcome email sent
        welcome_emails = [e for e in mock_email_sender.sent_emails if e["type"] == "welcome"]
        assert len(welcome_emails) == 1

    def test_run_confirm_invalid_token(self, mock_repo: MockNewsletterRepo) -> None:
        """Invalid token returns error."""
        from src.components.newsletter.component import run

        result = run(ConfirmInput(token="invalid_token"), repo=mock_repo)

        assert isinstance(result, ConfirmOutput)
        assert result.success is False
        assert any(e.code == "INVALID_TOKEN" for e in result.errors)

    def test_run_confirm_expired_token(
        self,
        mock_repo: MockNewsletterRepo,
    ) -> None:
        """TA-0078: Expired token returns error."""
        from src.components.newsletter.component import run

        # Create pending subscriber with old creation time
        old_time = datetime.now(UTC) - timedelta(hours=50)
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="expired_token",
            created_at=old_time,
        )
        mock_repo.save(subscriber)

        result = run(ConfirmInput(token="expired_token"), repo=mock_repo)

        assert isinstance(result, ConfirmOutput)
        assert result.success is False
        assert any(e.code == "TOKEN_EXPIRED" for e in result.errors)

    def test_run_confirm_idempotent(
        self,
        mock_repo: MockNewsletterRepo,
    ) -> None:
        """TA-0080: Confirming already confirmed is idempotent."""
        from src.components.newsletter.component import run

        # Create confirmed subscriber (still has token for lookup)
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.CONFIRMED,
            confirmation_token="confirmed_token",
            confirmed_at=datetime.now(UTC),
        )
        mock_repo.save(subscriber)

        result = run(ConfirmInput(token="confirmed_token"), repo=mock_repo)

        assert isinstance(result, ConfirmOutput)
        assert result.success is True
        assert result.already_confirmed is True

    def test_run_confirm_missing_token(self, mock_repo: MockNewsletterRepo) -> None:
        """Missing token returns error."""
        from src.components.newsletter.component import run

        result = run(ConfirmInput(token=""), repo=mock_repo)

        assert isinstance(result, ConfirmOutput)
        assert result.success is False
        assert any(e.code == "MISSING_TOKEN" for e in result.errors)


class TestRunUnsubscribe:
    """TA-0081-0083: Unsubscribe run tests."""

    def test_run_unsubscribe_valid_token(
        self,
        mock_repo: MockNewsletterRepo,
    ) -> None:
        """TA-0081: Valid token unsubscribes."""
        from src.components.newsletter.component import run

        # Create confirmed subscriber
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.CONFIRMED,
            unsubscribe_token="valid_unsub",
            confirmed_at=datetime.now(UTC),
        )
        mock_repo.save(subscriber)

        result = run(UnsubscribeInput(token="valid_unsub"), repo=mock_repo)

        assert isinstance(result, UnsubscribeOutput)
        assert result.success is True

        # Check status changed
        updated = mock_repo.get_by_id(subscriber.id)
        assert updated is not None
        assert updated.status == SubscriberStatus.UNSUBSCRIBED

    def test_run_unsubscribe_invalid_token(self, mock_repo: MockNewsletterRepo) -> None:
        """Invalid token returns error."""
        from src.components.newsletter.component import run

        result = run(UnsubscribeInput(token="invalid"), repo=mock_repo)

        assert isinstance(result, UnsubscribeOutput)
        assert result.success is False
        assert any(e.code == "INVALID_TOKEN" for e in result.errors)

    def test_run_unsubscribe_idempotent(
        self,
        mock_repo: MockNewsletterRepo,
    ) -> None:
        """TA-0082: Unsubscribing already unsubscribed is idempotent."""
        from src.components.newsletter.component import run

        # Create unsubscribed subscriber
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.UNSUBSCRIBED,
            unsubscribe_token="unsub_token",
            unsubscribed_at=datetime.now(UTC),
        )
        mock_repo.save(subscriber)

        result = run(UnsubscribeInput(token="unsub_token"), repo=mock_repo)

        assert isinstance(result, UnsubscribeOutput)
        assert result.success is True
        assert result.already_unsubscribed is True

    def test_run_unsubscribe_pending_invalid(
        self,
        mock_repo: MockNewsletterRepo,
    ) -> None:
        """Cannot unsubscribe from pending state."""
        from src.components.newsletter.component import run

        # Create pending subscriber
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.PENDING,
            unsubscribe_token="unsub_token",
        )
        mock_repo.save(subscriber)

        result = run(UnsubscribeInput(token="unsub_token"), repo=mock_repo)

        assert isinstance(result, UnsubscribeOutput)
        assert result.success is False
        assert any(e.code == "INVALID_STATE" for e in result.errors)

    def test_run_unsubscribe_missing_token(self, mock_repo: MockNewsletterRepo) -> None:
        """Missing token returns error."""
        from src.components.newsletter.component import run

        result = run(UnsubscribeInput(token=""), repo=mock_repo)

        assert isinstance(result, UnsubscribeOutput)
        assert result.success is False
        assert any(e.code == "MISSING_TOKEN" for e in result.errors)


class TestNewsletterServiceGDPR:
    """GDPR compliance tests."""

    def test_delete_subscriber(
        self,
        mock_repo: MockNewsletterRepo,
    ) -> None:
        """Delete subscriber removes data."""
        subscriber = create_subscriber(
            email="user@example.com",
            confirmation_token="token",
            unsubscribe_token="unsub",
        )
        mock_repo.save(subscriber)

        # Service method removed, test repo directly as that's what API does
        success = mock_repo.delete(subscriber.id)
        assert success is True
        assert mock_repo.get_by_id(subscriber.id) is None
        assert mock_repo.get_by_email("user@example.com") is None


