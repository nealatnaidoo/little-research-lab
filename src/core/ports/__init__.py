# little-research-lab-v3 — Ports (Protocol Interfaces)
# Abstract interfaces for adapters; no implementations here

from src.core.ports.email import (
    EmailAddress,
    EmailConfigPort,
    EmailError,
    EmailMessage,
    EmailPort,
    EmailRateLimitError,
    EmailResult,
    EmailSendError,
    EmailStatus,
    EmailValidationError,
)

__all__ = [
    # Email (P7)
    "EmailAddress",
    "EmailConfigPort",
    "EmailError",
    "EmailMessage",
    "EmailPort",
    "EmailRateLimitError",
    "EmailResult",
    "EmailSendError",
    "EmailStatus",
    "EmailValidationError",
]
