-- V90.6g3 private R2/D1 source-history index, no public routes or user data.
-- Apply only to an independently created, explicitly named private D1 database.
CREATE TABLE IF NOT EXISTS writer_lock (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  token TEXT NOT NULL CHECK (length(token) >= 32),
  acquired_at TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS asset_vintages (
  dataset TEXT NOT NULL,
  release TEXT NOT NULL,
  object_sha256 TEXT NOT NULL CHECK (length(object_sha256) = 64),
  object_key TEXT NOT NULL,
  rows INTEGER NOT NULL CHECK (rows > 0),
  source_url TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  rights_state TEXT NOT NULL CHECK (rights_state IN ('approved_public','review_required','restricted')),
  license_url TEXT NOT NULL,
  metadata_json TEXT NOT NULL CHECK (json_valid(metadata_json)),
  admitted_at TEXT NOT NULL,
  PRIMARY KEY (dataset, release, object_sha256),
  UNIQUE (object_key)
) STRICT;

CREATE INDEX IF NOT EXISTS idx_asset_vintages_release
  ON asset_vintages (dataset, release, admitted_at);
