"""
v3 SQLite Database Adapter (P1 Implementation).

Implements the v3 DB port interfaces using SQLite.
Designed to be Postgres-compatible (uses standard SQL patterns).

Spec refs: P1, E1-E8
Test assertions: TA-0103 (repo contract tests)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.core.entities import (
    AnalyticsEventAggregate,
    Asset,
    AssetVersion,
    AuditEvent,
    ContentItem,
    PublishJob,
    RedirectRule,
    SiteSettings,
    User,
)
from src.domain.entities import ContentBlock

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def dict_factory(cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert SQLite row to dictionary."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def parse_dt(s: str | None) -> datetime | None:
    """Parse ISO datetime string."""
    return datetime.fromisoformat(s) if s else None


def parse_uuid(s: str | None) -> UUID | None:
    """Parse UUID string."""
    return UUID(s) if s else None


# -----------------------------------------------------------------------------
# Base SQLite Repository
# -----------------------------------------------------------------------------


class SQLiteRepoBase:
    """Base class for SQLite repositories."""

    def __init__(self, db_path: str, connection: sqlite3.Connection | None = None):
        self.db_path = db_path
        self._external_conn = connection

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection (uses external if provided)."""
        if self._external_conn is not None:
            return self._external_conn

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _should_close(self) -> bool:
        """Whether to close connection after use."""
        return self._external_conn is None


# -----------------------------------------------------------------------------
# E4: AssetVersion Repository
# -----------------------------------------------------------------------------


class SQLiteAssetVersionRepo(SQLiteRepoBase):
    """SQLite implementation of AssetVersionRepoPort."""

    def get_by_id(self, version_id: UUID) -> AssetVersion | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM asset_versions WHERE id = ?", (str(version_id),)
            ).fetchone()
            return self._map_row(row) if row else None
        finally:
            if self._should_close():
                conn.close()

    def get_by_storage_key(self, storage_key: str) -> AssetVersion | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM asset_versions WHERE storage_key = ?", (storage_key,)
            ).fetchone()
            return self._map_row(row) if row else None
        finally:
            if self._should_close():
                conn.close()

    def save(self, version: AssetVersion) -> AssetVersion:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO asset_versions (
                    id, asset_id, version_number, storage_key, sha256,
                    size_bytes, mime_type, filename_original, is_latest,
                    created_by_user_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(version.id),
                    str(version.asset_id),
                    version.version_number,
                    version.storage_key,
                    version.sha256,
                    version.size_bytes,
                    version.mime_type,
                    version.filename_original,
                    version.is_latest,
                    str(version.created_by_user_id),
                    version.created_at.isoformat(),
                ),
            )
            if self._should_close():
                conn.commit()
            return version
        finally:
            if self._should_close():
                conn.close()

    def list_by_asset(self, asset_id: UUID) -> list[AssetVersion]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM asset_versions WHERE asset_id = ? ORDER BY version_number",
                (str(asset_id),),
            ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def get_latest(self, asset_id: UUID) -> AssetVersion | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM asset_versions WHERE asset_id = ? AND is_latest = 1",
                (str(asset_id),),
            ).fetchone()
            return self._map_row(row) if row else None
        finally:
            if self._should_close():
                conn.close()

    def set_latest(self, asset_id: UUID, version_id: UUID) -> None:
        conn = self._get_conn()
        try:
            # Clear previous latest
            conn.execute(
                "UPDATE asset_versions SET is_latest = 0 WHERE asset_id = ?",
                (str(asset_id),),
            )
            # Set new latest
            conn.execute(
                "UPDATE asset_versions SET is_latest = 1 WHERE id = ?",
                (str(version_id),),
            )
            if self._should_close():
                conn.commit()
        finally:
            if self._should_close():
                conn.close()

    def _map_row(self, row: dict[str, Any]) -> AssetVersion:
        return AssetVersion(
            id=UUID(row["id"]),
            asset_id=UUID(row["asset_id"]),
            version_number=row["version_number"],
            storage_key=row["storage_key"],
            sha256=row["sha256"],
            size_bytes=row["size_bytes"],
            mime_type=row["mime_type"],
            filename_original=row["filename_original"],
            is_latest=bool(row["is_latest"]),
            created_by_user_id=UUID(row["created_by_user_id"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


# -----------------------------------------------------------------------------
# E5: PublishJob Repository
# -----------------------------------------------------------------------------


class SQLitePublishJobRepo(SQLiteRepoBase):
    """SQLite implementation of PublishJobRepoPort."""

    def get_by_id(self, job_id: UUID) -> PublishJob | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM publish_jobs WHERE id = ?", (str(job_id),)).fetchone()
            return self._map_row(row) if row else None
        finally:
            if self._should_close():
                conn.close()

    def get_by_idempotency_key(
        self, content_id: UUID, publish_at_utc: datetime
    ) -> PublishJob | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM publish_jobs WHERE content_id = ? AND publish_at_utc = ?",
                (str(content_id), publish_at_utc.isoformat()),
            ).fetchone()
            return self._map_row(row) if row else None
        finally:
            if self._should_close():
                conn.close()

    def save(self, job: PublishJob) -> PublishJob:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO publish_jobs (
                    id, content_id, publish_at_utc, status, attempts,
                    last_attempt_at, next_retry_at, completed_at,
                    actual_publish_at, error_message, claimed_by,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    attempts=excluded.attempts,
                    last_attempt_at=excluded.last_attempt_at,
                    next_retry_at=excluded.next_retry_at,
                    completed_at=excluded.completed_at,
                    actual_publish_at=excluded.actual_publish_at,
                    error_message=excluded.error_message,
                    claimed_by=excluded.claimed_by,
                    updated_at=excluded.updated_at
                """,
                (
                    str(job.id),
                    str(job.content_id),
                    job.publish_at_utc.isoformat(),
                    job.status,
                    job.attempts,
                    job.last_attempt_at.isoformat() if job.last_attempt_at else None,
                    job.next_retry_at.isoformat() if job.next_retry_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.actual_publish_at.isoformat() if job.actual_publish_at else None,
                    job.error_message,
                    job.claimed_by,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                ),
            )
            if self._should_close():
                conn.commit()
            return job
        finally:
            if self._should_close():
                conn.close()

    def create_if_not_exists(self, job: PublishJob) -> tuple[PublishJob, bool]:
        conn = self._get_conn()
        try:
            # Check if exists
            existing = self.get_by_idempotency_key(job.content_id, job.publish_at_utc)
            if existing:
                return existing, False

            # Create new
            self.save(job)
            return job, True
        finally:
            if self._should_close():
                conn.close()

    def claim_next_runnable(self, worker_id: str, now_utc: datetime) -> PublishJob | None:
        conn = self._get_conn()
        try:
            # Find and claim in one transaction
            now_iso = now_utc.isoformat()

            # Get next runnable job
            row = conn.execute(
                """
                SELECT * FROM publish_jobs
                WHERE (status = 'queued' AND publish_at_utc <= ?)
                   OR (status = 'retry_wait' AND next_retry_at <= ?)
                ORDER BY publish_at_utc ASC
                LIMIT 1
                """,
                (now_iso, now_iso),
            ).fetchone()

            if not row:
                return None

            # Claim it
            conn.execute(
                """
                UPDATE publish_jobs
                SET status = 'running', claimed_by = ?, last_attempt_at = ?, updated_at = ?
                WHERE id = ? AND status IN ('queued', 'retry_wait')
                """,
                (worker_id, now_iso, now_iso, row["id"]),
            )

            if self._should_close():
                conn.commit()

            # Return updated job
            return self.get_by_id(UUID(row["id"]))
        finally:
            if self._should_close():
                conn.close()

    def list_pending(self) -> list[PublishJob]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM publish_jobs WHERE status IN ('queued', 'running', 'retry_wait')"
            ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def list_by_content(self, content_id: UUID) -> list[PublishJob]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM publish_jobs WHERE content_id = ? ORDER BY created_at DESC",
                (str(content_id),),
            ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def list_in_range(
        self,
        start_utc: datetime,
        end_utc: datetime,
        statuses: list[str] | None = None,
    ) -> list[PublishJob]:
        """List jobs with publish_at in the given date range."""
        conn = self._get_conn()
        try:
            if statuses:
                placeholders = ", ".join("?" for _ in statuses)
                rows = conn.execute(
                    f"""
                    SELECT * FROM publish_jobs
                    WHERE publish_at_utc >= ? AND publish_at_utc <= ?
                    AND status IN ({placeholders})
                    ORDER BY publish_at_utc ASC
                    """,
                    (start_utc.isoformat(), end_utc.isoformat(), *statuses),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM publish_jobs
                    WHERE publish_at_utc >= ? AND publish_at_utc <= ?
                    ORDER BY publish_at_utc ASC
                    """,
                    (start_utc.isoformat(), end_utc.isoformat()),
                ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def _map_row(self, row: dict[str, Any]) -> PublishJob:
        return PublishJob(
            id=UUID(row["id"]),
            content_id=UUID(row["content_id"]),
            publish_at_utc=datetime.fromisoformat(row["publish_at_utc"]),
            status=row["status"],
            attempts=row["attempts"],
            last_attempt_at=parse_dt(row["last_attempt_at"]),
            next_retry_at=parse_dt(row["next_retry_at"]),
            completed_at=parse_dt(row["completed_at"]),
            actual_publish_at=parse_dt(row["actual_publish_at"]),
            error_message=row["error_message"],
            claimed_by=row["claimed_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


# -----------------------------------------------------------------------------
# E6: AnalyticsEventAggregate Repository
# -----------------------------------------------------------------------------


class SQLiteAnalyticsAggregateRepo(SQLiteRepoBase):
    """SQLite implementation of AnalyticsAggregateRepoPort."""

    def get_or_create_bucket(
        self,
        bucket_type: str,
        bucket_start: datetime,
        event_type: str,
        dimensions: dict[str, Any],
    ) -> AnalyticsEventAggregate:
        conn = self._get_conn()
        try:
            # Try to find existing
            row = conn.execute(
                """
                SELECT * FROM analytics_aggregates
                WHERE bucket_type = ? AND bucket_start = ? AND event_type = ?
                  AND content_id IS ? AND utm_source IS ? AND utm_medium IS ?
                  AND utm_campaign IS ? AND referrer_domain IS ? AND ua_class = ?
                """,
                (
                    bucket_type,
                    bucket_start.isoformat(),
                    event_type,
                    str(dimensions.get("content_id")) if dimensions.get("content_id") else None,
                    dimensions.get("utm_source"),
                    dimensions.get("utm_medium"),
                    dimensions.get("utm_campaign"),
                    dimensions.get("referrer_domain"),
                    dimensions.get("ua_class", "unknown"),
                ),
            ).fetchone()

            if row:
                return self._map_row(row)

            # Create new bucket
            from uuid import uuid4

            now = datetime.now(UTC)
            bucket = AnalyticsEventAggregate(
                id=uuid4(),
                bucket_type=bucket_type,  # type: ignore[arg-type]
                bucket_start=bucket_start,
                event_type=event_type,  # type: ignore[arg-type]
                content_id=dimensions.get("content_id"),
                asset_id=dimensions.get("asset_id"),
                link_id=dimensions.get("link_id"),
                utm_source=dimensions.get("utm_source"),
                utm_medium=dimensions.get("utm_medium"),
                utm_campaign=dimensions.get("utm_campaign"),
                referrer_domain=dimensions.get("referrer_domain"),
                ua_class=dimensions.get("ua_class", "unknown"),
                count_total=0,
                count_real=0,
                count_bot=0,
                created_at=now,
                updated_at=now,
            )

            conn.execute(
                """
                INSERT INTO analytics_aggregates (
                    id, bucket_type, bucket_start, event_type,
                    content_id, asset_id, link_id,
                    utm_source, utm_medium, utm_campaign, referrer_domain, ua_class,
                    count_total, count_real, count_bot, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(bucket.id),
                    bucket.bucket_type,
                    bucket.bucket_start.isoformat(),
                    bucket.event_type,
                    str(bucket.content_id) if bucket.content_id else None,
                    str(bucket.asset_id) if bucket.asset_id else None,
                    str(bucket.link_id) if bucket.link_id else None,
                    bucket.utm_source,
                    bucket.utm_medium,
                    bucket.utm_campaign,
                    bucket.referrer_domain,
                    bucket.ua_class,
                    bucket.count_total,
                    bucket.count_real,
                    bucket.count_bot,
                    bucket.created_at.isoformat(),
                    bucket.updated_at.isoformat(),
                ),
            )

            if self._should_close():
                conn.commit()
            return bucket
        finally:
            if self._should_close():
                conn.close()

    def _build_dims_key(self, dimensions: dict[str, Any]) -> str:
        """Build a key from dimensions for comparison."""
        return json.dumps(dimensions, sort_keys=True)

    def increment(
        self,
        bucket_id: UUID,
        count_total: int = 1,
        count_real: int = 0,
        count_bot: int = 0,
    ) -> None:
        conn = self._get_conn()
        try:
            now = datetime.now(UTC).isoformat()
            conn.execute(
                """
                UPDATE analytics_aggregates
                SET count_total = count_total + ?,
                    count_real = count_real + ?,
                    count_bot = count_bot + ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (count_total, count_real, count_bot, now, str(bucket_id)),
            )
            if self._should_close():
                conn.commit()
        finally:
            if self._should_close():
                conn.close()

    def query(
        self,
        bucket_type: str,
        start: datetime,
        end: datetime,
        event_type: str | None = None,
        content_id: UUID | None = None,
        dimensions: dict[str, Any] | None = None,
    ) -> list[AnalyticsEventAggregate]:
        conn = self._get_conn()
        try:
            query = """
                SELECT * FROM analytics_aggregates
                WHERE bucket_type = ? AND bucket_start >= ? AND bucket_start < ?
            """
            params: list[Any] = [bucket_type, start.isoformat(), end.isoformat()]

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            if content_id:
                query += " AND content_id = ?"
                params.append(str(content_id))

            query += " ORDER BY bucket_start ASC"

            rows = conn.execute(query, params).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def _map_row(self, row: dict[str, Any]) -> AnalyticsEventAggregate:
        return AnalyticsEventAggregate(
            id=UUID(row["id"]),
            bucket_type=row["bucket_type"],
            bucket_start=datetime.fromisoformat(row["bucket_start"]),
            event_type=row["event_type"],
            content_id=parse_uuid(row["content_id"]),
            asset_id=parse_uuid(row["asset_id"]),
            link_id=parse_uuid(row["link_id"]),
            utm_source=row["utm_source"],
            utm_medium=row["utm_medium"],
            utm_campaign=row["utm_campaign"],
            referrer_domain=row["referrer_domain"],
            ua_class=row["ua_class"],
            count_total=row["count_total"],
            count_real=row["count_real"],
            count_bot=row["count_bot"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


# -----------------------------------------------------------------------------
# E7: RedirectRule Repository
# -----------------------------------------------------------------------------


class SQLiteRedirectRepo(SQLiteRepoBase):
    """SQLite implementation of RedirectRepoPort."""

    def get_by_id(self, redirect_id: UUID) -> RedirectRule | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM redirect_rules WHERE id = ?", (str(redirect_id),)
            ).fetchone()
            return self._map_row(row) if row else None
        finally:
            if self._should_close():
                conn.close()

    def get_by_source_path(self, source_path: str) -> RedirectRule | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM redirect_rules WHERE source_path = ? AND is_active = 1",
                (source_path,),
            ).fetchone()
            return self._map_row(row) if row else None
        finally:
            if self._should_close():
                conn.close()

    def save(self, rule: RedirectRule) -> RedirectRule:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO redirect_rules (
                    id, source_path, target_path, status_code, is_active,
                    preserve_query_params, created_by_user_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_path=excluded.source_path,
                    target_path=excluded.target_path,
                    status_code=excluded.status_code,
                    is_active=excluded.is_active,
                    preserve_query_params=excluded.preserve_query_params,
                    updated_at=excluded.updated_at
                """,
                (
                    str(rule.id),
                    rule.source_path,
                    rule.target_path,
                    rule.status_code,
                    rule.is_active,
                    rule.preserve_query_params,
                    str(rule.created_by_user_id),
                    rule.created_at.isoformat(),
                    rule.updated_at.isoformat(),
                ),
            )
            if self._should_close():
                conn.commit()
            return rule
        finally:
            if self._should_close():
                conn.close()

    def delete(self, redirect_id: UUID) -> None:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM redirect_rules WHERE id = ?", (str(redirect_id),))
            if self._should_close():
                conn.commit()
        finally:
            if self._should_close():
                conn.close()

    def list_all(self) -> list[RedirectRule]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM redirect_rules ORDER BY created_at DESC").fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def list_active(self) -> list[RedirectRule]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM redirect_rules WHERE is_active = 1 ORDER BY created_at DESC"
            ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def _map_row(self, row: dict[str, Any]) -> RedirectRule:
        return RedirectRule(
            id=UUID(row["id"]),
            source_path=row["source_path"],
            target_path=row["target_path"],
            status_code=row["status_code"],
            is_active=bool(row["is_active"]),
            preserve_query_params=bool(row["preserve_query_params"]),
            created_by_user_id=UUID(row["created_by_user_id"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


# -----------------------------------------------------------------------------
# E8: AuditLogEvent Repository
# -----------------------------------------------------------------------------


class SQLiteAuditLogRepo(SQLiteRepoBase):
    """SQLite implementation of AuditLogRepoPort."""

    def append(self, event: AuditEvent) -> AuditEvent:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO audit_events (
                    id, actor_user_id, action, target_type, target_id,
                    meta_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.id),
                    str(event.actor_user_id) if event.actor_user_id else None,
                    event.action,
                    event.target_type,
                    event.target_id,
                    json.dumps(event.meta_json),
                    event.created_at.isoformat(),
                ),
            )
            if self._should_close():
                conn.commit()
            return event
        finally:
            if self._should_close():
                conn.close()

    def list_recent(self, limit: int = 100) -> list[AuditEvent]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def list_by_target(
        self, target_type: str, target_id: str, limit: int = 100
    ) -> list[AuditEvent]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT * FROM audit_events
                WHERE target_type = ? AND target_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (target_type, target_id, limit),
            ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def list_by_actor(self, actor_user_id: UUID, limit: int = 100) -> list[AuditEvent]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT * FROM audit_events
                WHERE actor_user_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (str(actor_user_id), limit),
            ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def _map_row(self, row: dict[str, Any]) -> AuditEvent:
        return AuditEvent(
            id=UUID(row["id"]),
            actor_user_id=parse_uuid(row["actor_user_id"]),
            action=row["action"],
            target_type=row["target_type"],
            target_id=row["target_id"],
            meta_json=json.loads(row["meta_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


# -----------------------------------------------------------------------------
# Unit of Work
# -----------------------------------------------------------------------------


class SQLiteUnitOfWork:
    """
    SQLite Unit of Work implementation.

    Provides transaction management and access to all repositories.
    Uses a shared connection for all operations within a transaction.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

        # Lazy-initialized repositories
        self._settings: SQLiteSiteSettingsRepoAdapter | None = None
        self._content: SQLiteContentRepoAdapter | None = None
        self._assets: SQLiteAssetRepoAdapter | None = None
        self._asset_versions: SQLiteAssetVersionRepo | None = None
        self._publish_jobs: SQLitePublishJobRepo | None = None
        self._analytics: SQLiteAnalyticsAggregateRepo | None = None
        self._redirects: SQLiteRedirectRepo | None = None
        self._audit_log: SQLiteAuditLogRepo | None = None
        self._users: SQLiteUserRepoAdapter | None = None

    def __enter__(self) -> SQLiteUnitOfWork:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = dict_factory
        self._conn.execute("PRAGMA foreign_keys = ON;")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if exc_type is not None:
            self.rollback()
        if self._conn:
            self._conn.close()
            self._conn = None

    def commit(self) -> None:
        if self._conn:
            self._conn.commit()

    def rollback(self) -> None:
        if self._conn:
            self._conn.rollback()

    @property
    def settings(self) -> SQLiteSiteSettingsRepoAdapter:
        if self._settings is None:
            self._settings = SQLiteSiteSettingsRepoAdapter(self.db_path, self._conn)
        return self._settings

    @property
    def content(self) -> SQLiteContentRepoAdapter:
        if self._content is None:
            self._content = SQLiteContentRepoAdapter(self.db_path, self._conn)
        return self._content

    @property
    def assets(self) -> SQLiteAssetRepoAdapter:
        if self._assets is None:
            self._assets = SQLiteAssetRepoAdapter(self.db_path, self._conn)
        return self._assets

    @property
    def asset_versions(self) -> SQLiteAssetVersionRepo:
        if self._asset_versions is None:
            self._asset_versions = SQLiteAssetVersionRepo(self.db_path, self._conn)
        return self._asset_versions

    @property
    def publish_jobs(self) -> SQLitePublishJobRepo:
        if self._publish_jobs is None:
            self._publish_jobs = SQLitePublishJobRepo(self.db_path, self._conn)
        return self._publish_jobs

    @property
    def analytics(self) -> SQLiteAnalyticsAggregateRepo:
        if self._analytics is None:
            self._analytics = SQLiteAnalyticsAggregateRepo(self.db_path, self._conn)
        return self._analytics

    @property
    def redirects(self) -> SQLiteRedirectRepo:
        if self._redirects is None:
            self._redirects = SQLiteRedirectRepo(self.db_path, self._conn)
        return self._redirects

    @property
    def audit_log(self) -> SQLiteAuditLogRepo:
        if self._audit_log is None:
            self._audit_log = SQLiteAuditLogRepo(self.db_path, self._conn)
        return self._audit_log

    @property
    def users(self) -> SQLiteUserRepoAdapter:
        if self._users is None:
            self._users = SQLiteUserRepoAdapter(self.db_path, self._conn)
        return self._users


# -----------------------------------------------------------------------------
# Adapter wrappers for existing v2 repos (bridging v2 -> v3)
# -----------------------------------------------------------------------------


class SQLiteSiteSettingsRepoAdapter(SQLiteRepoBase):
    """Adapter wrapping existing SQLiteSiteSettingsRepo for v3 interface."""

    def get(self) -> SiteSettings | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM site_settings WHERE id = 1").fetchone()
            if not row:
                return None
            return SiteSettings(
                site_title=row["site_title"],
                site_subtitle=row["site_subtitle"],
                avatar_asset_id=parse_uuid(row["avatar_asset_id"]),
                theme=row["theme"],
                social_links_json=json.loads(row["social_links_json"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
        finally:
            if self._should_close():
                conn.close()

    def save(self, settings: SiteSettings) -> SiteSettings:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO site_settings (
                    id, site_title, site_subtitle, avatar_asset_id,
                    theme, social_links_json, updated_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    site_title=excluded.site_title,
                    site_subtitle=excluded.site_subtitle,
                    avatar_asset_id=excluded.avatar_asset_id,
                    theme=excluded.theme,
                    social_links_json=excluded.social_links_json,
                    updated_at=excluded.updated_at
                """,
                (
                    settings.site_title,
                    settings.site_subtitle,
                    str(settings.avatar_asset_id) if settings.avatar_asset_id else None,
                    settings.theme,
                    json.dumps(settings.social_links_json),
                    settings.updated_at.isoformat(),
                ),
            )
            if self._should_close():
                conn.commit()
            return settings
        finally:
            if self._should_close():
                conn.close()


class SQLiteContentRepoAdapter(SQLiteRepoBase):
    """Adapter wrapping existing SQLiteContentRepo for v3 interface."""

    def get_by_id(self, item_id: UUID) -> ContentItem | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM content_items WHERE id = ?", (str(item_id),)
            ).fetchone()
            if not row:
                return None
            return self._map_row_with_blocks(conn, row)
        finally:
            if self._should_close():
                conn.close()

    def get_by_slug(self, slug: str, item_type: str) -> ContentItem | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM content_items WHERE slug = ? AND type = ?",
                (slug, item_type),
            ).fetchone()
            if not row:
                return None
            return self._map_row_with_blocks(conn, row)
        finally:
            if self._should_close():
                conn.close()

    def save(self, content: ContentItem) -> ContentItem:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO content_items (
                    id, type, slug, title, summary, status,
                    publish_at, published_at, owner_user_id,
                    visibility, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type=excluded.type,
                    slug=excluded.slug,
                    title=excluded.title,
                    summary=excluded.summary,
                    status=excluded.status,
                    publish_at=excluded.publish_at,
                    published_at=excluded.published_at,
                    owner_user_id=excluded.owner_user_id,
                    visibility=excluded.visibility,
                    updated_at=excluded.updated_at
                """,
                (
                    str(content.id),
                    content.type,
                    content.slug,
                    content.title,
                    content.summary,
                    content.status,
                    content.publish_at.isoformat() if content.publish_at else None,
                    content.published_at.isoformat() if content.published_at else None,
                    str(content.owner_user_id),
                    content.visibility,
                    content.created_at.isoformat(),
                    content.updated_at.isoformat(),
                ),
            )

            # Delete and re-insert blocks
            conn.execute(
                "DELETE FROM content_blocks WHERE content_item_id = ?",
                (str(content.id),),
            )
            for i, block in enumerate(content.blocks):
                conn.execute(
                    """
                    INSERT INTO content_blocks
                    (id, content_item_id, block_type, data_json, position)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(block.id),
                        str(content.id),
                        block.block_type,
                        json.dumps(block.data_json),
                        i,
                    ),
                )

            if self._should_close():
                conn.commit()
            return content
        finally:
            if self._should_close():
                conn.close()

    def delete(self, item_id: UUID) -> None:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM content_items WHERE id = ?", (str(item_id),))
            if self._should_close():
                conn.commit()
        finally:
            if self._should_close():
                conn.close()

    def list_items(self, filters: dict[str, Any]) -> list[ContentItem]:
        conn = self._get_conn()
        try:
            query = "SELECT * FROM content_items"
            params: list[Any] = []
            if filters:
                conditions = [f"{k} = ?" for k in filters]
                params = list(filters.values())
                query += " WHERE " + " AND ".join(conditions)

            rows = conn.execute(query, params).fetchall()
            return [self._map_row_with_blocks(conn, r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def list_published(self) -> list[ContentItem]:
        return self.list_items({"status": "published"})

    def list_scheduled_before(self, before_utc: datetime) -> list[ContentItem]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM content_items WHERE status = 'scheduled' AND publish_at <= ?",
                (before_utc.isoformat(),),
            ).fetchall()
            return [self._map_row_with_blocks(conn, r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def _map_row_with_blocks(self, conn: sqlite3.Connection, row: dict[str, Any]) -> ContentItem:
        block_rows = conn.execute(
            "SELECT * FROM content_blocks WHERE content_item_id = ? ORDER BY position ASC",
            (row["id"],),
        ).fetchall()

        blocks = [
            ContentBlock(
                id=str(b["id"]),
                block_type=b["block_type"],
                data_json=json.loads(b["data_json"]),
            )
            for b in block_rows
        ]

        return ContentItem(
            id=UUID(row["id"]),
            type=row["type"],
            slug=row["slug"],
            title=row["title"],
            summary=row["summary"],
            status=row["status"],
            publish_at=parse_dt(row["publish_at"]),
            published_at=parse_dt(row["published_at"]),
            owner_user_id=UUID(row["owner_user_id"]),
            visibility=row["visibility"],
            created_at=parse_dt(row["created_at"]) or datetime.min,
            updated_at=parse_dt(row["updated_at"]) or datetime.min,
            blocks=blocks,
        )


class SQLiteAssetRepoAdapter(SQLiteRepoBase):
    """Adapter wrapping existing SQLiteAssetRepo for v3 interface."""

    def get_by_id(self, asset_id: UUID) -> Asset | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM assets WHERE id = ?", (str(asset_id),)).fetchone()
            if not row:
                return None
            return self._map_row(row)
        finally:
            if self._should_close():
                conn.close()

    def save(self, asset: Asset) -> Asset:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO assets (
                    id, filename_original, mime_type, size_bytes, sha256,
                    storage_path, visibility, created_by_user_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    filename_original=excluded.filename_original,
                    mime_type=excluded.mime_type,
                    size_bytes=excluded.size_bytes,
                    sha256=excluded.sha256,
                    storage_path=excluded.storage_path,
                    visibility=excluded.visibility,
                    created_by_user_id=excluded.created_by_user_id
                """,
                (
                    str(asset.id),
                    asset.filename_original,
                    asset.mime_type,
                    asset.size_bytes,
                    asset.sha256,
                    asset.storage_path,
                    asset.visibility,
                    str(asset.created_by_user_id),
                    asset.created_at.isoformat(),
                ),
            )
            if self._should_close():
                conn.commit()
            return asset
        finally:
            if self._should_close():
                conn.close()

    def delete(self, asset_id: UUID) -> None:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM assets WHERE id = ?", (str(asset_id),))
            if self._should_close():
                conn.commit()
        finally:
            if self._should_close():
                conn.close()

    def list_assets(self) -> list[Asset]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM assets").fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def _map_row(self, row: dict[str, Any]) -> Asset:
        return Asset(
            id=UUID(row["id"]),
            filename_original=row["filename_original"],
            mime_type=row["mime_type"],
            size_bytes=row["size_bytes"],
            sha256=row["sha256"],
            storage_path=row["storage_path"],
            visibility=row["visibility"],
            created_by_user_id=UUID(row["created_by_user_id"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


class SQLiteUserRepoAdapter(SQLiteRepoBase):
    """Adapter wrapping existing SQLiteUserRepo for v3 interface."""

    def get_by_id(self, user_id: UUID) -> User | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (str(user_id),)).fetchone()
            if not row:
                return None
            return self._map_row_with_roles(conn, row)
        finally:
            if self._should_close():
                conn.close()

    def get_by_email(self, email: str) -> User | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if not row:
                return None
            return self._map_row_with_roles(conn, row)
        finally:
            if self._should_close():
                conn.close()

    def save(self, user: User) -> None:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO users (
                    id, email, display_name, password_hash, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    email=excluded.email,
                    display_name=excluded.display_name,
                    password_hash=excluded.password_hash,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (
                    str(user.id),
                    user.email,
                    user.display_name,
                    user.password_hash,
                    user.status,
                    user.created_at.isoformat(),
                    user.updated_at.isoformat(),
                ),
            )

            # Update roles
            conn.execute("DELETE FROM role_assignments WHERE user_id = ?", (str(user.id),))
            for role in user.roles:
                from uuid import uuid4

                conn.execute(
                    """INSERT INTO role_assignments
                    (id, user_id, role, created_at) VALUES (?, ?, ?, ?)""",
                    (str(uuid4()), str(user.id), role, datetime.now(UTC).isoformat()),
                )

            if self._should_close():
                conn.commit()
        finally:
            if self._should_close():
                conn.close()

    def list_all(self) -> list[User]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM users ORDER BY email").fetchall()
            return [self._map_row_with_roles(conn, r) for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def _map_row_with_roles(self, conn: sqlite3.Connection, row: dict[str, Any]) -> User:
        role_rows = conn.execute(
            "SELECT role FROM role_assignments WHERE user_id = ?", (row["id"],)
        ).fetchall()
        roles = [r["role"] for r in role_rows]

        return User(
            id=UUID(row["id"]),
            email=row["email"],
            display_name=row["display_name"],
            password_hash=row["password_hash"],
            roles=roles,
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


# -----------------------------------------------------------------------------
# E14: Engagement Sessions Repository
# -----------------------------------------------------------------------------


class SQLiteEngagementRepo(SQLiteRepoBase):
    """
    SQLite implementation of EngagementRepoPort.

    Spec refs: E14.1, E14.2, E14.3
    Test assertions: TA-0059, TA-0060

    Privacy invariant: Only bucketed values stored, no precise timestamps/durations.
    """

    def store_session(
        self,
        content_id: UUID,
        date: datetime,
        time_bucket: str,
        scroll_bucket: str,
        is_engaged: bool,
    ) -> None:
        """Store or increment an engagement session aggregate."""
        conn = self._get_conn()
        try:
            # Try to increment existing
            date_str = date.strftime("%Y-%m-%d")
            now = datetime.now(UTC).isoformat()

            result = conn.execute(
                """
                UPDATE engagement_sessions
                SET session_count = session_count + 1, updated_at = ?
                WHERE content_id = ? AND date = ? AND time_bucket = ? AND scroll_bucket = ?
                """,
                (now, str(content_id), date_str, time_bucket, scroll_bucket),
            )

            if result.rowcount == 0:
                # Create new aggregate
                from uuid import uuid4

                conn.execute(
                    """
                    INSERT INTO engagement_sessions (
                        id, content_id, date, time_bucket, scroll_bucket,
                        is_engaged, session_count, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        str(content_id),
                        date_str,
                        time_bucket,
                        scroll_bucket,
                        1 if is_engaged else 0,
                        1,
                        now,
                        now,
                    ),
                )

            if self._should_close():
                conn.commit()
        finally:
            if self._should_close():
                conn.close()

    def get_totals(
        self,
        content_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        engaged_only: bool = False,
    ) -> dict[str, int]:
        """Get engagement totals."""
        conn = self._get_conn()
        try:
            query = "SELECT SUM(session_count) as total, SUM(CASE WHEN is_engaged = 1 THEN session_count ELSE 0 END) as engaged FROM engagement_sessions WHERE 1=1"
            params: list[Any] = []

            if content_id:
                query += " AND content_id = ?"
                params.append(str(content_id))

            if start_date:
                query += " AND date >= ?"
                params.append(start_date.strftime("%Y-%m-%d"))

            if end_date:
                query += " AND date <= ?"
                params.append(end_date.strftime("%Y-%m-%d"))

            if engaged_only:
                query += " AND is_engaged = 1"

            row = conn.execute(query, params).fetchone()

            return {
                "total_sessions": row["total"] or 0 if row else 0,
                "engaged_sessions": row["engaged"] or 0 if row else 0,
            }
        finally:
            if self._should_close():
                conn.close()

    def get_distribution(
        self,
        distribution_type: str,
        content_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get engagement distribution by bucket."""
        conn = self._get_conn()
        try:
            bucket_col = "time_bucket" if distribution_type == "time" else "scroll_bucket"
            query = f"SELECT {bucket_col} as bucket, SUM(session_count) as count FROM engagement_sessions WHERE 1=1"
            params: list[Any] = []

            if content_id:
                query += " AND content_id = ?"
                params.append(str(content_id))

            if start_date:
                query += " AND date >= ?"
                params.append(start_date.strftime("%Y-%m-%d"))

            if end_date:
                query += " AND date <= ?"
                params.append(end_date.strftime("%Y-%m-%d"))

            query += f" GROUP BY {bucket_col} ORDER BY {bucket_col}"

            rows = conn.execute(query, params).fetchall()
            return [{"bucket": r["bucket"], "count": r["count"] or 0} for r in rows]
        finally:
            if self._should_close():
                conn.close()

    def get_top_engaged_content(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get top content by engagement."""
        conn = self._get_conn()
        try:
            query = """
                SELECT content_id,
                       SUM(session_count) as total_sessions,
                       SUM(CASE WHEN is_engaged = 1 THEN session_count ELSE 0 END) as engaged_sessions
                FROM engagement_sessions
                WHERE 1=1
            """
            params: list[Any] = []

            if start_date:
                query += " AND date >= ?"
                params.append(start_date.strftime("%Y-%m-%d"))

            if end_date:
                query += " AND date <= ?"
                params.append(end_date.strftime("%Y-%m-%d"))

            query += " GROUP BY content_id ORDER BY engaged_sessions DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [
                {
                    "content_id": UUID(r["content_id"]),
                    "total_sessions": r["total_sessions"] or 0,
                    "engaged_sessions": r["engaged_sessions"] or 0,
                }
                for r in rows
            ]
        finally:
            if self._should_close():
                conn.close()
