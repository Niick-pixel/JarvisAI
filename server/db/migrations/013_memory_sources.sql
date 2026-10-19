-- The memory timeline: which chat taught each automatic memory. Mirrors the `from:` line in the
-- Markdown file, which stays the truth - a rescan fills these back in.
ALTER TABLE memory_entries ADD COLUMN source_conversation_id TEXT;
ALTER TABLE memory_entries ADD COLUMN source_message_id TEXT;
CREATE INDEX idx_memory_source ON memory_entries(source_conversation_id);
