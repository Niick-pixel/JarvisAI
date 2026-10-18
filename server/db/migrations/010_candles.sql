-- Futures bars for forecasting (server/forecast). Five-minute bars, stamped in UTC by when they
-- end, one row per contract: the continuous series is built from these when it is read, so a
-- newly imported contract re-rolls everything before it instead of being stitched on by hand.
CREATE TABLE candles (
    symbol   TEXT NOT NULL,
    contract TEXT NOT NULL,  -- "03-25", or "" for a file that was already continuous
    t        INTEGER NOT NULL,
    open     REAL NOT NULL,
    high     REAL NOT NULL,
    low      REAL NOT NULL,
    close    REAL NOT NULL,
    volume   REAL NOT NULL,
    PRIMARY KEY (symbol, contract, t)
) WITHOUT ROWID;

-- What each import found, so the sheet can say how a file was read (its time zone above all).
CREATE TABLE candle_imports (
    id             TEXT PRIMARY KEY,
    symbol         TEXT NOT NULL,
    contract       TEXT NOT NULL,
    filename       TEXT NOT NULL,
    bars           INTEGER NOT NULL,
    first_t        INTEGER NOT NULL,
    last_t         INTEGER NOT NULL,
    zone           TEXT NOT NULL,
    zone_assumed   INTEGER NOT NULL,
    source_minutes INTEGER NOT NULL,
    imported_at    INTEGER NOT NULL
);
