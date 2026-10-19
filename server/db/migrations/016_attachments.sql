-- Images in a conversation (server/attachments.py): photos you add and screenshots you take. The
-- bytes live as files under data/attachments; this says which message each one belongs to.
CREATE TABLE attachments (
  id              TEXT PRIMARY KEY,
  conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
  message_id      TEXT REFERENCES messages(id) ON DELETE CASCADE,
  mime            TEXT NOT NULL,
  bytes           INTEGER NOT NULL,
  source          TEXT NOT NULL DEFAULT 'upload' CHECK (source IN ('upload','screen')),
  created_at      INTEGER NOT NULL
);
CREATE INDEX idx_attachments_message ON attachments(message_id);
