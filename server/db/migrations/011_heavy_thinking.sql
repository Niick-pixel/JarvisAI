-- Heavy thinking (server/providers/forcing.py): the least reasoning a run was made to do. Stored
-- beside `thinking` for the same reason: replaying a heavy answer without it would think less
-- and not reproduce. 0 means the model stopped thinking whenever it chose.
ALTER TABLE runs ADD COLUMN min_thinking_tokens INTEGER NOT NULL DEFAULT 0;
