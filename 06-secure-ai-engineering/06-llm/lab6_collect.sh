#!/usr/bin/env bash
# Lab 6 - collect the evidence for Nova's threat model and control document.
#
#   cd ~/security-for-ai-boothcamp/06-secure
#   bash lab6_collect.sh             # baselines + lp, taint, allow + platform + redaction
#   bash lab6_collect.sh --approve   # also the interactive approve guard (answer N)
#
# Re-runs the Lab 5 attack (--scenario soc --task phish --offline) once per defence,
# so the attack is identical every time and only the guard changes. Everything lands
# in ~/lab6/evidence. Nothing is installed; nothing leaves the VM.
#
# Override locations with:  LAB5_DIR=...  EVIDENCE_DIR=...  PYTHON=...

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
LAB5="${LAB5_DIR:-$HERE/../05-llm}"
OUT="${EVIDENCE_DIR:-$HOME/lab6/evidence}"
PY="${PYTHON:-python3}"
DATA="$LAB5/lab5_hijack_data"
WITH_APPROVE=0
[ "${1:-}" = "--approve" ] && WITH_APPROVE=1

die() { echo "ERROR: $*" >&2; exit 1; }
[ -f "$LAB5/lab5_hijack.py" ] || die "lab5_hijack.py not found in $LAB5 (set LAB5_DIR=/path/to/05-llm)"
[ -d "$DATA" ] || die "$DATA not found"
mkdir -p "$OUT"

# run_case NAME [extra lab5_hijack.py args...]
run_case() {
  local name="$1"; shift
  echo
  echo "=== $name: python3 lab5_hijack.py --scenario soc --task phish --offline $*"
  rm -f "$DATA/outbox.log" "$DATA/audit.jsonl" "$OUT/$name".*
  ( cd "$LAB5" && "$PY" lab5_hijack.py --scenario soc --task phish --offline "$@" ) 2>&1 \
    | tee "$OUT/$name.console.txt"
  if [ -f "$DATA/audit.jsonl" ]; then
    cp "$DATA/audit.jsonl" "$OUT/$name.audit.jsonl"
  else
    echo "WARNING: no audit.jsonl written for $name"
  fi
  if [ -f "$DATA/outbox.log" ]; then
    cp "$DATA/outbox.log" "$OUT/$name.outbox.log"
    echo "--> outbox.log WRITTEN: an attacker-chosen action ran"
  else
    echo "outbox.log absent: nothing was sent or allowlisted" > "$OUT/$name.outbox-empty.txt"
    echo "--> outbox.log empty: nothing was sent or allowlisted"
  fi
}

echo "Lab 6 evidence -> $OUT"

# 1. Baselines: prove the threat is real, otherwise the guards prove nothing.
run_case baseline-none
run_case baseline-prompt --defense prompt

# 2. One run per code guard.
for g in lp taint allow; do
  run_case "guard-$g" --defense guard --guards "$g"
done

if [ "$WITH_APPROVE" = 1 ]; then
  echo
  echo ">>> The approve guard will ask y/N for each side effect. Answer N."
  run_case guard-approve --defense guard --guards approve
else
  echo
  echo "(skipped guard-approve: re-run with --approve and answer N to collect it)"
fi
rm -f "$DATA/outbox.log" "$DATA/audit.jsonl"

# 3. Platform evidence.
echo
echo "=== platform"
{
  echo "# $(date '+%Y-%m-%d %H:%M:%S %z') host=$(hostname)"
  ss -ltn 2>&1 | grep ':11434 ' || echo "no listener on port 11434"
} > "$OUT/ports.txt"
cat "$OUT/ports.txt"

if command -v ollama >/dev/null 2>&1; then
  ollama list > "$OUT/model.txt" 2>&1
  ollama show llama3.1:8b --modelfile > "$OUT/modelfile.txt" 2>&1
  cat "$OUT/model.txt"
else
  echo "ollama not found on PATH" > "$OUT/model.txt"
fi

{
  echo "# SHA-256 of the exact code and data that produced this evidence"
  "$PY" --version 2>&1
  ( cd "$LAB5" && sha256sum lab5_hijack.py lab5_hijack_data/*.json )
  ( cd "$HERE" && sha256sum lab6_*.py lab6_collect.sh )
} > "$OUT/code-hashes.txt" 2>&1

# 4. Redaction evidence (rule 2: redact at the tool boundary).
echo
echo "=== redaction"
"$PY" "$HERE/lab6_redact.py" --data "$DATA/soc.json" --case NW-4480 \
  --out "$OUT/case-notes-redacted.txt"

# 5. Check everything and write evidence_index.md.
echo
echo "=== evidence index"
"$PY" "$HERE/lab6_index.py" "$OUT"
status=$?

echo
echo "Done. Paste $OUT/evidence_index.md into section 6 of your document."
exit $status
