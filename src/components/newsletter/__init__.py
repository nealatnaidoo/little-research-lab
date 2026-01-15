"""
Newsletter component (C10).

Double opt-in newsletter subscription management.

Spec refs: E16.1, E16.2, E16.3, SM3, I8, I11, R7
"""

from src.components.newsletter.component import (
    DEFAULT_DISPOSABLE_DOMAINS,
    EMAIL_REGEX,
    build_confirmation_url,
    build_unsubscribe_url,
    confirm_subscriber,
    create_subscriber,
    generate_confirmation_token,
    generate_token,
    generate_unsubscribe_token,
    is_token_expired,
    run,
    unsubscribe_subscriber,
    validate_email,
)
from src.components.newsletter.models import (
    VALID_TRANSITIONS,
    ConfirmInput,
    ConfirmOutput,
    GenerateTokenInput,
    GenerateTokenOutput,
    NewsletterConfig,
    NewsletterError,
    NewsletterSubscriber,
    RateLimitError,
    SubscribeInput,
    SubscribeOutput,
    SubscriberStatus,
    SubscriptionError,
    TokenError,
    TokenExpiredError,
    TokenNotFoundError,
    UnsubscribeInput,
    UnsubscribeOutput,
    ValidateEmailInput,
    ValidateEmailOutput,
    ValidateTokenInput,
    ValidateTokenOutput,
    ValidationError,
    can_transition,
)
from src.components.newsletter.ports import (
    DisposableEmailCheckerPort,
    NewsletterEmailSenderPort,
    NewsletterRepoPort,
    NewsletterRulesPort,
    RateLimiterPort,
)

__all__ = [
    # Component
    "run",
    # Pure functions
    "validate_email",
    "generate_token",
    "generate_confirmation_token",
    "generate_unsubscribe_token",
    "is_token_expired",
    "create_subscriber",
    "confirm_subscriber",
    "unsubscribe_subscriber",
    "build_confirmation_url",
    "build_unsubscribe_url",
    # Constants
    "DEFAULT_DISPOSABLE_DOMAINS",
    "EMAIL_REGEX",
    # Models
    "NewsletterSubscriber",
    "SubscriberStatus",
    "VALID_TRANSITIONS",
    "can_transition",
    "NewsletterConfig",
    # Input/Output
    "ValidateEmailInput",
    "ValidateEmailOutput",
    "SubscribeInput",
    "SubscribeOutput",
    "ConfirmInput",
    "ConfirmOutput",
    "UnsubscribeInput",
    "UnsubscribeOutput",
    "GenerateTokenInput",
    "GenerateTokenOutput",
    "ValidateTokenInput",
    "ValidateTokenOutput",
    "ValidationError",
    # Errors
    "NewsletterError",
    "TokenError",
    "TokenExpiredError",
    "TokenNotFoundError",
    "SubscriptionError",
    "RateLimitError",
    # Ports
    "NewsletterRepoPort",
    "DisposableEmailCheckerPort",
    "RateLimiterPort",
    "NewsletterRulesPort",
    "NewsletterEmailSenderPort",
]
