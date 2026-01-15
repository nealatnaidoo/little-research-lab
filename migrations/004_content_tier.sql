-- Up
-- Add tier column to content_items for monetization (T-0085, E17.1)
-- Default is 'free' for all existing content
ALTER TABLE content_items ADD COLUMN tier TEXT NOT NULL DEFAULT 'free' CHECK(tier IN ('free', 'premium', 'subscriber_only'));

-- Down
-- SQLite doesn't support DROP COLUMN directly; would need table recreation
-- For rollback, recreate table without tier column
