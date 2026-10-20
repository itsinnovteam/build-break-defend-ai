"""
assistant.py - the QUERY-TIME pipeline, in two versions side by side.

  prepare_v1()  VULNERABLE: trusts a role the user types (--role), searches ALL documents,
                and only ASKS the model (in the prompt) to respect the access rules.
  prepare_v2()  SECURE: roles come only from the trusted directory; the vector store filters
                by role and residency BEFORE ranking; poisoned documents are held back;
                every problem fails closed; an audit line is written.

Steps (both versions): embed the question -> retrieve top-k -> build the context with
numbered sources -> the model answers with [S1] citations -> print the sources.

Run:  python ask_v1.py ...   (vulnerable)     python ask.py ...   (secure)
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

import config
import identity
import ollama_client
import pipeline
import retrieval
import safety
from vectorstore import VectorStore

SYSTEM_V1 = (config.HERE / "prompts" / "system_v1.txt").read_text(encoding="utf-8")
SYSTEM_V2 = (config.HERE / "prompts" / "system_v2.txt").read_text(encoding="utf-8")


def _result(version, user, roles, question, mode, location, top_k):
    return {"version": version, "user": user, "roles": roles, "question": question,
            "mode": mode, "location": location, "top_k": top_k, "used": [],
            "quarantined": [], "blocked_count": 0, "residency_held": 0, "messages": None}


def _source_tag(number, chunk, show_access=False):
    """One numbered source for the prompt. Text is defused so it cannot close the tag."""
    title = re.sub(r'[<>"]', "", chunk["title"])
    access = (f' classification="{chunk["classification"]}"'
              f' allowed_roles="{", ".join(chunk["allowed_roles"])}"') if show_access else ""
    return (f'<source id="S{number}" doc="{chunk["doc_id"]}" title="{title}"{access}>\n'
            f'{safety.defuse_tags(chunk["text"])}\n</source>')


def _user_message(question, sources):
    return ("Sources:\n" + "\n\n".join(sources) + f"\n\nQuestion: {question}\n"
            "Answer from the sources only, with [S1]-style citations.")


# ---------- v1: VULNERABLE ------------------------------------------------------
def prepare_v1(store, question, question_vector, user, claimed_role=None,
               top_k=None, mode="vector", location="local", directory=None):
    """VULNERABLE on purpose (Phase 4). Three flaws are marked FLAW."""
    top_k = top_k or config.TOP_K
    users = identity.load_directory() if directory is None else directory
    entry = users.get(user) or {}
    roles = entry.get("roles") or ["employee"]           # FLAW 1: unknown user -> 'employee' (fails open)
    if claimed_role:
        roles = [claimed_role]                           # FLAW 2: trusts a role the user typed
    r = _result("v1", user, roles, question, mode, location, top_k)
    r["used"] = retrieval.retrieve(store, question, question_vector, roles=None,  # FLAW 3: no filter
                                   mode=mode, k=top_k)
    if r["used"]:
        sources = [_source_tag(n, h["chunk"], show_access=True) for n, h in enumerate(r["used"], 1)]
        system = SYSTEM_V1.replace("{roles}", ", ".join(roles))   # the rules live ONLY in the prompt
        r["messages"] = [{"role": "system", "content": system},
                         {"role": "user", "content": _user_message(question, sources)}]
    return r


# ---------- v2: SECURE ----------------------------------------------------------
def poisoned_documents(store):
    """{doc_id: phrases} for every document where ANY chunk tries to instruct the AI.
    The whole document is held back, so an instruction split over two chunks cannot slip in."""
    found = {}
    for chunk in store.all_chunks():
        phrases = safety.find_injection(chunk["title"] + "\n" + chunk["text"])
        if phrases:
            known = found.setdefault(chunk["doc_id"], [])
            known.extend(p for p in phrases if p not in known)
    return found


def prepare_v2(store, question, question_vector, user, top_k=None, mode="vector",
               location="local", directory=None):
    """SECURE. Raises identity.AccessDenied when there is no valid authorization context."""
    top_k = top_k or config.TOP_K
    roles = identity.resolve_roles(user, directory)        # trusted, server side; fails closed
    r = _result("v2", user, roles, question, mode, location, top_k)
    allow_local_only = (location == "local")               # data residency
    poisoned = poisoned_documents(store)

    # THE FIX: the vector store filters by role (and residency) BEFORE anything is ranked.
    candidates = retrieval.retrieve(store, question, question_vector, roles=roles,
                                    allow_local_only=allow_local_only, mode=mode, k=10_000)
    for hit in candidates:
        if hit["chunk"]["doc_id"] in poisoned:              # prompt-injection defense
            r["quarantined"].append((hit, poisoned[hit["chunk"]["doc_id"]]))
        elif len(r["used"]) < top_k:
            r["used"].append(hit)

    # For the audit log only (never shown to the user): what did the filters remove?
    everything = retrieval.retrieve(store, question, question_vector, roles=None, mode=mode, k=10_000)
    visible = [h for h in everything if set(h["chunk"]["allowed_roles"]) & set(roles)]
    r["blocked_count"] = len(everything) - len(visible)
    r["residency_held"] = sum(1 for h in visible if not allow_local_only
                              and h["chunk"]["residency"] == "local-only")

    if r["used"]:
        sources = [_source_tag(n, h["chunk"]) for n, h in enumerate(r["used"], 1)]
        r["messages"] = [{"role": "system", "content": SYSTEM_V2},
                         {"role": "user", "content": _user_message(question, sources)}]
    return r


def write_audit(r, outcome, path=None):
    """Who asked, which chunks were sent, what was filtered. No question text, no answer text."""
    path = path or config.AUDIT_FILE
    line = {
        "time_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user": str(r["user"])[:64], "roles": r["roles"],
        "question_sha256": hashlib.sha256(r["question"].encode("utf-8")).hexdigest()[:16],
        "mode": r["mode"], "model_location": r["location"],
        "chunks_sent": [h["chunk"]["chunk_id"] for h in r["used"]],
        "blocked_by_access_control": r["blocked_count"],
        "held_back_by_residency": r["residency_held"],
        "quarantined": sorted({h["chunk"]["doc_id"] for h, _ in r["quarantined"]}),
        "outcome": outcome,
    }
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
    if new:
        os.chmod(path, 0o600)


# ---------- output helpers ------------------------------------------------------
def citations_check(answer, n_sources):
    """Which [S#] ids does the answer cite, and are they real?"""
    cited = sorted({int(m) for m in re.findall(r"\[S(\d+)\]", answer)})
    unknown = [c for c in cited if c < 1 or c > n_sources]
    return cited, unknown


def print_retrieved(r):
    if not r["used"]:
        print("Retrieved : nothing relevant in the documents this user can access")
        return
    print(f"Retrieved (sent to the model, best first):")
    for n, h in enumerate(r["used"], 1):
        c = h["chunk"]
        score = f"similarity {h['similarity']:.2f}"
        if r["mode"] == "hybrid":
            score += f", keyword {h['keyword']:.1f}"
        print(f"  [S{n}] {c['chunk_id']:<11} {c['title']}  ({score})")
        if r["version"] == "v1":
            print(f"        classification: {c['classification']} | allowed roles: "
                  f"{', '.join(c['allowed_roles'])} | residency: {c['residency']}")


def print_sources(r):
    print("Sources:")
    for n, h in enumerate(r["used"], 1):
        c = h["chunk"]
        print(f"  [S{n}] {c['doc_id']} | {c['title']} | {c['classification']} | chunk {c['chunk_id']}")


# ---------- command line --------------------------------------------------------
TITLES = {"v1": "ASSISTANT v1 - VULNERABLE (access rules only in the prompt)",
          "v2": "ASSISTANT v2 - SECURE (access control at retrieval)"}


def run_cli(version, argv=None):
    parser = argparse.ArgumentParser(description=TITLES[version])
    parser.add_argument("--user", required=True, help="who is asking (stands in for the SSO login)")
    parser.add_argument("question", help="the question, in quotes")
    if version == "v1":
        parser.add_argument("--role", help="v1 only: a role the user CLAIMS to have (v1 trusts it!)")
    parser.add_argument("--top-k", type=int, default=config.TOP_K, choices=range(1, 9), metavar="1-8",
                        help=f"how many chunks to send (default {config.TOP_K})")
    parser.add_argument("--mode", choices=retrieval.MODES, default="vector", help="vector (default) or hybrid")
    parser.add_argument("--model-location", choices=["local", "cloud"], default="local",
                        help="local = Ollama on this VM; cloud = a SIMULATED external service (nothing is sent)")
    parser.add_argument("--dry-run", action="store_true", help="show the exact prompt; do not call the model")
    raw = sys.argv[1:] if argv is None else list(argv)
    if version == "v2" and any(a == "--role" or a.startswith("--role=") for a in raw):
        print("ERROR: v2 has no --role option. Roles come only from config/directory.json "
              "(the trusted directory), never from the user.", file=sys.stderr)
        return 2
    args = parser.parse_args(raw)
    question = args.question.strip()
    if not question or len(question) > 500:
        print("ERROR: the question must be 1 to 500 characters.", file=sys.stderr)
        return 1

    try:
        store = VectorStore().open()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    try:
        if store.get_info("embed_model") != config.EMBED_MODEL:
            print("ERROR: the index was built with another embedding model. Run: python ingest.py", file=sys.stderr)
            return 1
        if store.get_info("kb_fingerprint") != pipeline.kb_fingerprint():
            msg = "documents in kb/ changed after the index was built (old text or old permissions)."
            if version == "v2":                          # fail closed: refuse a stale index
                print(f"ERROR: {msg} Run: python ingest.py", file=sys.stderr)
                return 1
            print(f"WARNING: {msg}", file=sys.stderr)    # v1 carries on anyway
        try:
            question_vector = ollama_client.embed([question])[0]        # embed the question
        except ollama_client.OllamaError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        try:
            if version == "v1":
                r = prepare_v1(store, question, question_vector, args.user, args.role,
                               args.top_k, args.mode, args.model_location)
            else:
                r = prepare_v2(store, question, question_vector, args.user,
                               args.top_k, args.mode, args.model_location)
        except identity.AccessDenied as exc:
            denied = _result(version, args.user, [], question, args.mode, args.model_location, args.top_k)
            if version == "v2":
                write_audit(denied, "access_denied")      # failed attempts matter to the SOC
            print(TITLES[version])
            print(f"ACCESS DENIED: {exc}. Nothing was retrieved.")
            return 2
        return _finish(version, r, args)
    finally:
        store.close()


def _finish(version, r, args):
    cloud = r["location"] == "cloud"
    print(TITLES[version])
    source = "from config/directory.json"
    if version == "v1" and args.role:
        source = "claimed with --role - v1 does NOT check it"
    elif version == "v1" and r["user"] not in identity.load_directory():
        source = "unknown user - v1 assumes 'employee'"
    print(f"User      : {r['user']}   roles: {', '.join(r['roles'])}   ({source})")
    print(f"Question  : {r['question']}")
    print(f"Search    : {r['mode']}, top {r['top_k']}, minimum similarity {config.MIN_SIMILARITY:.2f}")
    print("Model     : " + ("example cloud model (SIMULATED - this lab never sends anything to a cloud service)"
                            if cloud else f"{config.CHAT_MODEL}, local (on this VM)"))
    print_retrieved(r)
    shown = set()
    for hit, phrases in r["quarantined"]:                 # one line per document, not per chunk
        c = hit["chunk"]
        if c["doc_id"] in shown:
            continue
        shown.add(c["doc_id"])
        print(f"Held back : {c['doc_id']} - this document contains instructions aimed at the AI")
        print(f"            found: \"{phrases[0]}\" -> tell the owner: {c['owner']}")
    if r["residency_held"]:
        print(f"Residency : {r['residency_held']} matching chunk(s) are local-only, so not sent to a cloud model")

    if r["messages"] is None:
        if version == "v2":
            write_audit(r, "no_relevant_sources")
        print(f"\nAnswer    : {config.NO_ANSWER}\n            (nothing was sent to the AI)")
        return 0
    if args.dry_run or cloud:
        if version == "v2":
            write_audit(r, "dry_run")
        print("\nDRY RUN - this is exactly what would be sent" + (" to the cloud model" if cloud else "")
              + ". Nothing was sent.")
        for number, m in enumerate(r["messages"], 1):
            print(f"\n----- message {number} of {len(r['messages'])}, role: {m['role']} -----")
            print(m["content"].rstrip())
        size = sum(pipeline.estimate_tokens(m["content"]) for m in r["messages"])
        print(f"\n(about {size} input tokens)")
        return 0

    print("\nAsking the local model... (CPU: often 30-120 seconds)")
    try:
        text, usage = ollama_client.chat(r["messages"])
    except ollama_client.OllamaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    answer = safety.clean_for_terminal(text).strip()
    print(f"\nAnswer ({config.CHAT_MODEL} - your wording will differ):")
    print(answer)
    cited, unknown = citations_check(answer, len(r["used"]))
    if unknown:
        print(f"WARNING   : the answer cites sources that do not exist: {', '.join('S%d' % u for u in unknown)}")
    elif not cited and config.NO_ANSWER not in answer:
        print("WARNING   : the answer has no [S#] citations - check it against the sources below")
    print()
    print_sources(r)
    print(f"Usage     : input tokens {usage['input_tokens']} | output tokens {usage['output_tokens']}"
          f" | {usage['seconds']} s")
    if version == "v2":
        write_audit(r, "answered")
    return 0
