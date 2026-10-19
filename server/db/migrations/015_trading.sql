-- The trading co-pilot (server/trading): alert rules and what they said, and your trade journal.
CREATE TABLE alert_rules (
  id         TEXT PRIMARY KEY,
  symbol     TEXT NOT NULL,
  kind       TEXT NOT NULL CHECK (kind IN ('above','below','prob_up','prob_down','range','stale')),
  value      REAL NOT NULL,
  enabled    INTEGER NOT NULL DEFAULT 1,
  armed      INTEGER NOT NULL DEFAULT 1,
  -- Fires once when its condition becomes true, then waits for it to stop being true before it
  -- can fire again: a level that price sits on must not ring every five minutes.
  created_at INTEGER NOT NULL
);

CREATE TABLE alert_events (
  id         TEXT PRIMARY KEY,
  rule_id    TEXT REFERENCES alert_rules(id) ON DELETE SET NULL,
  symbol     TEXT NOT NULL,
  message    TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  read_at    INTEGER
);
CREATE INDEX idx_alert_events_created ON alert_events(created_at);

CREATE TABLE trades (
  id          TEXT PRIMARY KEY,
  account     TEXT NOT NULL DEFAULT '',
  instrument  TEXT NOT NULL,
  side        TEXT NOT NULL CHECK (side IN ('long','short')),
  qty         REAL NOT NULL,
  entry_price REAL NOT NULL,
  exit_price  REAL NOT NULL,
  entry_time  TEXT NOT NULL,   -- as NinjaTrader wrote it, local time: "2026-10-16 09:35:12"
  exit_time   TEXT NOT NULL,
  profit      REAL NOT NULL,   -- net of commission, in dollars
  commission  REAL NOT NULL DEFAULT 0,
  mae         REAL,
  mfe         REAL,
  strategy    TEXT NOT NULL DEFAULT '',
  imported_at INTEGER NOT NULL,
  UNIQUE (account, instrument, entry_time, exit_time, entry_price, exit_price, qty)
);
CREATE INDEX idx_trades_entry ON trades(entry_time);
