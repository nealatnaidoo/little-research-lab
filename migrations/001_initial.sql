-- Up
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active', 'disabled')),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS role_assignments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    filename_original TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    visibility TEXT NOT NULL CHECK(visibility IN ('public', 'unlisted', 'private')),
    created_by_user_id TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY(created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS content_items (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT,
    status TEXT NOT NULL CHECK(status IN ('draft', 'scheduled', 'published', 'archived')),
    publish_at DATETIME,
    published_at DATETIME,
    owner_user_id TEXT NOT NULL,
    visibility TEXT NOT NULL CHECK(visibility IN ('public', 'unlisted', 'private')),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS content_blocks (
    id TEXT PRIMARY KEY,
    content_item_id TEXT NOT NULL,
    block_type TEXT NOT NULL,
    data_json TEXT NOT NULL, -- JSON string
    position INTEGER NOT NULL,
    FOREIGN KEY(content_item_id) REFERENCES content_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS link_items (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    icon TEXT,
    status TEXT NOT NULL CHECK(status IN ('active', 'disabled')),
    position INTEGER NOT NULL DEFAULT 0,
    visibility TEXT NOT NULL CHECK(visibility IN ('public', 'unlisted', 'private')),
    group_id TEXT
);

CREATE TABLE IF NOT EXISTS link_groups (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    visibility TEXT NOT NULL CHECK(visibility IN ('public', 'unlisted', 'private'))
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    actor_user_id TEXT,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    meta_json TEXT NOT NULL, -- JSON string
    created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS invites (
    id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    redeemed_at DATETIME,
    redeemed_by_user_id TEXT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY(redeemed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS collaboration_grants (
    id TEXT PRIMARY KEY,
    content_item_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    scope TEXT NOT NULL CHECK(scope IN ('view', 'edit')),
    created_at DATETIME NOT NULL,
    FOREIGN KEY(content_item_id) REFERENCES content_items(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(content_item_id, user_id)
);

CREATE TABLE IF NOT EXISTS site_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Single row constraint
    site_title TEXT NOT NULL,
    site_subtitle TEXT NOT NULL,
    avatar_asset_id TEXT,
    theme TEXT NOT NULL CHECK(theme IN ('light', 'dark', 'system')),
    social_links_json TEXT NOT NULL DEFAULT '{}',
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(avatar_asset_id) REFERENCES assets(id) ON DELETE SET NULL
);

-- Down
DROP TABLE audit_events;
DROP TABLE link_groups;
DROP TABLE link_items;
DROP TABLE content_blocks;
DROP TABLE content_items;
DROP TABLE assets;
DROP TABLE sessions;
DROP TABLE role_assignments;
DROP TABLE users;
