"""
vectorstore.py - a minimal vector store on SQLite (Python standard library only).

A vector database does three jobs. This file does the same three, in plain code:
  1. STORE   each chunk with its vector and its metadata (doc id, roles, residency ...)
  2. FILTER  keep only the chunks a query is allowed to see  (SQL WHERE, with placeholders)
  3. SEARCH  rank the remaining chunks by cosine similarity to the question vector

Production systems (Chroma, pgvector, Qdrant, Milvus, OpenSearch) add approximate
nearest-neighbour indexes (such as HNSW) to search millions of vectors fast. With a few
dozen chunks, an exact search over every vector takes a few milliseconds.

Security rule built in: search_filtered() puts the role check INSIDE the query, so a chunk
the user may not see is never even scored. A chunk without roles matches no one (fail closed).
"""

import os
import sqlite3
from array import array
from pathlib import Path

import config

SCHEMA = """
CREATE TABLE info   (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE chunks (
    chunk_id       TEXT PRIMARY KEY,
    doc_id         TEXT NOT NULL,
    title          TEXT NOT NULL,
    department     TEXT NOT NULL,
    classification TEXT NOT NULL,
    residency      TEXT NOT NULL,
    owner          TEXT NOT NULL,
    text           TEXT NOT NULL,
    embedding      BLOB NOT NULL
);
CREATE TABLE chunk_roles (
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),
    role     TEXT NOT NULL,
    PRIMARY KEY (chunk_id, role)
);
CREATE INDEX idx_chunk_roles_role ON chunk_roles(role);
"""
SELECT_ALL = ("SELECT chunk_id, doc_id, title, department, classification, residency, owner, "
              "text, embedding FROM chunks ORDER BY chunk_id")
# The secure query. Every value arrives through a placeholder (?) or the q_roles table,
# never through string formatting - the same lesson as Lab 2 (R4, SQL injection).
SELECT_ALLOWED = ("SELECT chunk_id, doc_id, title, department, classification, residency, owner, "
                  "text, embedding FROM chunks "
                  "WHERE chunk_id IN (SELECT chunk_id FROM chunk_roles "
                  "WHERE role IN (SELECT role FROM q_roles)) "
                  "AND (residency = 'any' OR ? = 1) ORDER BY chunk_id")
COLUMNS = ("chunk_id", "doc_id", "title", "department", "classification", "residency", "owner", "text")


def _to_blob(vector):
    return array("f", vector).tobytes()          # 384 floats -> 1,536 bytes


def _from_blob(blob):
    values = array("f")
    values.frombytes(blob)
    return values


def cosine(a, b):
    """Vectors are normalized to length 1, so the dot product IS the cosine similarity."""
    return sum(x * y for x, y in zip(a, b))


class VectorStore:
    def __init__(self, path=None):
        self.path = Path(path or config.DB_FILE)
        self.db = None

    # ---- open / create ------------------------------------------------------
    def open(self):
        if not self.path.is_file():
            raise FileNotFoundError("The vector store does not exist yet. Run: python ingest.py")
        self.db = sqlite3.connect(str(self.path))
        return self

    def create(self):
        """Start a new, empty store (the old file is replaced). Folder 700, file 600."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        if self.path.exists():
            self.path.unlink()
        self.db = sqlite3.connect(str(self.path))
        os.chmod(self.path, 0o600)
        self.db.executescript(SCHEMA)
        return self

    def close(self):
        if self.db is not None:
            self.db.commit()
            self.db.close()
            self.db = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- 1. STORE -----------------------------------------------------------
    def add(self, chunk, vector):
        if len(vector) != config.EMBED_DIMENSIONS:
            raise ValueError(f"vector must have {config.EMBED_DIMENSIONS} numbers")
        self.db.execute(
            "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(chunk[c] for c in COLUMNS) + (_to_blob(vector),),
        )
        for role in chunk["allowed_roles"]:
            self.db.execute("INSERT INTO chunk_roles VALUES (?, ?)", (chunk["chunk_id"], role))

    def set_info(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO info VALUES (?, ?)", (key, str(value)))

    def get_info(self, key, default=None):
        row = self.db.execute("SELECT value FROM info WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def count(self):
        return self.db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def _rows_to_chunks(self, rows):
        chunks = []
        for row in rows:
            chunk = dict(zip(COLUMNS, row[:-1]))
            chunk["vector"] = _from_blob(row[-1])
            roles = self.db.execute(
                "SELECT role FROM chunk_roles WHERE chunk_id = ? ORDER BY role", (chunk["chunk_id"],)
            ).fetchall()
            chunk["allowed_roles"] = [r[0] for r in roles]
            chunks.append(chunk)
        return chunks

    def all_chunks(self):
        rows = self.db.execute(SELECT_ALL)
        return self._rows_to_chunks(rows.fetchall())

    # ---- 2. FILTER + 3. SEARCH -------------------------------------------------
    @staticmethod
    def _rank(chunks, query_vector, k):
        scored = [(round(cosine(query_vector, c["vector"]), 4), c) for c in chunks]
        scored.sort(key=lambda s: (-s[0], s[1]["chunk_id"]))
        return scored if k is None else scored[:k]

    def search_all(self, query_vector, k=None):
        """INSECURE on purpose: ranks EVERY chunk, whoever is asking. Used by v1 and experiments."""
        return self._rank(self.all_chunks(), query_vector, k)

    def search_filtered(self, query_vector, roles, allow_local_only, k=None):
        """
        SECURE: only chunks that list at least one of `roles`, and (for a cloud model) only
        chunks with residency 'any'. The filter runs in SQL, BEFORE any similarity is computed.
        """
        roles = [r for r in (roles or []) if isinstance(r, str) and r]
        if not roles:
            raise PermissionError("no roles: access denied (fail closed)")
        self.db.execute("CREATE TEMP TABLE IF NOT EXISTS q_roles (role TEXT NOT NULL)")
        self.db.execute("DELETE FROM q_roles")
        self.db.executemany("INSERT INTO q_roles VALUES (?)", [(r,) for r in roles])
        rows = self.db.execute(SELECT_ALLOWED, (1 if allow_local_only else 0,)).fetchall()
        return self._rank(self._rows_to_chunks(rows), query_vector, k)
