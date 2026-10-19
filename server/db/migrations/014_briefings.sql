-- The morning briefing (server/briefing): each one written, kept, and linked to the chat that
-- holds it so you can ask follow-ups.
CREATE TABLE briefings (
  id              TEXT PRIMARY KEY,
  created_at      INTEGER NOT NULL,
  title           TEXT NOT NULL,
  body            TEXT NOT NULL,
  sections_json   TEXT NOT NULL DEFAULT '[]',
  conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
  read_at         INTEGER
);
CREATE INDEX idx_briefings_created ON briefings(created_at);
