"""
test_lab6.py - the lab IS the traceability. These tests prove the governance
artifacts are complete and internally consistent, so the CISO document cannot
ship with a hole in it. No model, no network, no GPU - pure checks on the model.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import compliance
import controls
import deployment
import owasp
import system_model as sm
import threat_model as tm


# ---- system model is well-formed --------------------------------------------
def test_components_have_unique_ids():
    ids = [c["id"] for c in sm.COMPONENTS]
    assert len(ids) == len(set(ids))


def test_every_data_flow_endpoint_exists():
    ids = {c["id"] for c in sm.COMPONENTS}
    for f in sm.DATA_FLOWS:
        assert f["frm"] in ids and f["to"] in ids


def test_there_is_at_least_one_untrusted_entry_point():
    assert len(sm.untrusted_entry_points()) >= 1


def test_trust_boundary_flows_are_real():
    flow_ids = {f["id"] for f in sm.DATA_FLOWS}
    for b in sm.TRUST_BOUNDARIES:
        for f in b["crossing_flows"]:
            assert f in flow_ids


# ---- controls are complete and evidenced ------------------------------------
def test_controls_have_unique_ids():
    ids = [c["id"] for c in controls.CONTROLS]
    assert len(ids) == len(set(ids))


def test_every_control_cites_evidence():
    for c in controls.CONTROLS:
        assert c["evidence"], f"{c['id']} has no evidence test"


def test_every_control_maps_to_at_least_one_owasp():
    valid = {o[0] for o in owasp.TOP10}
    for c in controls.CONTROLS:
        assert c["owasp"], f"{c['id']} maps to no OWASP risk"
        assert set(c["owasp"]) <= valid


def test_every_control_maps_to_every_framework():
    for c in controls.CONTROLS:
        for fw in compliance.FRAMEWORKS:
            assert fw in c["compliance"], f"{c['id']} missing {fw}"


# ---- threat model is complete -----------------------------------------------
def test_no_threat_is_left_undecided():
    assert tm.validate() == []


def test_no_open_threats():
    assert tm.summary()["open"] == 0


def test_mitigated_threats_point_to_real_controls():
    ids = {c["id"] for c in controls.CONTROLS}
    for t in tm.THREATS:
        if t["status"] == "Mitigated":
            assert t["control"] in ids


def test_not_applicable_threats_have_rationale():
    for t in tm.THREATS:
        if t["status"] != "Mitigated":
            assert t.get("rationale")


# ---- OWASP coverage ---------------------------------------------------------
def test_all_ten_owasp_risks_are_listed():
    assert len(owasp.TOP10) == 10


def test_only_expected_owasp_items_are_not_applicable():
    assert set(owasp.gaps()) <= {"LLM04", "LLM07", "LLM08"}


def test_prompt_injection_is_covered():
    assert controls.controls_for_owasp("LLM01"), "LLM01 must have at least one control"


# ---- deployment & compliance ------------------------------------------------
def test_sensitive_data_recommends_local_hosting():
    _, best = deployment.recommended_for_system(sm.DATA_ASSETS)
    assert best["id"] == "P4", "confidential data should recommend fully local hosting"


def test_every_framework_has_mapped_clauses():
    for fw in compliance.FRAMEWORKS:
        assert compliance.mapping(fw), f"{fw} has no mapped controls"


# ---- the document builds ----------------------------------------------------
def test_document_builds_and_mentions_evidence(tmp_path, monkeypatch):
    import build_docs
    text = build_docs.md()
    assert "Threat Model & Control Document" in text
    assert "OWASP LLM Top 10" in text
    # every control id appears in the document
    for c in controls.CONTROLS:
        assert c["id"] in text
    # the HTML renders without error
    htmltext = build_docs.to_html(text)
    assert "<table>" in htmltext and "<h1>" in htmltext
