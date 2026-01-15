-- Up
-- Newsletter subscribers table (E9, E16)
-- Supports double opt-in flow with cryptographic tokens

CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK(status IN ('pending', 'confirmed', 'unsubscribed')),
    confirmation_token TEXT,
    unsubscribe_token TEXT,
    created_at DATETIME NOT NULL,
    confirmed_at DATETIME,
    unsubscribed_at DATETIME
);

-- Index for email lookup (most common query)
CREATE INDEX IF NOT EXISTS idx_newsletter_email ON newsletter_subscribers(email);

-- Index for status filtering (admin queries)
CREATE INDEX IF NOT EXISTS idx_newsletter_status ON newsletter_subscribers(status);

-- Index for confirmation token lookup (confirmation flow)
CREATE INDEX IF NOT EXISTS idx_newsletter_confirmation_token ON newsletter_subscribers(confirmation_token)
    WHERE confirmation_token IS NOT NULL;

-- Index for unsubscribe token lookup (unsubscribe flow)
CREATE INDEX IF NOT EXISTS idx_newsletter_unsubscribe_token ON newsletter_subscribers(unsubscribe_token)
    WHERE unsubscribe_token IS NOT NULL;

-- Down
DROP INDEX IF EXISTS idx_newsletter_unsubscribe_token;
DROP INDEX IF EXISTS idx_newsletter_confirmation_token;
DROP INDEX IF EXISTS idx_newsletter_status;
DROP INDEX IF EXISTS idx_newsletter_email;
DROP TABLE IF EXISTS newsletter_subscribers;
