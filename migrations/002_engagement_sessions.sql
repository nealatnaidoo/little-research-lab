-- Up
-- Engagement Sessions aggregate table (E14)
-- Privacy: No precise timestamps/durations - only bucketed values (TA-0060)

CREATE TABLE IF NOT EXISTS engagement_sessions (
    id TEXT PRIMARY KEY,
    content_id TEXT NOT NULL,
    date DATE NOT NULL,  -- Truncated to day (no time component)
    time_bucket TEXT NOT NULL CHECK(time_bucket IN ('0-10s', '10-30s', '30-60s', '60-120s', '120-300s', '300+s')),
    scroll_bucket TEXT NOT NULL CHECK(scroll_bucket IN ('0-25%', '25-50%', '50-75%', '75-100%')),
    is_engaged INTEGER NOT NULL DEFAULT 0,  -- Boolean: 1 if met threshold
    session_count INTEGER NOT NULL DEFAULT 1,  -- Aggregated count
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE(content_id, date, time_bucket, scroll_bucket)  -- Aggregate key
);

-- Index for content-level queries
CREATE INDEX IF NOT EXISTS idx_engagement_content_date
    ON engagement_sessions(content_id, date);

-- Index for date-range queries
CREATE INDEX IF NOT EXISTS idx_engagement_date
    ON engagement_sessions(date);

-- Index for engaged-only queries
CREATE INDEX IF NOT EXISTS idx_engagement_engaged
    ON engagement_sessions(is_engaged, date);

-- Down
DROP INDEX IF EXISTS idx_engagement_engaged;
DROP INDEX IF EXISTS idx_engagement_date;
DROP INDEX IF EXISTS idx_engagement_content_date;
DROP TABLE IF EXISTS engagement_sessions;
