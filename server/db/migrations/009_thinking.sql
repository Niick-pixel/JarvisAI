-- Whether a run asked the model to think first. NULL means the model's own default.
-- A column rather than a JSON field because replay reads its params from these columns: without
-- it, rerunning a "fast" answer would silently turn thinking back on and not reproduce.
ALTER TABLE runs ADD COLUMN thinking INTEGER;
