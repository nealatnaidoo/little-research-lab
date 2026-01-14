"""
C2-PublicTemplates Imperative Shell: I/O handlers and adapters.

Handles HTTP response generation, cache header management, and
integration with Next.js App Router handlers.

This module defines the P3 RevalidationAdapter port and provides
implementations for cache invalidation.

Spec refs: E2.1, E2.3, TA-E2.3-01
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol

# ═══════════════════════════════════════════════════════════════════════════
# P3 REVALIDATION ADAPTER (Port)
# Abstract interface for cache revalidation
# ═══════════════════════════════════════════════════════════════════════════


class RevalidationPort(Protocol):
    """
    Port for cache revalidation operations.

    This is P3 from the spec - the RevalidationAdapter interface.
    Implementations wrap platform-specific revalidation mechanisms
    (e.g., Next.js revalidateTag/revalidatePath).
    """

    def revalidate_tag(self, tag: str) -> bool:
        """
        Revalidate cache entries with the given tag.

        Args:
            tag: Cache tag to revalidate

        Returns:
            True if revalidation was triggered
        """
        ...

    def revalidate_path(self, path: str) -> bool:
        """
        Revalidate cache entries for the given path.

        Args:
            path: URL path to revalidate

        Returns:
            True if revalidation was triggered
        """
        ...

    def revalidate_tags(self, tags: list[str]) -> dict[str, bool]:
        """
        Revalidate multiple cache tags.

        Args:
            tags: List of cache tags to revalidate

        Returns:
            Dict mapping tag to success status
        """
        ...


@dataclass
class RevalidationResult:
    """Result of a revalidation operation."""

    success: bool
    tags_revalidated: list[str] = field(default_factory=list)
    paths_revalidated: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class RevalidationAdapter(ABC):
    """
    Abstract base class for revalidation adapters.

    Concrete implementations handle platform-specific revalidation.
    """

    @abstractmethod
    def revalidate_tag(self, tag: str) -> bool:
        """Revalidate by tag."""
        pass

    @abstractmethod
    def revalidate_path(self, path: str) -> bool:
        """Revalidate by path."""
        pass

    def revalidate_tags(self, tags: list[str]) -> dict[str, bool]:
        """Revalidate multiple tags."""
        results = {}
        for tag in tags:
            results[tag] = self.revalidate_tag(tag)
        return results

    def revalidate_content(
        self,
        content_type: str,
        content_id: str,
        slug: str | None = None,
        tag_prefix: str = "content:",
    ) -> RevalidationResult:
        """
        Revalidate all cache entries for a content item.

        Args:
            content_type: Type of content (post, resource)
            content_id: Content identifier
            slug: Optional content slug
            tag_prefix: Tag prefix from rules

        Returns:
            RevalidationResult with status
        """
        from src.components.C2_PublicTemplates.fc import generate_cache_tags

        tags = generate_cache_tags(content_type, content_id, slug, tag_prefix)
        results = self.revalidate_tags(tags)

        success_tags = [tag for tag, success in results.items() if success]
        failed_tags = [tag for tag, success in results.items() if not success]

        return RevalidationResult(
            success=len(failed_tags) == 0,
            tags_revalidated=success_tags,
            errors=[f"Failed to revalidate: {tag}" for tag in failed_tags],
        )


# ═══════════════════════════════════════════════════════════════════════════
# STUB ADAPTER (for testing and development)
# ═══════════════════════════════════════════════════════════════════════════


class StubRevalidationAdapter(RevalidationAdapter):
    """
    Stub adapter for testing.

    Records all revalidation calls without performing actual revalidation.
    """

    def __init__(self) -> None:
        self.revalidated_tags: list[str] = []
        self.revalidated_paths: list[str] = []

    def revalidate_tag(self, tag: str) -> bool:
        """Record tag revalidation."""
        self.revalidated_tags.append(tag)
        return True

    def revalidate_path(self, path: str) -> bool:
        """Record path revalidation."""
        self.revalidated_paths.append(path)
        return True

    def reset(self) -> None:
        """Reset recorded calls."""
        self.revalidated_tags = []
        self.revalidated_paths = []


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    "RevalidationPort",
    "RevalidationAdapter",
    "RevalidationResult",
    "StubRevalidationAdapter",
]
