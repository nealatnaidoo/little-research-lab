import builtins
import json
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.domain.entities import (
    Asset,
    CollaborationGrant,
    ContentBlock,
    ContentItem,
    Invite,
    LinkItem,
    SiteSettings,
    User,
)


# Helper to convert sqlite rows to dicts
def dict_factory(cursor: sqlite3.Cursor, row: Any) -> dict[str, Any]:
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class SQLiteContentRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def save(self, item: ContentItem) -> ContentItem:
        conn = self._get_conn()
        try:
            # 1. Upsert ContentItem
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
                    str(item.id),
                    item.type,
                    item.slug,
                    item.title,
                    item.summary,
                    item.status,
                    item.publish_at.isoformat() if item.publish_at else None,
                    item.published_at.isoformat() if item.published_at else None,
                    str(item.owner_user_id),
                    item.visibility,
                    item.created_at.isoformat(),
                    item.updated_at.isoformat(),
                ),
            )

            # 2. Delete existing blocks
            conn.execute("DELETE FROM content_blocks WHERE content_item_id = ?", (str(item.id),))

            # 3. Insert blocks
            for i, block in enumerate(item.blocks):
                conn.execute(
                    """
                    INSERT INTO content_blocks 
                    (id, content_item_id, block_type, data_json, position)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (str(block.id), str(item.id), block.block_type, json.dumps(block.data_json), i),
                )

            conn.commit()
            return item
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_by_id(self, item_id: UUID) -> ContentItem | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM content_items WHERE id = ?", (str(item_id),)
            ).fetchone()
            if not row:
                return None

            # Fetch blocks
            block_rows = conn.execute(
                "SELECT * FROM content_blocks WHERE content_item_id = ? ORDER BY position ASC",
                (str(item_id),),
            ).fetchall()

            blocks = []
            for b_row in block_rows:
                blocks.append(
                    ContentBlock(
                        id=str(b_row["id"]),
                        block_type=b_row["block_type"],
                        data_json=json.loads(b_row["data_json"]),
                    )
                )

            def parse_dt(s: str | None) -> datetime | None:
                return datetime.fromisoformat(s) if s else None

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
                created_at=parse_dt(row["created_at"]) or datetime.min,  # should not be None
                updated_at=parse_dt(row["updated_at"]) or datetime.min,
                blocks=blocks,
            )
        finally:
            conn.close()

    def get_by_slug(self, slug: str, item_type: str) -> ContentItem | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id FROM content_items WHERE slug = ? AND type = ?", (slug, item_type)
            ).fetchone()
            if not row:
                return None
            return self.get_by_id(UUID(row["id"]))
        finally:
            conn.close()

    def delete(self, item_id: UUID) -> None:
        conn = self._get_conn()
        try:
            # Delete related records first (handles DBs without ON DELETE CASCADE)
            item_id_str = str(item_id)
            conn.execute(
                "DELETE FROM content_blocks WHERE content_item_id = ?", (item_id_str,)
            )
            conn.execute(
                "DELETE FROM collaboration_grants WHERE content_item_id = ?",
                (item_id_str,),
            )
            conn.execute(
                "DELETE FROM publish_jobs WHERE content_id = ?", (item_id_str,)
            )
            conn.execute("DELETE FROM content_items WHERE id = ?", (str(item_id),))
            conn.commit()
        finally:
            conn.close()

    def list(
        self,
        content_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ContentItem], int]:
        filters = {}
        if content_type:
            filters["type"] = content_type
        if status:
            filters["status"] = status

        # Reuse internal list logic or call list_items
        # But list_items takes filters dict and returns list
        # I need to implement pagination and total count here or update list_items logic.
        # Since I'm editing the repos file, I can just implement it.

        conn = self._get_conn()
        try:
            # Base query
            query = "SELECT id FROM content_items WHERE 1=1"
            params: list[str | int] = []

            if content_type:
                query += " AND type = ?"
                params.append(content_type)
            if status:
                query += " AND status = ?"
                params.append(status)

            # Get Total
            count_query = f"SELECT COUNT(*) as cnt FROM ({query})"
            row = conn.execute(count_query, params).fetchone()
            total = row["cnt"] if row else 0

            # Pagination
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.append(limit)
            params.append(offset)

            rows = conn.execute(query, params).fetchall()
            items = []
            for row in rows:
                item = self.get_by_id(UUID(row["id"]))
                if item:
                    items.append(item)

            return items, total
        finally:
            conn.close()

    def list_items(self, filters: dict[str, Any]) -> builtins.list[ContentItem]:
        # Legacy support using new logic if possible, or just wrap
        ct = filters.get("type")
        st = filters.get("status")
        # Legacy didn't paginate explicitly always? Or defaults?
        # Just use list() with defaults
        items, _ = self.list(content_type=ct, status=st, limit=100)
        return items

    def get_related_published(
        self,
        *,
        exclude_id: UUID,
        limit: int = 3,
    ) -> builtins.list[ContentItem]:
        """Get related published content, excluding the given ID."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT id FROM content_items
                WHERE status = 'published' AND id != ?
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (str(exclude_id), limit),
            ).fetchall()
            items = []
            for row in rows:
                item = self.get_by_id(UUID(row["id"]))
                if item:
                    items.append(item)
            return items
        finally:
            conn.close()


class SQLiteAssetRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

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
            conn.commit()
            return asset
        finally:
            conn.close()

    def get_by_id(self, asset_id: UUID) -> Asset | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM assets WHERE id = ?", (str(asset_id),)).fetchone()
            if not row:
                return None
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
        finally:
            conn.close()

    def list(
        self,
        *,
        user_id: UUID | None = None,
        mime_type_prefix: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Asset], int]:
        conn = self._get_conn()
        try:
            query = "SELECT * FROM assets WHERE 1=1"
            params: list[Any] = []

            if user_id:
                query += " AND created_by_user_id = ?"
                params.append(str(user_id))
            if mime_type_prefix:
                query += " AND mime_type LIKE ?"
                params.append(f"{mime_type_prefix}%")

            # Count total
            count_query = f"SELECT COUNT(*) as cnt FROM ({query})"
            row_count = conn.execute(count_query, params).fetchone()
            total = row_count["cnt"] if row_count else 0

            # Pagination
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.append(limit)
            params.append(offset)

            rows = conn.execute(query, params).fetchall()
            assets = []
            for row in rows:
                assets.append(
                    Asset(
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
                )
            return assets, total
        finally:
            conn.close()

    def get(self, asset_id: UUID) -> Asset | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM assets WHERE id = ?", (str(asset_id),)).fetchone()
            if not row:
                return None
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
        finally:
            conn.close()

    def list_assets(self) -> builtins.list[Asset]:
        """List all assets (implements AssetRepoPort protocol)."""
        assets, _ = self.list(limit=10000)  # Get all assets
        return assets


class SQLiteLinkRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def save(self, link: LinkItem) -> LinkItem:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO link_items (
                    id, slug, title, url, icon, status, position, visibility, group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    slug=excluded.slug,
                    title=excluded.title,
                    url=excluded.url,
                    icon=excluded.icon,
                    status=excluded.status,
                    position=excluded.position,
                    visibility=excluded.visibility,
                    group_id=excluded.group_id
            """,
                (
                    str(link.id),
                    link.slug,
                    link.title,
                    str(link.url),
                    link.icon,
                    link.status,
                    link.position,
                    link.visibility,
                    str(link.group_id) if link.group_id else None,
                ),
            )
            conn.commit()
            return link
        finally:
            conn.close()

    def get_all(self) -> list[LinkItem]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM link_items ORDER BY position ASC").fetchall()
            links = []
            for row in rows:
                links.append(
                    LinkItem(
                        id=UUID(row["id"]),
                        slug=row["slug"],
                        title=row["title"],
                        url=row["url"],
                        icon=row["icon"],
                        status=row["status"],
                        position=row["position"],
                        visibility=row["visibility"],
                        group_id=UUID(row["group_id"]) if row["group_id"] else None,
                    )
                )
            return links
        finally:
            conn.close()

    def delete(self, link_id: UUID) -> None:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM link_items WHERE id = ?", (str(link_id),))
            conn.commit()
        finally:
            conn.close()


class SQLiteUserRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def save(self, user: User) -> None:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO users (
                    id, email, display_name, password_hash, status, created_at, updated_at
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

            # Save Roles
            # First delete existing
            conn.execute("DELETE FROM role_assignments WHERE user_id = ?", (str(user.id),))
            # Insert new
            for role in user.roles:
                from uuid import uuid4

                conn.execute(
                    "INSERT INTO role_assignments (id, user_id, role, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (str(uuid4()), str(user.id), role, datetime.now(UTC).isoformat()),
                )

            conn.commit()
        finally:
            conn.close()

    def get_by_email(self, email: str) -> User | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if not row:
                return None
            return self._map_row_to_user(conn, row)
        finally:
            conn.close()

    def get_by_id(self, user_id: UUID) -> User | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (str(user_id),)).fetchone()
            if not row:
                return None
            return self._map_row_to_user(conn, row)
        finally:
            conn.close()

    def list_all(self) -> list[User]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM users ORDER BY email").fetchall()
            return [self._map_row_to_user(conn, row) for row in rows]
        finally:
            conn.close()

    def _map_row_to_user(self, conn: sqlite3.Connection, row: dict[str, Any]) -> User:
        # Fetch roles
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


class SQLiteInviteRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def save(self, invite: Invite) -> None:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO invites (
                    id, token_hash, role, expires_at, 
                    redeemed_at, redeemed_by_user_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    token_hash=excluded.token_hash,
                    role=excluded.role,
                    expires_at=excluded.expires_at,
                    redeemed_at=excluded.redeemed_at,
                    redeemed_by_user_id=excluded.redeemed_by_user_id
            """,
                (
                    str(invite.id),
                    invite.token_hash,
                    invite.role,
                    invite.expires_at.isoformat(),
                    invite.redeemed_at.isoformat() if invite.redeemed_at else None,
                    str(invite.redeemed_by_user_id) if invite.redeemed_by_user_id else None,
                    invite.created_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_by_token_hash(self, token_hash: str) -> Invite | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM invites WHERE token_hash = ?", (token_hash,)
            ).fetchone()
            if not row:
                return None
            return self._map_row(row)
        finally:
            conn.close()

    def get_pending(self) -> list[Invite]:
        conn = self._get_conn()
        try:
            now_iso = datetime.now(UTC).isoformat()
            # Active = not redeemed AND not expired
            rows = conn.execute(
                "SELECT * FROM invites WHERE redeemed_at IS NULL "
                "AND expires_at > ? ORDER BY created_at DESC",
                (now_iso,),
            ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            conn.close()

    def _map_row(self, row: dict[str, Any]) -> Invite:
        def parse_dt(s: str | None) -> datetime | None:
            return datetime.fromisoformat(s) if s else None

        return Invite(
            id=UUID(row["id"]),
            token_hash=row["token_hash"],
            role=row["role"],
            expires_at=datetime.fromisoformat(row["expires_at"]),
            redeemed_at=parse_dt(row["redeemed_at"]),
            redeemed_by_user_id=(
                UUID(row["redeemed_by_user_id"]) if row["redeemed_by_user_id"] else None
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


class SQLiteCollabRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def save(self, grant: CollaborationGrant) -> None:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO collaboration_grants (
                    id, content_item_id, user_id, scope, created_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(content_item_id, user_id) DO UPDATE SET
                    scope=excluded.scope
            """,
                (
                    str(grant.id),
                    str(grant.content_item_id),
                    str(grant.user_id),
                    grant.scope,
                    grant.created_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, grant_id: UUID) -> None:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM collaboration_grants WHERE id = ?", (str(grant_id),))
            conn.commit()
        finally:
            conn.close()

    def get_by_content_and_user(self, content_id: UUID, user_id: UUID) -> CollaborationGrant | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM collaboration_grants WHERE content_item_id = ? AND user_id = ?",
                (str(content_id), str(user_id)),
            ).fetchone()
            if not row:
                return None
            return self._map_row(row)
        finally:
            conn.close()

    def list_by_content(self, content_id: UUID) -> list[CollaborationGrant]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM collaboration_grants WHERE content_item_id = ?", (str(content_id),)
            ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            conn.close()

    def _map_row(self, row: dict[str, Any]) -> CollaborationGrant:
        return CollaborationGrant(
            id=UUID(row["id"]),
            content_item_id=UUID(row["content_item_id"]),
            user_id=UUID(row["user_id"]),
            scope=row["scope"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


class SQLiteSiteSettingsRepo:
    """SQLite adapter for SiteSettings (single-row table)."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def get(self) -> SiteSettings | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM site_settings WHERE id = 1").fetchone()
            if not row:
                return None
            return self._map_row(row)
        finally:
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
            conn.commit()
            return settings
        finally:
            conn.close()

    def _map_row(self, row: dict[str, Any]) -> SiteSettings:
        return SiteSettings(
            site_title=row["site_title"],
            site_subtitle=row["site_subtitle"],
            avatar_asset_id=UUID(row["avatar_asset_id"]) if row["avatar_asset_id"] else None,
            theme=row["theme"],
            social_links_json=json.loads(row["social_links_json"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class SQLitePublishJobRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _map_row(self, row: dict[str, Any]) -> Any:
        # Import here to avoid circular dependency if models imports repo (unlikely but safe)
        from src.core.entities import PublishJob

        def parse_dt(s: str | None) -> datetime | None:
            return datetime.fromisoformat(s) if s else None

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
            updated_at=(
                parse_dt(row["updated_at"])
                if row["updated_at"]
                else datetime.fromisoformat(row["created_at"])
            )
            or datetime.fromisoformat(row["created_at"]),
        )

    def get_by_id(self, job_id: UUID) -> Any | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM publish_jobs WHERE id = ?", (str(job_id),)).fetchone()
            if not row:
                return None
            return self._map_row(row)
        finally:
            conn.close()

    def get_by_idempotency_key(self, content_id: UUID, publish_at_utc: datetime) -> Any | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM publish_jobs WHERE content_id = ? AND publish_at_utc = ?",
                (str(content_id), publish_at_utc.isoformat()),
            ).fetchone()
            if not row:
                return None
            return self._map_row(row)
        finally:
            conn.close()

    def save(self, job: Any) -> Any:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO publish_jobs (
                    id, content_id, publish_at_utc, status, attempts,
                    last_attempt_at, next_retry_at, completed_at, actual_publish_at,
                    error_message, claimed_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    publish_at_utc=excluded.publish_at_utc,
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
                    job.updated_at.isoformat() if job.updated_at else datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
            return job
        finally:
            conn.close()

    def delete(self, job_id: UUID) -> None:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM publish_jobs WHERE id = ?", (str(job_id),))
            conn.commit()
        finally:
            conn.close()

    def list_due_jobs(self, now_utc: datetime, limit: int = 10) -> list[Any]:
        conn = self._get_conn()
        try:
            # Status must be 'pending' or 'retrying' and next_retry_at <= now
            # OR (status is pending and next_retry_at is null which usually implies immediate?
            # Logic: publish_at <= now AND status IN ('scheduled', 'pending')
            # The scheduler component uses 'scheduled' as initial status usually?
            # I must check models.py for status enums.

            # Assuming 'scheduled' is mapped to 'pending' in this DB or vice versa.
            # Let's inspect component to be sure.

            now_iso = now_utc.isoformat()
            rows = conn.execute(
                """
                SELECT * FROM publish_jobs 
                WHERE (status = 'queued' OR status = 'retry_wait')
                AND (next_retry_at IS NULL OR next_retry_at <= ?)
                AND publish_at_utc <= ?
                ORDER BY publish_at_utc ASC
                LIMIT ?
            """,
                (now_iso, now_iso, limit),
            ).fetchall()

            return [self._map_row(r) for r in rows]
        finally:
            conn.close()

    def claim_job(self, job_id: UUID, worker_id: str, now_utc: datetime) -> Any | None:
        conn = self._get_conn()
        try:
            # Atomic update
            cursor = conn.execute(
                """
                UPDATE publish_jobs
                SET status = 'running', claimed_by = ?, updated_at = ?
                WHERE id = ? AND (status = 'queued' OR status = 'retry_wait')
                RETURNING *
            """,
                (worker_id, now_utc.isoformat(), str(job_id)),
            )

            row = cursor.fetchone()
            conn.commit()

            if not row:
                return None
            return self._map_row(row)
        finally:
            conn.close()

    def list_in_range(
        self,
        start_utc: datetime,
        end_utc: datetime,
        statuses: list[str] | None = None,
    ) -> list[Any]:
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
            conn.close()


class SQLiteRedirectRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def save(self, redirect: Any) -> Any:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO redirects (
                    id, source_path, target_path, status_code, 
                    enabled, created_at, updated_at, created_by, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_path=excluded.source_path,
                    target_path=excluded.target_path,
                    status_code=excluded.status_code,
                    enabled=excluded.enabled,
                    updated_at=excluded.updated_at,
                    notes=excluded.notes
            """,
                (
                    str(redirect.id),
                    redirect.source_path,
                    redirect.target_path,
                    redirect.status_code,
                    redirect.enabled,
                    redirect.created_at.isoformat(),
                    redirect.updated_at.isoformat(),
                    str(redirect.created_by) if redirect.created_by else None,
                    redirect.notes,
                ),
            )
            conn.commit()
            return redirect
        finally:
            conn.close()

    def get_by_id(self, redirect_id: UUID) -> Any | None:
        return self._get_one("SELECT * FROM redirects WHERE id = ?", (str(redirect_id),))

    def get_by_source(self, source_path: str) -> Any | None:
        print(f"DEBUG REPO: get_by_source path={source_path}")
        res = self._get_one("SELECT * FROM redirects WHERE source_path = ?", (source_path,))
        print(f"DEBUG REPO: result={res}")
        return res

    def delete(self, redirect_id: UUID) -> None:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM redirects WHERE id = ?", (str(redirect_id),))
            conn.commit()
        finally:
            conn.close()

    def list_all(self) -> list[Any]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM redirects ORDER BY created_at DESC").fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            conn.close()

    def _get_one(self, query: str, params: tuple[Any, ...]) -> Any | None:
        conn = self._get_conn()
        try:
            row = conn.execute(query, params).fetchone()
            if not row:
                return None
            return self._map_row(row)
        finally:
            conn.close()

    def _map_row(self, row: dict[str, Any]) -> Any:
        # Import dynamically to avoid circular issues if any, but Redirect is from entities
        from src.domain.entities import Redirect
        return Redirect(
            id=UUID(row["id"]),
            source_path=row["source_path"],
            target_path=row["target_path"],
            status_code=row["status_code"],
            enabled=bool(row["enabled"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            created_by=UUID(row["created_by"]) if row["created_by"] else None,
            notes=row["notes"],
        )
