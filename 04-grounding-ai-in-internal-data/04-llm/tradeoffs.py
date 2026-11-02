#!/usr/bin/env python3
"""
SOC RAG Trade-offs Lab
======================
A small RAG assistant over fictional SOC documents (playbooks, threat-intel
IOC feeds, an escalation matrix, an access-restricted incident case).
Every run prints each pipeline stage and how long it took, so learners can
change one setting and see the trade-off.

  Lab 1  Accuracy vs. Latency          --hybrid, --verify
  Lab 2  Retrieval Quality vs. Cost    --embed-model, --rerank
  Lab 3  Chunk Size vs. Context        --chunk-size, --overlap, --split
  Lab 4  Freshness vs. Maintenance     --nightly-batch, --include-old
  Lab 5  More Context vs. Focus        --top-k, --min-score, --loose
  Lab 6  Accessibility vs. Security    --role, --no-acl, --external-llm

Setup:
    pip install sentence-transformers numpy
    # optional, for generated answers: install Ollama, then  ollama pull llama3.2

Example:
    python soc_rag_lab.py "What should I do with a host infected by ransomware?"
    python soc_rag_lab.py --help
"""

import argparse
import json
import math
import re
import textwrap
import time
import urllib.request
import zlib
from collections import Counter
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).parent / "tradeoffs_data"

# ---------------------------------------------------------------------------
# Fictional SOC knowledge base. Front matter: access level and status.
#   access: all | tier2 | ir_lead      status: current | superseded | new
# "new" = arrived after last night's batch index run (used in Lab 4).
# IPs use documentation ranges (198.51.100.0/24, 203.0.113.0/24).
# ---------------------------------------------------------------------------
SAMPLE_DOCS = {
    "playbook_phishing_v3.md": """---
access: all
status: current
---
# Phishing Response Playbook (v3, 2026)
## Triage
Check the sender domain, links and attachments in the sandbox. If a user
clicked a link, reset the user's password and revoke active sessions.
## Containment
Block the sender domain and the URL on the mail gateway and web proxy.
Search all mailboxes for the same subject line and purge matching messages.
## Escalation
Escalate to tier 2 if credentials were entered or an attachment was opened.
""",
    "playbook_phishing_v1_OLD.md": """---
access: all
status: superseded
---
# Phishing Response Playbook (v1, 2021) - SUPERSEDED
## Triage
Forward suspicious emails to the helpdesk mailbox. Ask the user to change
their password within 90 days. No session revocation is required.
""",
    "playbook_ransomware.md": """---
access: all
status: current
---
# Ransomware Response Playbook
## Detection
EDR alerts for mass file renaming, shadow copy deletion (vssadmin delete
shadows) or a ransom note file indicate possible ransomware.
## Containment
Disconnect the infected host from the network immediately, but do not
power it off: memory holds encryption keys and evidence. Isolate the host
in EDR network containment mode and disable the affected user account.
## Eradication
Re-image the host from a known-good image. Rotate credentials used on it.
## Recovery
Restore files from the last clean backup and monitor the host for 14 days.
""",
    "runbook_bruteforce.md": """---
access: all
status: current
---
# Brute-Force Login Runbook
## Detection
Windows event ID 4625 records a failed logon. Ten or more 4625 events for
one account within five minutes indicates a brute-force attempt. Event ID
4624 after a burst of 4625 events may mean the attacker succeeded.
## Response
Block the source IP on the firewall, lock the targeted account, and check
for a successful 4624 logon from the same source.
""",
    "escalation_matrix.md": """---
access: all
status: current
---
# SOC Escalation Matrix
## Severity levels
SEV1: active compromise of production or customer data. Page the SOC lead
and the CISO immediately; response within 15 minutes.
SEV2: confirmed malware on a single endpoint. Tier 2 responds within 4 hours.
SEV3: policy violation or suspicious email. Handled within 2 business days.
""",
    "edr_agent_errors.md": """---
access: all
status: current
---
# EDR Agent Error Codes
## EDR-1042
EDR-1042 means the agent lost contact with the management console for more
than 24 hours. Check the host's network connectivity and restart the agent
service.
## EDR-2210
EDR-2210 means agent tamper protection was disabled. Treat this as a
possible attacker action and open a SEV2 ticket.
""",
    "threat_intel_2026-10-26.md": """---
access: all
status: current
---
# Threat Intel Feed, 2026-10-26
## Indicators of compromise
Phishing campaign "InvoiceDue": sender domain invoices-portal[.]biz, URL
hxxps://invoices-portal[.]biz/view, C2 IP 198.51.100.23.
Ransomware family "LockNine": file hash SHA-256 4f2a...9c1e, ransom note
file README_LOCKNINE.txt.
""",
    "threat_intel_2026-10-27_NEW.md": """---
access: all
status: new
---
# Threat Intel Feed, 2026-10-27
## Indicators of compromise
New C2 infrastructure for "LockNine": domain update-check-cdn[.]net and IP
203.0.113.45. Block both on the firewall and DNS resolver. Hosts contacting
203.0.113.45 should be treated as SEV1.
""",
    "ir_case_IR-2026-0142.md": """---
access: ir_lead
status: current
---
# Incident Case IR-2026-0142 (OPEN, restricted)
## Summary
Suspected insider data theft. User account j.reyes on host FIN-WS-112
uploaded 4 GB of finance files to an external storage site. The user is
not yet aware of the investigation.
## Containment plan
Monitor the account silently until legal approval, then disable it and
collect a memory image from FIN-WS-112.
""",
    "tier2_hunting_notes.md": """---
access: tier2
status: current
---
# Tier 2 Threat Hunting Notes
## Lateral movement
Hunt for pivoting between hosts with remote service creation (event ID
7045) and SMB logons from workstations to other workstations. Check for
C2 beacon callbacks at regular intervals to rare domains.
""",
}

ROLE_ACCESS = {"tier1": {"all"}, "tier2": {"all", "tier2"}, "ir_lead": {"all", "tier2", "ir_lead"}}


# ===========================================================================
# INDEXING PIPELINE
# ===========================================================================

def parse_front_matter(text):
    meta = {}
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
        text = text[m.end():]
    return meta, text


def stage_internal_data(include_old, nightly_batch):
    DATA_DIR.mkdir(exist_ok=True)
    for name, text in SAMPLE_DOCS.items():
        p = DATA_DIR / name
        if not p.exists():
            p.write_text(text, encoding="utf-8")
    docs, skipped = [], []
    for f in sorted(DATA_DIR.glob("*.md")):
        meta, body = parse_front_matter(f.read_text(encoding="utf-8"))
        status = meta.get("status", "current")
        if status == "superseded" and not include_old:
            skipped.append((f.name, "superseded"))
            continue
        if status == "new" and nightly_batch:
            skipped.append((f.name, "arrived after last nightly batch"))
            continue
        docs.append({"source": f.name, "access": meta.get("access", "all"), "status": status, "text": body})
    return docs, skipped


def stage_document_processing(docs):
    sections = []
    for d in docs:
        lines = d["text"].strip().splitlines()
        title = lines[0].lstrip("# ").strip()
        heading, buf = title, []

        def flush():
            body = " ".join(" ".join(buf).split())
            if body:
                sections.append({**d, "title": title, "section": heading, "text": body})

        for line in lines[1:]:
            if line.startswith("## "):
                flush()
                buf, heading = [], line[3:].strip()
            else:
                buf.append(line)
        flush()
    return sections


def stage_chunking(sections, docs, size, overlap, split):
    if overlap >= size:
        raise SystemExit("--overlap must be smaller than --chunk-size")
    units = sections
    if split == "fixed":  # ignore headings: one long text per document
        units = [{**d, "title": d["text"].strip().splitlines()[0].lstrip("# "), "section": "(fixed-size)",
                  "text": " ".join(re.sub(r"^#+ .*$", "", d["text"], flags=re.M).split())} for d in docs]
    chunks, step = [], size - overlap
    for u in units:
        words = u["text"].split()
        for start in range(0, max(len(words), 1), step):
            piece = words[start:start + size]
            if not piece:
                break
            chunks.append({**u, "id": f"C{len(chunks) + 1}", "text": " ".join(piece)})
            if start + size >= len(words):
                break
    return chunks


def tokenize(text):
    return re.findall(r"[a-z0-9]+(?:[-.][a-z0-9]+)*", text.lower())


class Embedder:
    def __init__(self, name):
        self.model = None
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(name)
            self.kind = f"sentence-transformers: {name}"
        except Exception as exc:
            self.kind = f"FALLBACK keyword-hash embedder ({type(exc).__name__}); install sentence-transformers"

    def embed(self, texts):
        if self.model is not None:
            return np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype=np.float32)
        out = np.zeros((len(texts), 512), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in tokenize(t):
                out[i, zlib.crc32(tok.encode()) % 512] += 1.0
        return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)


# ===========================================================================
# QUERY PIPELINE helpers
# ===========================================================================

def bm25(chunks, question, k1=1.5, b=0.75):
    docs = [tokenize(c["section"] + " " + c["text"]) for c in chunks]
    avg = sum(map(len, docs)) / len(docs)
    df = Counter(t for d in docs for t in set(d))
    n, scores = len(docs), []
    for d in docs:
        tf, s = Counter(d), 0.0
        for q in tokenize(question):
            if q in tf:
                idf = math.log(1 + (n - df[q] + 0.5) / (df[q] + 0.5))
                s += idf * tf[q] * (k1 + 1) / (tf[q] + k1 * (1 - b + b * len(d) / avg))
        scores.append(s)
    return np.asarray(scores)


def rrf(rank_lists, k=60):
    fused = Counter()
    for ranks in rank_lists:
        for r, i in enumerate(ranks):
            fused[i] += 1 / (k + r + 1)
    return [i for i, _ in fused.most_common()]


SENSITIVE = [
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "[IP]"),
    (re.compile(r"\b[a-z0-9-]+\[\.\][a-z]{2,}\b", re.I), "[DOMAIN]"),
    (re.compile(r"\b[A-Z]{2,4}-WS-\d+\b"), "[HOST]"),
    (re.compile(r"\b[a-z]\.[a-z]+\b"), "[USER]"),
]


def mask(text):
    for rx, rep in SENSITIVE:
        text = rx.sub(rep, text)
    return text


def build_prompt(question, blocks, loose):
    rules = ("Use the context to help answer; you may also use your own knowledge. Cite chunks like [C3]."
             if loose else
             "Answer ONLY from the context. If it is not there, reply: \"I don't know based on the SOC documents.\" "
             "Cite chunks like [C3] after each fact.")
    ctx = "\n\n".join(blocks) if blocks else "(no relevant context found)"
    return f"You are a SOC assistant.\n{rules}\n\n### Context\n{ctx}\n\n### Question\n{question}\n\n### Answer\n"


def call_llm(prompt, model, url, temperature=0.1):
    data = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": temperature}}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())["response"].strip()
    except Exception:
        return None


# ===========================================================================
# MAIN
# ===========================================================================

def banner(text):
    print(f"\n{'=' * 72}\n{text}\n{'=' * 72}")


def short(t, w=100):
    return textwrap.shorten(t, width=w, placeholder=" ...")


def main():
    p = argparse.ArgumentParser(description="SOC RAG trade-offs lab")
    p.add_argument("question", nargs="?", default="What should I do with a host infected by ransomware?")
    g = p.add_argument_group("Lab 1: accuracy vs. latency")
    g.add_argument("--hybrid", action="store_true", help="vector + BM25 keyword search")
    g.add_argument("--verify", action="store_true", help="second LLM call checks the answer against the context")
    g = p.add_argument_group("Lab 2: retrieval quality vs. cost")
    g.add_argument("--embed-model", default="all-MiniLM-L6-v2", help="e.g. all-mpnet-base-v2 (larger)")
    g.add_argument("--rerank", action="store_true", help="cross-encoder reranker on the top 20")
    g = p.add_argument_group("Lab 3: chunk size vs. context quality")
    g.add_argument("--chunk-size", type=int, default=60, help="words per chunk")
    g.add_argument("--overlap", type=int, default=8, help="overlapping words")
    g.add_argument("--split", choices=["heading", "fixed"], default="heading")
    g = p.add_argument_group("Lab 4: freshness vs. maintenance")
    g.add_argument("--nightly-batch", action="store_true", help="simulate an index built last night (today's feed missing)")
    g.add_argument("--include-old", action="store_true", help="index superseded documents too")
    g = p.add_argument_group("Lab 5: more context vs. answer focus")
    g.add_argument("--top-k", type=int, default=3)
    g.add_argument("--min-score", type=float, default=0.0, help="drop chunks below this similarity")
    g.add_argument("--loose", action="store_true", help="allow model knowledge (loose grounding)")
    g = p.add_argument_group("Lab 6: accessibility vs. security")
    g.add_argument("--role", choices=list(ROLE_ACCESS), default="tier1")
    g.add_argument("--no-acl", action="store_true", help="ignore access tags (one shared index)")
    g.add_argument("--external-llm", action="store_true", help="show what would leave the network; mask it")
    p.add_argument("--llm-model", default="llama3.2")
    p.add_argument("--ollama-url", default="http://localhost:11434/api/generate")
    p.add_argument("--no-llm", action="store_true", help="stop after building the prompt")
    a = p.parse_args()
    timings = {}

    def timed(name, fn, *args):
        t0 = time.perf_counter()
        out = fn(*args)
        timings[name] = (time.perf_counter() - t0) * 1000
        return out

    print("\n##########  INDEXING PIPELINE  ##########")
    banner("1. INTERNAL DATA")
    docs, skipped = timed("Internal Data", stage_internal_data, a.include_old, a.nightly_batch)
    for d in docs:
        print(f"  + {d['source']:<34} access={d['access']:<8} status={d['status']}")
    for name, why in skipped:
        print(f"  - {name:<34} NOT INDEXED ({why})")

    banner("2. DOCUMENT PROCESSING")
    sections = timed("Document Processing", stage_document_processing, docs)
    print(f"  {len(sections)} sections, each tagged with source, section, access and status")

    banner("3. CHUNKING")
    chunks = timed("Chunking", stage_chunking, sections, docs, a.chunk_size, a.overlap, a.split)
    sizes = [len(c["text"].split()) for c in chunks]
    print(f"  split={a.split}, chunk_size={a.chunk_size}, overlap={a.overlap} -> {len(chunks)} chunks, "
          f"avg {sum(sizes) / len(sizes):.0f} words")

    banner("4. EMBEDDING")
    t0 = time.perf_counter()
    emb = Embedder(a.embed_model)
    load_ms = (time.perf_counter() - t0) * 1000
    vecs = timed("Embedding", emb.embed, [f"{c['section']}: {c['text']}" for c in chunks])
    print(f"  model: {emb.kind}  (load {load_ms:.0f} ms)")
    print(f"  {vecs.shape[0]} vectors x {vecs.shape[1]} dims = {vecs.nbytes / 1024:.1f} KB")

    banner("5. VECTOR DB")
    print("  exact (flat) cosine index in memory")

    print("\n##########  QUERY PIPELINE  ##########")
    banner("1. USER QUESTION")
    print(f"  {a.question}\n  role={a.role}  access control={'OFF (shared index)' if a.no_acl else 'ON'}")

    banner("2. QUESTION EMBEDDING")
    q = timed("Question Embedding", emb.embed, [a.question])[0]
    print(f"  same model as indexing, {q.shape[0]} dims")

    banner("3. RETRIEVE RELEVANT CHUNKS")
    t0 = time.perf_counter()
    allowed = ROLE_ACCESS[a.role]
    pool = [i for i, c in enumerate(chunks) if a.no_acl or c["access"] in allowed]
    hidden = len(chunks) - len(pool)
    dense = vecs @ q
    dense_rank = sorted(pool, key=lambda i: -dense[i])
    if a.hybrid:
        kw = bm25(chunks, a.question)
        kw_rank = sorted(pool, key=lambda i: -kw[i])
        ranked = rrf([dense_rank[:20], kw_rank[:20]])
    else:
        ranked = dense_rank
    timings["Retrieve"] = (time.perf_counter() - t0) * 1000
    if a.rerank:
        t0 = time.perf_counter()
        try:
            from sentence_transformers import CrossEncoder
            ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            cand = ranked[:20]
            scores = ce.predict([(a.question, chunks[i]["text"]) for i in cand])
            ranked = [i for _, i in sorted(zip(-np.asarray(scores), cand))]
            print("  reranked top 20 with cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as exc:
            print(f"  reranker unavailable ({type(exc).__name__}); install sentence-transformers")
        timings["Rerank"] = (time.perf_counter() - t0) * 1000
    print(f"  mode: {'hybrid (vector + BM25)' if a.hybrid else 'vector only'}; "
          f"{hidden} chunks hidden by access control")
    kept = []
    for i in ranked[:a.top_k]:
        c, sc = chunks[i], float(dense[i])
        keep = sc >= a.min_score
        if keep:
            kept.append(c)
        flag = "" if keep else "  DROPPED (below --min-score)"
        print(f"  [{c['id']}] sim={sc:.3f} access={c['access']:<7} {c['source']} > {c['section']}{flag}")
        print(f"        {short(c['text'])}")

    banner("4. CONTEXT")
    blocks = [f"[{c['id']}] ({c['source']} > {c['section']})\n{c['text']}" for c in kept]
    words = sum(len(b.split()) for b in blocks)
    print(f"  {len(blocks)} chunks, ~{int(words / 0.75)} tokens")

    banner("5. PROMPT + CONTEXT")
    prompt = build_prompt(a.question, blocks, a.loose)
    if a.external_llm:
        leaked = sorted({m for rx, _ in SENSITIVE for m in rx.findall(prompt)})
        print(f"  EXTERNAL LLM: these values would leave the network: {leaked or 'none'}")
        prompt = mask(prompt)
        print("  -> masked before sending")
    print(f"  grounding: {'LOOSE' if a.loose else 'STRICT'}\n")
    print(textwrap.indent(prompt, "  | "))

    if not a.no_llm:
        banner(f"6. LLM ({a.llm_model} via Ollama)")
        t0 = time.perf_counter()
        answer = call_llm(prompt, a.llm_model, a.ollama_url)
        timings["LLM"] = (time.perf_counter() - t0) * 1000
        banner("7. GROUNDED RESPONSE")
        if answer is None:
            print("  Ollama not running: paste the prompt above into any chat LLM, or run  ollama pull llama3.2")
        else:
            print(textwrap.indent(textwrap.fill(answer, 90), "  "))
            cited = sorted(set(re.findall(r"\[(C\d+)\]", answer)))
            bad = [x for x in cited if x not in {c["id"] for c in kept}]
            print(f"\n  citations: {cited or 'none'}" + (f"  UNKNOWN: {bad}" if bad else ""))
            if a.verify:
                t0 = time.perf_counter()
                check = call_llm("Context:\n" + "\n\n".join(blocks) + f"\n\nAnswer:\n{answer}\n\n"
                                 "Is every statement in the answer supported by the context? "
                                 "Reply SUPPORTED or list the unsupported statements.", a.llm_model, a.ollama_url, 0)
                timings["Verify"] = (time.perf_counter() - t0) * 1000
                print(f"  verification: {check}")

    banner("TIMING (ms)")
    for k, v in timings.items():
        print(f"  {k:<22}{v:>10.1f}")
    print(f"  {'TOTAL':<22}{sum(timings.values()):>10.1f}")


if __name__ == "__main__":
    main()
