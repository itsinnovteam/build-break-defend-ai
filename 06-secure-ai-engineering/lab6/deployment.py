"""
deployment.py - choose a deployment pattern by data sensitivity.

The question: given what the system handles, where should the model run?
The lab's answer, and the industry default for sensitive data, is LOCAL hosting.
"""

# Ordered from least to most control over data.
PATTERNS = [
    {"id": "P1", "name": "Public SaaS LLM API",
     "control_over_data": "low",
     "good_for": "Public, non-sensitive content; prototypes.",
     "risk": "Your prompts and data leave your network to a third party.",
     "max_sensitivity": "public"},
    {"id": "P2", "name": "Vendor API with data-protection contract (no training, region-locked)",
     "control_over_data": "medium",
     "good_for": "Internal content where a contract and region lock are acceptable.",
     "risk": "Data still leaves your perimeter; you rely on the contract.",
     "max_sensitivity": "internal"},
    {"id": "P3", "name": "Private cloud / VPC-hosted open model",
     "control_over_data": "high",
     "good_for": "Confidential data that may live in your cloud tenancy.",
     "risk": "Must harden the tenancy; data stays in your cloud.",
     "max_sensitivity": "confidential"},
    {"id": "P4", "name": "Fully local / on-prem open-weight model (this lab)",
     "control_over_data": "highest",
     "good_for": "Confidential or regulated data that must not leave the network.",
     "risk": "You run and patch it; capacity is your own - the trade for full control.",
     "max_sensitivity": "regulated"},
]

# how sensitive, from low to high
_RANK = {"public": 0, "internal": 1, "confidential": 2, "regulated": 3, "untrusted-input": 2}


def recommend(sensitivity):
    """Return the patterns that are acceptable for this data sensitivity (most control first)."""
    need = _RANK.get(sensitivity, 3)
    ok = [p for p in PATTERNS if _RANK[p["max_sensitivity"]] >= need]
    return sorted(ok, key=lambda p: -_RANK[p["max_sensitivity"]])


def recommended_for_system(data_assets):
    """The single pattern that covers the most sensitive data asset in the system."""
    worst = max(_RANK.get(a["sensitivity"], 2) for a in data_assets)
    canonical = {0: "public", 1: "internal", 2: "confidential", 3: "regulated"}
    sens = canonical[worst]
    best = recommend(sens)[0]
    return sens, best


if __name__ == "__main__":
    import system_model as sm
    sens, best = recommended_for_system(sm.DATA_ASSETS)
    print(f"Most sensitive data in the system: {sens}")
    print(f"Recommended deployment: {best['id']} {best['name']}")
    print("\nAll patterns (most control first):")
    for p in sorted(PATTERNS, key=lambda p: -_RANK[p["max_sensitivity"]]):
        print(f"  {p['id']}  {p['name']:52s}  up to: {p['max_sensitivity']}")
