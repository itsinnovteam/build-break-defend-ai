"""
why_rag.py - Section 4.1: the same question, with and without our documents.

  A. The model alone      : llama3.1:8b answers from its training data only
  B. RAG                  : we retrieve our HR policy first, then the model answers with citations
  C. Not in the documents : retrieval finds nothing relevant, so we do not let the model guess

Run:  python why_rag.py            (2 AI calls, often 1 to 4 minutes on a CPU)
      python why_rag.py --dry-run  (no AI calls: shows what would be sent)
"""

import argparse
import sys

import assistant
import config
import ollama_client
from vectorstore import VectorStore

QUESTION = "How do I apply for emergency leave according to our company's HR policy?"
NOT_IN_DOCS = "How many vacation days do I get per year?"
USER = "ana"     # a regular employee (SOC analyst)


def ask_model(messages, dry_run):
    if dry_run:
        print("(dry run: not sent)")
        return
    print("Asking the local model... (CPU: often 30-120 seconds)")
    text, usage = ollama_client.chat(messages)
    print(text.strip())
    print(f"(input tokens {usage['input_tokens']}, {usage['seconds']} s)")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--dry-run", action="store_true", help="do not call the chat model")
    args = parser.parse_args(argv)
    try:
        store = VectorStore().open()
        print("=" * 72)
        print("A. THE MODEL ALONE (no company documents)")
        print("=" * 72)
        print(f"Question: {QUESTION}\n")
        ask_model([{"role": "user", "content": QUESTION}], args.dry_run)
        print("\n-> Check: does it name OUR form (HR-F-12), OUR portal (PeopleDesk) and OUR")
        print("   deadlines? It cannot: it has never seen our HR policy. Anything specific is a guess.\n")

        print("=" * 72)
        print(f"B. RAG (retrieve our documents first, as user '{USER}')")
        print("=" * 72)
        vector = ollama_client.embed([QUESTION])[0]
        r = assistant.prepare_v2(store, QUESTION, vector, USER)
        assistant.print_retrieved(r)
        print()
        ask_model(r["messages"], args.dry_run)
        print()
        assistant.print_sources(r)
        print("\n-> Check: every fact should carry a [S#] citation. Compare it with")
        print("   kb/HR-001_emergency_leave_policy.md.")
        print("   RAG improves grounding; it does not guarantee a correct answer. Verify the citation.\n")

        print("=" * 72)
        print("C. A QUESTION OUR DOCUMENTS DO NOT ANSWER")
        print("=" * 72)
        print(f"Question: {NOT_IN_DOCS}")
        vector = ollama_client.embed([NOT_IN_DOCS])[0]
        r = assistant.prepare_v2(store, NOT_IN_DOCS, vector, USER)
        assistant.print_retrieved(r)
        if r["messages"] is None:
            print(f"Answer   : {config.NO_ANSWER}\n           (nothing was sent to the AI: no guess)")
        else:
            ask_model(r["messages"], args.dry_run)
        store.close()
    except (FileNotFoundError, ollama_client.OllamaError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
