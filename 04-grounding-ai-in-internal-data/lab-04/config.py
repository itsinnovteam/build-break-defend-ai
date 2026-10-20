"""
config.py - every Lab 4 setting in one place.

Change a setting here (or with an environment variable) instead of editing the code.
All paths are relative to this lab4 folder, so the lab works from any location.
"""

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---- Where the data lives ----------------------------------------------------
KB_DIR = HERE / "kb"                                   # the synthetic internal documents
DIRECTORY_FILE = HERE / "config" / "directory.json"    # TRUSTED user -> roles (server side)
INDEX_DIR = HERE / "index"                             # created by ingest.py
DB_FILE = INDEX_DIR / "vectors.db"                     # the SQLite vector store
AUDIT_FILE = HERE / "rag_audit.log"                    # written by the secure assistant (v2)

# ---- Local AI service (Ollama on this VM) ------------------------------------
OLLAMA_URL = os.environ.get("LAB4_OLLAMA_URL", "http://127.0.0.1:11434")
CHAT_MODEL = os.environ.get("LAB4_CHAT_MODEL", "llama3.1:8b")    # answers questions
EMBED_MODEL = os.environ.get("LAB4_EMBED_MODEL", "all-minilm")   # turns text into vectors
EMBED_DIMENSIONS = 384          # all-minilm returns 384 numbers per text

# ---- Pipeline settings (Section 4.3 explains each tradeoff) ------------------
CHUNK_CHARS = 450       # target chunk size in characters (about 100 tokens)
CHUNK_OVERLAP = 0       # characters repeated from the previous chunk (0 = none)
TOP_K = 3               # how many chunks go into the prompt
MIN_SIMILARITY = 0.30   # below this, the chunk is "not relevant enough" (0 to 1)
NUM_CTX = 4096          # context window we ask Ollama to use (input + output tokens)
MAX_ANSWER_TOKENS = 300 # hard cap on the answer length

# ---- Security vocabulary -----------------------------------------------------
KNOWN_ROLES = ("employee", "contractor", "hr", "itops", "devops", "soc", "security-lead")
CLASSIFICATIONS = ("public", "internal", "confidential", "restricted")
RESIDENCY_VALUES = ("any", "local-only")
NO_ANSWER = "I could not find this in the documents you can access."
