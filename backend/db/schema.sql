PRAGMA foreign_keys = ON;

-- =========================
-- Programs (Stammdaten)
-- =========================
CREATE TABLE IF NOT EXISTS programs (
  id                  TEXT PRIMARY KEY,
  name                TEXT NOT NULL,
  provider            TEXT NOT NULL,
  funding_type        TEXT NOT NULL,
  focus_area          TEXT,
  geography           TEXT,
  variant             TEXT,
  source_url          TEXT,
  status              TEXT NOT NULL DEFAULT 'active',
  notes               TEXT,
  created_at          TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_programs_provider ON programs(provider);
CREATE INDEX IF NOT EXISTS idx_programs_status   ON programs(status);

-- =========================
-- Program Project Forms
-- =========================
CREATE TABLE IF NOT EXISTS program_project_forms (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  program_id    TEXT NOT NULL,
  project_form  TEXT NOT NULL CHECK (
      project_form IN (
        'fue_single',
        'fue_coop',
        'innovation_network',
        'feasibility_study',
        'market_launch'
      )
  ),
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(program_id) REFERENCES programs(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_program_project_forms
  ON program_project_forms(program_id, project_form);

-- =========================
-- Documents
-- =========================
CREATE TABLE IF NOT EXISTS documents (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  program_id          TEXT NOT NULL,
  doc_type            TEXT NOT NULL,
  filename            TEXT NOT NULL,
  filepath            TEXT NOT NULL,
  source_url          TEXT,
  version_date        TEXT,
  sha256              TEXT,
  last_checked_at     TEXT,
  last_ingested_at    TEXT,
  created_at          TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(program_id) REFERENCES programs(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_program_doctype
  ON documents(program_id, doc_type);

CREATE INDEX IF NOT EXISTS idx_documents_program ON documents(program_id);

-- =========================
-- Chunks
-- =========================
CREATE TABLE IF NOT EXISTS chunks (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  program_id           TEXT NOT NULL,
  document_id          INTEGER NOT NULL,
  chunk_index          INTEGER NOT NULL,
  page_ref             TEXT,
  text                 TEXT NOT NULL,
  chroma_id            TEXT,
  token_estimate       INTEGER,
  created_at           TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(program_id) REFERENCES programs(id) ON DELETE CASCADE,
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_chunks_doc_chunkindex
  ON chunks(document_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_chunks_program ON chunks(program_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc     ON chunks(document_id);

-- =========================
-- Program Rules (Eligibility / Rule Engine)
-- =========================
CREATE TABLE IF NOT EXISTS program_rules (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  program_id          TEXT NOT NULL,
  rule_id             TEXT NOT NULL,
  rule_type           TEXT NOT NULL CHECK (rule_type IN ('boolean', 'enum', 'numeric')),
  path               TEXT NOT NULL,                -- JSON path like "company.is_kmu"
  op                 TEXT NOT NULL,                -- e.g. "eq", "in", "lt", "lte", "gt", "gte", "between"
  value_json         TEXT NOT NULL,                -- JSON scalar/array/object
  weight             INTEGER NOT NULL CHECK (weight >= 0),
  hard_fail          INTEGER NOT NULL DEFAULT 0 CHECK (hard_fail IN (0,1)),
  unknown_factor     REAL NOT NULL DEFAULT 0.35 CHECK (unknown_factor >= 0 AND unknown_factor <= 1),
  reason_ok          TEXT,
  reason_fail        TEXT,
  missing_field      TEXT,                         -- if unknown -> this is pushed to missing_fields
  created_at         TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at         TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(program_id) REFERENCES programs(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_program_rules_program_ruleid
  ON program_rules(program_id, rule_id);

CREATE INDEX IF NOT EXISTS idx_program_rules_program
  ON program_rules(program_id);