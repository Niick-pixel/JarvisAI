-- The phone companion (server/phone): devices you paired, by the hash of their token. The token
-- itself only ever exists on the phone - a copy of this database cannot be used to sign in.
CREATE TABLE paired_devices (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  token_hash  TEXT NOT NULL UNIQUE,
  created_at  INTEGER NOT NULL,
  last_seen   INTEGER
);
