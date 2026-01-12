"""
AuditHooks (E8.1) - Audit integration hooks for services.

Provides hooks to integrate audit logging into existing services.

Spec refs: E8.1, TA-0049
Test assertions:
- TA-0049: All admin actions are audited

Key behaviors:
- Hook into settings/content/assets/schedule/redirects services
- Log create/update/delete/publish/schedule actions
- Capture metadata and changes
- Support optional actor context
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar
from uuid import UUID

from src.components.audit import (
    AuditAction,
    AuditService,
    EntityType,
)

# --- Type Variables ---

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


# --- Actor Context ---


@dataclass
class ActorContext:
    """Context for the actor performing an action."""

    actor_id: UUID | None = None
    actor_name: str | None = None
    ip_address: str | None = None


# --- Hooks Configuration ---


@dataclass
class HooksConfig:
    """Configuration for audit hooks."""

    enabled: bool = True
    log_reads: bool = False  # Whether to log read operations


# --- Service Hook Wrapper ---


class AuditHooks:
    """
    Audit hooks for service integration.

    Wraps service methods to automatically log actions.
    """

    def __init__(
        self,
        audit_service: AuditService,
        config: HooksConfig | None = None,
    ) -> None:
        """Initialize hooks."""
        self._audit = audit_service
        self._config = config or HooksConfig()

    def log(
        self,
        action: AuditAction,
        entity_type: EntityType,
        entity_id: str | None = None,
        actor: ActorContext | None = None,
        metadata: dict[str, Any] | None = None,
        description: str = "",
    ) -> None:
        """
        Log an audit action.

        Convenience method for manual logging.
        """
        if not self._config.enabled:
            return

        self._audit.log(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor.actor_id if actor else None,
            actor_name=actor.actor_name if actor else None,
            ip_address=actor.ip_address if actor else None,
            metadata=metadata,
            description=description,
        )

    # --- Settings Hooks ---

    def log_settings_update(
        self,
        setting_key: str,
        old_value: Any,
        new_value: Any,
        actor: ActorContext | None = None,
    ) -> None:
        """Log a settings update."""
        self.log(
            action=AuditAction.UPDATE,
            entity_type=EntityType.SETTINGS,
            entity_id=setting_key,
            actor=actor,
            metadata={
                "changes": {
                    setting_key: {"old": old_value, "new": new_value},
                },
            },
        )

    def log_settings_bulk_update(
        self,
        changes: dict[str, dict[str, Any]],
        actor: ActorContext | None = None,
    ) -> None:
        """Log a bulk settings update."""
        self.log(
            action=AuditAction.UPDATE,
            entity_type=EntityType.SETTINGS,
            entity_id="bulk",
            actor=actor,
            metadata={"changes": changes},
            description=f"Updated {len(changes)} settings",
        )

    # --- Content Hooks ---

    def log_content_create(
        self,
        content_id: UUID | str,
        content_type: str,
        title: str | None = None,
        actor: ActorContext | None = None,
    ) -> None:
        """Log content creation."""
        self.log(
            action=AuditAction.CREATE,
            entity_type=EntityType.CONTENT,
            entity_id=str(content_id),
            actor=actor,
            metadata={"content_type": content_type, "title": title},
        )

    def log_content_update(
        self,
        content_id: UUID | str,
        changes: dict[str, Any] | None = None,
        actor: ActorContext | None = None,
    ) -> None:
        """Log content update."""
        self.log(
            action=AuditAction.UPDATE,
            entity_type=EntityType.CONTENT,
            entity_id=str(content_id),
            actor=actor,
            metadata={"changes": changes} if changes else None,
        )

    def log_content_delete(
        self,
        content_id: UUID | str,
        title: str | None = None,
        actor: ActorContext | None = None,
    ) -> None:
        """Log content deletion."""
        self.log(
            action=AuditAction.DELETE,
            entity_type=EntityType.CONTENT,
            entity_id=str(content_id),
            actor=actor,
            metadata={"title": title} if title else None,
        )

    def log_content_publish(
        self,
        content_id: UUID | str,
        actor: ActorContext | None = None,
    ) -> None:
        """Log content publish."""
        self.log(
            action=AuditAction.PUBLISH,
            entity_type=EntityType.CONTENT,
            entity_id=str(content_id),
            actor=actor,
        )

    def log_content_unpublish(
        self,
        content_id: UUID | str,
        actor: ActorContext | None = None,
    ) -> None:
        """Log content unpublish."""
        self.log(
            action=AuditAction.UNPUBLISH,
            entity_type=EntityType.CONTENT,
            entity_id=str(content_id),
            actor=actor,
        )

    # --- Asset Hooks ---

    def log_asset_upload(
        self,
        asset_id: UUID | str,
        filename: str,
        mime_type: str,
        file_size: int,
        actor: ActorContext | None = None,
    ) -> None:
        """Log asset upload."""
        self.log(
            action=AuditAction.CREATE,
            entity_type=EntityType.ASSET,
            entity_id=str(asset_id),
            actor=actor,
            metadata={
                "filename": filename,
                "mime_type": mime_type,
                "file_size": file_size,
            },
        )

    def log_asset_update(
        self,
        asset_id: UUID | str,
        changes: dict[str, Any] | None = None,
        actor: ActorContext | None = None,
    ) -> None:
        """Log asset metadata update."""
        self.log(
            action=AuditAction.UPDATE,
            entity_type=EntityType.ASSET,
            entity_id=str(asset_id),
            actor=actor,
            metadata={"changes": changes} if changes else None,
        )

    def log_asset_delete(
        self,
        asset_id: UUID | str,
        filename: str | None = None,
        actor: ActorContext | None = None,
    ) -> None:
        """Log asset deletion."""
        self.log(
            action=AuditAction.DELETE,
            entity_type=EntityType.ASSET,
            entity_id=str(asset_id),
            actor=actor,
            metadata={"filename": filename} if filename else None,
        )

    def log_asset_version_create(
        self,
        asset_id: UUID | str,
        version_id: UUID | str,
        actor: ActorContext | None = None,
    ) -> None:
        """Log new asset version creation."""
        self.log(
            action=AuditAction.CREATE,
            entity_type=EntityType.ASSET,
            entity_id=str(asset_id),
            actor=actor,
            metadata={"version_id": str(version_id)},
            description=f"Created version {version_id} for asset {asset_id}",
        )

    def log_asset_latest_update(
        self,
        asset_id: UUID | str,
        version_id: UUID | str,
        actor: ActorContext | None = None,
    ) -> None:
        """Log latest version update."""
        self.log(
            action=AuditAction.UPDATE,
            entity_type=EntityType.ASSET,
            entity_id=str(asset_id),
            actor=actor,
            metadata={"latest_version_id": str(version_id)},
            description=f"Set version {version_id} as latest for asset {asset_id}",
        )

    # --- Schedule Hooks ---

    def log_schedule_create(
        self,
        schedule_id: UUID | str,
        content_id: UUID | str,
        scheduled_for: str,
        actor: ActorContext | None = None,
    ) -> None:
        """Log schedule creation."""
        self.log(
            action=AuditAction.SCHEDULE,
            entity_type=EntityType.SCHEDULE,
            entity_id=str(schedule_id),
            actor=actor,
            metadata={
                "content_id": str(content_id),
                "scheduled_for": scheduled_for,
            },
        )

    def log_schedule_update(
        self,
        schedule_id: UUID | str,
        changes: dict[str, Any] | None = None,
        actor: ActorContext | None = None,
    ) -> None:
        """Log schedule update."""
        self.log(
            action=AuditAction.UPDATE,
            entity_type=EntityType.SCHEDULE,
            entity_id=str(schedule_id),
            actor=actor,
            metadata={"changes": changes} if changes else None,
        )

    def log_schedule_cancel(
        self,
        schedule_id: UUID | str,
        content_id: UUID | str | None = None,
        actor: ActorContext | None = None,
    ) -> None:
        """Log schedule cancellation."""
        self.log(
            action=AuditAction.UNSCHEDULE,
            entity_type=EntityType.SCHEDULE,
            entity_id=str(schedule_id),
            actor=actor,
            metadata={"content_id": str(content_id)} if content_id else None,
        )

    def log_schedule_execute(
        self,
        schedule_id: UUID | str,
        content_id: UUID | str,
        success: bool,
    ) -> None:
        """Log schedule execution (system action)."""
        action = AuditAction.PUBLISH if success else AuditAction.UPDATE
        self.log(
            action=action,
            entity_type=EntityType.SCHEDULE,
            entity_id=str(schedule_id),
            metadata={
                "content_id": str(content_id),
                "success": success,
                "system_action": True,
            },
            description=f"{'Executed' if success else 'Failed'} scheduled publish for {content_id}",
        )

    # --- Redirect Hooks ---

    def log_redirect_create(
        self,
        redirect_id: UUID | str,
        source_path: str,
        target_path: str,
        status_code: int,
        actor: ActorContext | None = None,
    ) -> None:
        """Log redirect creation."""
        self.log(
            action=AuditAction.CREATE,
            entity_type=EntityType.REDIRECT,
            entity_id=str(redirect_id),
            actor=actor,
            metadata={
                "source": source_path,
                "target": target_path,
                "status_code": status_code,
            },
        )

    def log_redirect_update(
        self,
        redirect_id: UUID | str,
        changes: dict[str, Any] | None = None,
        actor: ActorContext | None = None,
    ) -> None:
        """Log redirect update."""
        self.log(
            action=AuditAction.UPDATE,
            entity_type=EntityType.REDIRECT,
            entity_id=str(redirect_id),
            actor=actor,
            metadata={"changes": changes} if changes else None,
        )

    def log_redirect_delete(
        self,
        redirect_id: UUID | str,
        source_path: str | None = None,
        actor: ActorContext | None = None,
    ) -> None:
        """Log redirect deletion."""
        self.log(
            action=AuditAction.DELETE,
            entity_type=EntityType.REDIRECT,
            entity_id=str(redirect_id),
            actor=actor,
            metadata={"source": source_path} if source_path else None,
        )

    def log_redirect_enable(
        self,
        redirect_id: UUID | str,
        actor: ActorContext | None = None,
    ) -> None:
        """Log redirect enable."""
        self.log(
            action=AuditAction.ENABLE,
            entity_type=EntityType.REDIRECT,
            entity_id=str(redirect_id),
            actor=actor,
        )

    def log_redirect_disable(
        self,
        redirect_id: UUID | str,
        actor: ActorContext | None = None,
    ) -> None:
        """Log redirect disable."""
        self.log(
            action=AuditAction.DISABLE,
            entity_type=EntityType.REDIRECT,
            entity_id=str(redirect_id),
            actor=actor,
        )


# --- Factory ---


def create_audit_hooks(
    audit_service: AuditService,
    config: HooksConfig | None = None,
) -> AuditHooks:
    """Create an AuditHooks instance."""
    return AuditHooks(audit_service=audit_service, config=config)
