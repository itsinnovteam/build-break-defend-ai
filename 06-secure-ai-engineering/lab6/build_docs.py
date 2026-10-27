"""
build_docs.py - generate the CISO-ready Threat Model & Control Document.

Writes:
  out/Threat_Model_and_Control_Document.md   (the source of truth, plain Markdown)
  out/Threat_Model_and_Control_Document.html (a styled, printable version)

Everything is derived from system_model / threat_model / controls / owasp /
deployment / compliance. Re-run it any time the system changes and the document
is regenerated - the paperwork cannot drift from the build.
"""
import datetime
import html
from pathlib import Path

import compliance
import controls
import deployment
import owasp
import system_model as sm
import threat_model as tm

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
TODAY = datetime.date.today().isoformat()


def md():
    L = []
    w = L.append
    w(f"# Threat Model & Control Document")
    w(f"**System:** {sm.SYSTEM['name']} ({sm.SYSTEM['version']})  ")
    w(f"**Owner:** {sm.SYSTEM['owner']}  ")
    w(f"**Date:** {TODAY}  ")
    w(f"**Hosting:** {sm.SYSTEM['hosting']}\n")
    w("> Prepared for security review. Every control in this document is backed by an "
      "automated test in Lab 5 (see the Evidence column). Compliance clause references are "
      "representative; map them to your own framework as needed.\n")

    # 1. Purpose and scope
    w("## 1. Purpose and scope")
    w(sm.SYSTEM["purpose"])
    w("\nThis document threat-models the agent, maps it to the OWASP LLM Top 10 and common "
      "compliance frameworks, records the deployment decision, and lists the controls with "
      "their evidence.\n")

    # 2. Data flow & trust boundaries
    w("## 2. Data flow and trust boundaries")
    w("**Components**\n")
    w("| ID | Component | Zone | Role |")
    w("|----|-----------|------|------|")
    for c in sm.COMPONENTS:
        w(f"| {c['id']} | {c['name']} | {c['zone']} | {c['desc']} |")
    w("\n**Data flows**\n")
    w("| Flow | From | To | Data | Untrusted? |")
    w("|------|------|----|------|-----------|")
    for f in sm.DATA_FLOWS:
        w(f"| {f['id']} | {sm.component(f['frm'])['name']} | {sm.component(f['to'])['name']} | {f['data']} | {'YES' if f['untrusted'] else 'no'} |")
    w("\n**Trust boundaries**\n")
    for b in sm.TRUST_BOUNDARIES:
        w(f"- **{b['id']} {b['name']}** (crosses {', '.join(b['crossing_flows'])}): {b['note']}")
    w("\n**Where untrusted input enters** (the first question to answer):\n")
    for p in tm.untrusted_entry_points():
        w(f"- `{p['flow']}` {p['from']} -> {p['to']} - {p['data']}")
    w("")

    # 3. Threat model
    w("## 3. Threat model (STRIDE over the boundaries)")
    s = tm.summary()
    w(f"{s['total']} threats identified: **{s['mitigated']} mitigated**, {s['not_applicable']} "
      f"not applicable, **{s['open']} open**.\n")
    w("| Threat | STRIDE | Target | Description | Decision | Control |")
    w("|--------|--------|--------|-------------|----------|---------|")
    for t in tm.THREATS:
        dec = t["status"] + (f" - {t['rationale']}" if t.get("rationale") else "")
        w(f"| {t['id']} | {t['stride']} | {t['element']} | {t['desc']} | {t['status']} | {t['control'] or '-'} |")
    w("")

    # 4. OWASP LLM Top 10
    w("## 4. OWASP LLM Top 10 (2025) coverage")
    w("| ID | Risk | How this system is exposed | Controls |")
    w("|----|------|----------------------------|----------|")
    for r in owasp.coverage():
        ctls = ", ".join(r["controls"]) if r["controls"] else "N/A by design"
        w(f"| {r['id']} | {r['title']} | {r['exposure']} | {ctls} |")
    w(f"\nRisks marked *N/A by design*: {', '.join(owasp.gaps())} - documented with rationale in the threat model (not unmanaged gaps).\n")

    # 5. Controls with evidence
    w("## 5. Controls and evidence")
    w("Each control names the Lab 5 test that proves it works. Run `python link_lab5.py` to execute them live.\n")
    for c in controls.CONTROLS:
        w(f"### {c['id']} - {c['name']}")
        w(f"- **What:** {c['what']}")
        w(f"- **Mechanism:** `{c['mechanism']}`")
        w(f"- **OWASP:** {', '.join(c['owasp'])}")
        w(f"- **Compliance:** " + "; ".join(f"{k} {v}" for k, v in c["compliance"].items()))
        w(f"- **Evidence (tests):** " + ", ".join(f"`{t}`" for t in c["evidence"]))
        w("")

    # 6. Deployment decision
    w("## 6. Deployment pattern decision")
    sens, best = deployment.recommended_for_system(sm.DATA_ASSETS)
    w(f"The most sensitive data handled is **{sens}**. Recommended pattern: **{best['id']} {best['name']}**.\n")
    w(f"> {best['good_for']} Trade-off: {best['risk']}\n")
    w("| Pattern | Control over data | Up to sensitivity | Good for |")
    w("|---------|-------------------|-------------------|----------|")
    for p in sorted(deployment.PATTERNS, key=lambda p: -deployment._RANK[p["max_sensitivity"]]):
        w(f"| {p['id']} {p['name']} | {p['control_over_data']} | {p['max_sensitivity']} | {p['good_for']} |")
    w("")

    # 7. Compliance mapping
    w("## 7. Compliance mapping")
    for fw in compliance.FRAMEWORKS:
        m = compliance.mapping(fw)
        w(f"### {fw}")
        w(f"*{compliance.FRAMEWORK_NOTE[fw]}* - {len(m)} clauses touched.\n")
        w("| Clause | Controls | Evidence tests |")
        w("|--------|----------|----------------|")
        for clause, info in m.items():
            w(f"| {clause} | {', '.join(info['controls'])} | {len(info['evidence'])} |")
        w("")

    # 8. Data governance
    w("## 8. Data governance")
    w("| Data asset | Sensitivity | PII | Residency |")
    w("|------------|-------------|-----|-----------|")
    for d in sm.DATA_ASSETS:
        w(f"| {d['name']} | {d['sensitivity']} | {'yes' if d['pii'] else 'no'} | {d['residency']} |")
    w("\nAll data stays on the VM (residency: on-VM). No asset is sent to any external service.\n")

    # 9. Residual risk & sign-off
    w("## 9. Residual risk and sign-off")
    w(f"- Threats: {s['mitigated']} mitigated, {s['not_applicable']} not applicable, **{s['open']} open**.")
    w("- Accepted / not-applicable items carry a documented rationale (see section 3).")
    w("- Residual risk: the local model can still mis-rate an alert (LLM09); mitigated by mandatory "
      "human approval for any action and by the deterministic fallback path.")
    w("\n| Role | Name | Decision | Date |")
    w("|------|------|----------|------|")
    w("| System owner | ______________ | ______________ | ______ |")
    w("| Security reviewer / CISO | ______________ | Approve / Reject | ______ |")
    w("")
    return "\n".join(L)


def to_html(markdown_text):
    """Tiny, dependency-free Markdown -> HTML (headings, tables, lists, code, bold)."""
    import re
    css = """body{font:15px/1.55 'Segoe UI',system-ui,Arial,sans-serif;color:#1C2733;max-width:960px;margin:0 auto;padding:28px 20px}
h1{font-family:Cambria,Georgia,serif;color:#0F2A44;border-bottom:3px solid#0E8C7E;padding-bottom:8px}
h2{font-family:Cambria,Georgia,serif;color:#0F2A44;margin-top:28px;border-bottom:1px solid#D8DEE6;padding-bottom:4px}
h3{color:#0E8C7E;margin-top:18px}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13.5px}
th,td{border:1px solid#D8DEE6;padding:6px 9px;text-align:left;vertical-align:top}
th{background:#0F2A44;color:#fff}tr:nth-child(even) td{background:#F4F6F9}
code{background:#EEF2F6;color:#7A3E00;padding:1px 5px;border-radius:4px;font-family:Consolas,monospace;font-size:12.5px}
blockquote{background:#E3F2EF;border-left:4px solid#0E8C7E;margin:10px 0;padding:8px 14px;color:#214A42}
li{margin:3px 0}"""
    lines = markdown_text.split("\n")
    out, i, in_tbl = [], 0, False
    def inline(t):
        t = html.escape(t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        return t
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[-\s|]+\|$", lines[i + 1]):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            out.append("<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells) + "</tr>")
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                row = [c.strip() for c in lines[i].strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
                i += 1
            out.append("</table>")
            continue
        if ln.startswith("### "): out.append(f"<h3>{inline(ln[4:])}</h3>")
        elif ln.startswith("## "): out.append(f"<h2>{inline(ln[3:])}</h2>")
        elif ln.startswith("# "): out.append(f"<h1>{inline(ln[2:])}</h1>")
        elif ln.startswith("> "): out.append(f"<blockquote>{inline(ln[2:])}</blockquote>")
        elif ln.startswith("- "): out.append(f"<li>{inline(ln[2:])}</li>")
        elif ln.strip() == "": out.append("")
        else: out.append(f"<p>{inline(ln)}</p>")
        i += 1
    body = "\n".join(out)
    return f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>Threat Model & Control Document</title><style>{css}</style></head><body>{body}</body></html>"


def main():
    text = md()
    (OUT / "Threat_Model_and_Control_Document.md").write_text(text, encoding="utf-8")
    (OUT / "Threat_Model_and_Control_Document.html").write_text(to_html(text), encoding="utf-8")
    print("Wrote:")
    print(f"  {OUT / 'Threat_Model_and_Control_Document.md'}")
    print(f"  {OUT / 'Threat_Model_and_Control_Document.html'}")
    s = tm.summary()
    print(f"\n{len(controls.CONTROLS)} controls | {len(tm.THREATS)} threats "
          f"({s['mitigated']} mitigated, {s['open']} open) | "
          f"{len(controls.all_evidence_tests())} evidence tests cited")


if __name__ == "__main__":
    main()
