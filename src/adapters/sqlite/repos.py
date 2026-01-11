
import json
import sqlite3
from datetime import datetime
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
            conn.execute("""
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
            """, (
                str(item.id), item.type, item.slug, item.title, item.summary, item.status,
                item.publish_at.isoformat() if item.publish_at else None,
                item.published_at.isoformat() if item.published_at else None,
                str(item.owner_user_id), item.visibility,
                item.created_at.isoformat(), item.updated_at.isoformat()
            ))
            
            # 2. Delete existing blocks
            conn.execute("DELETE FROM content_blocks WHERE content_item_id = ?", (str(item.id),))
            
            # 3. Insert blocks
            for i, block in enumerate(item.blocks):
                conn.execute("""
                    INSERT INTO content_blocks 
                    (id, content_item_id, block_type, data_json, position)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    str(block.id), str(item.id), block.block_type, 
                    json.dumps(block.data_json), i
                ))
            
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
                (str(item_id),)
            ).fetchall()
            
            blocks = []
            for b_row in block_rows:
                blocks.append(ContentBlock(
                    id=str(b_row['id']),
                    block_type=b_row['block_type'],
                    data_json=json.loads(b_row['data_json'])
                ))

            def parse_dt(s: str | None) -> datetime | None:
                return datetime.fromisoformat(s) if s else None
            
            return ContentItem(
                id=UUID(row['id']),
                type=row['type'],
                slug=row['slug'],
                title=row['title'],
                summary=row['summary'],
                status=row['status'],
                publish_at=parse_dt(row['publish_at']),
                published_at=parse_dt(row['published_at']),
                owner_user_id=UUID(row['owner_user_id']),
                visibility=row['visibility'],
                created_at=parse_dt(row['created_at']) or datetime.min, # should not be None
                updated_at=parse_dt(row['updated_at']) or datetime.min,
                blocks=blocks
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
            return self.get_by_id(UUID(row['id']))
        finally:
            conn.close()
    def delete(self, item_id: UUID) -> None:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM content_items WHERE id = ?", (str(item_id),))
            conn.commit()
        finally:
            conn.close()

    def list_items(self, filters: dict[str, Any]) -> list[ContentItem]:
        conn = self._get_conn()
        try:
            # Build query dynamically
            query = "SELECT id FROM content_items"
            params = []
            if filters:
                conditions = []
                for k, v in filters.items():
                    conditions.append(f"{k} = ?")
                    params.append(v)
                query += " WHERE " + " AND ".join(conditions)
            
            rows = conn.execute(query, tuple(params)).fetchall()
            items = []
            for r in rows:
                item = self.get_by_id(UUID(r['id']))
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
            conn.execute("""
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
            """, (
                str(asset.id), asset.filename_original, asset.mime_type, asset.size_bytes,
                asset.sha256, asset.storage_path, asset.visibility, str(asset.created_by_user_id),
                asset.created_at.isoformat()
            ))
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
                id=UUID(row['id']),
                filename_original=row['filename_original'],
                mime_type=row['mime_type'],
                size_bytes=row['size_bytes'],
                sha256=row['sha256'],
                storage_path=row['storage_path'],
                visibility=row['visibility'],
                created_by_user_id=UUID(row['created_by_user_id']),
                created_at=datetime.fromisoformat(row['created_at'])
            )
        finally:
            conn.close()

    def list_assets(self) -> list[Asset]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM assets").fetchall()
            assets = []
            for row in rows:
                assets.append(Asset(
                    id=UUID(row['id']),
                    filename_original=row['filename_original'],
                    mime_type=row['mime_type'],
                    size_bytes=row['size_bytes'],
                    sha256=row['sha256'],
                    storage_path=row['storage_path'],
                    visibility=row['visibility'],
                    created_by_user_id=UUID(row['created_by_user_id']),
                    created_at=datetime.fromisoformat(row['created_at'])
                ))
            return assets
        finally:
            conn.close()

    def get(self, asset_id: UUID) -> Asset | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM assets WHERE id = ?", (str(asset_id),)).fetchone()
            if not row:
                return None
            return Asset(
                id=UUID(row['id']),
                filename_original=row['filename_original'],
                mime_type=row['mime_type'],
                size_bytes=row['size_bytes'],
                sha256=row['sha256'],
                storage_path=row['storage_path'],
                visibility=row['visibility'],
                created_by_user_id=UUID(row['created_by_user_id']),
                created_at=datetime.fromisoformat(row['created_at'])
            )
        finally:
            conn.close()


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
            conn.execute("""
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
            """, (
                str(link.id), link.slug, link.title, str(link.url), link.icon,
                link.status, link.position, link.visibility,
                str(link.group_id) if link.group_id else None
            ))
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
                links.append(LinkItem(
                    id=UUID(row['id']),
                    slug=row['slug'],
                    title=row['title'],
                    url=row['url'],
                    icon=row['icon'],
                    status=row['status'],
                    position=row['position'],
                    visibility=row['visibility'],
                    group_id=UUID(row['group_id']) if row['group_id'] else None
                ))
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
            conn.execute("""
                INSERT INTO users (
                    id, email, display_name, password_hash, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    email=excluded.email,
                    display_name=excluded.display_name,
                    password_hash=excluded.password_hash,
                    status=excluded.status,
                    updated_at=excluded.updated_at
            """, (
                str(user.id), user.email, user.display_name, user.password_hash, user.status,
                user.created_at.isoformat(), user.updated_at.isoformat()
            ))
            
            # Save Roles
            # First delete existing
            conn.execute("DELETE FROM role_assignments WHERE user_id = ?", (str(user.id),))
            # Insert new
            for role in user.roles: 
                from uuid import uuid4
                conn.execute(
                    "INSERT INTO role_assignments (id, user_id, role, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (str(uuid4()), str(user.id), role, datetime.now().isoformat())
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
            "SELECT role FROM role_assignments WHERE user_id = ?", 
            (row['id'],)
        ).fetchall()
        roles = [r['role'] for r in role_rows]
        
        return User(
            id=UUID(row['id']),
            email=row['email'],
            display_name=row['display_name'],
            password_hash=row['password_hash'],
            roles=roles,
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
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
            conn.execute("""
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
            """, (
                str(invite.id), invite.token_hash, invite.role, 
                invite.expires_at.isoformat(),
                invite.redeemed_at.isoformat() if invite.redeemed_at else None,
                str(invite.redeemed_by_user_id) if invite.redeemed_by_user_id else None,
                invite.created_at.isoformat()
            ))
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
            now_iso = datetime.utcnow().isoformat()
            # Active = not redeemed AND not expired
            rows = conn.execute(
                "SELECT * FROM invites WHERE redeemed_at IS NULL "
                "AND expires_at > ? ORDER BY created_at DESC", 
                (now_iso,)
            ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            conn.close()

    def _map_row(self, row: dict[str, Any]) -> Invite:
        def parse_dt(s: str | None) -> datetime | None:
             return datetime.fromisoformat(s) if s else None
             
        return Invite(
            id=UUID(row['id']),
            token_hash=row['token_hash'],
            role=row['role'],
            expires_at=datetime.fromisoformat(row['expires_at']),
            redeemed_at=parse_dt(row['redeemed_at']),
            redeemed_by_user_id=(
                UUID(row['redeemed_by_user_id']) if row['redeemed_by_user_id'] else None
            ),
            created_at=datetime.fromisoformat(row['created_at'])
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
            conn.execute("""
                INSERT INTO collaboration_grants (
                    id, content_item_id, user_id, scope, created_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(content_item_id, user_id) DO UPDATE SET
                    scope=excluded.scope
            """, (
                str(grant.id), str(grant.content_item_id), str(grant.user_id),
                grant.scope, grant.created_at.isoformat()
            ))
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
                (str(content_id), str(user_id))
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
                "SELECT * FROM collaboration_grants WHERE content_item_id = ?",
                (str(content_id),)
            ).fetchall()
            return [self._map_row(r) for r in rows]
        finally:
            conn.close()

    def _map_row(self, row: dict[str, Any]) -> CollaborationGrant:
        return CollaborationGrant(
            id=UUID(row['id']),
            content_item_id=UUID(row['content_item_id']),
            user_id=UUID(row['user_id']),
            scope=row['scope'],
            created_at=datetime.fromisoformat(row['created_at'])
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
            conn.execute("""
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
            """, (
                settings.site_title,
                settings.site_subtitle,
                str(settings.avatar_asset_id) if settings.avatar_asset_id else None,
                settings.theme,
                json.dumps(settings.social_links_json),
                settings.updated_at.isoformat()
            ))
            conn.commit()
            return settings
        finally:
            conn.close()

    def _map_row(self, row: dict[str, Any]) -> SiteSettings:
        return SiteSettings(
            site_title=row['site_title'],
            site_subtitle=row['site_subtitle'],
            avatar_asset_id=UUID(row['avatar_asset_id']) if row['avatar_asset_id'] else None,
            theme=row['theme'],
            social_links_json=json.loads(row['social_links_json']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )
