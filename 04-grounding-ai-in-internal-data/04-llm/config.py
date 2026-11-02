"""Settings for the Module 4 RAG labs. Change values here, not in the scripts."""

OLLAMA_URL = "http://localhost:11434"   # Ollama on the Module 0 VM
CHAT_MODEL = "llama3.2:latest"              # the model from Module 0
EMBED_MODEL = "nomic-embed-text"        # small embedding model, runs on CPU

DOCS_DIR = "docs"                       # where the playbooks live
INDEX_FILE = "index.json"               # where Lab 4.3 saves the vector index

CHUNK_MAX_WORDS = 120                   # a section longer than this is split
CHUNK_OVERLAP_WORDS = 20                # words repeated between split pieces

TOP_K = 3                               # how many chunks to retrieve
MIN_SCORE = 0.45                        # ignore chunks less similar than this

REQUEST_TIMEOUT = 300                   # seconds; CPU-only answers can be slow
