"""
schema.py - the contract for the AI's answer (structured output).

SCHEMA is sent to Ollama so the model is forced to answer in this shape.
validate() checks the answer again in our own code, because we never trust
the model blindly: if the answer does not match, the tool fails closed.
"""

import json

CATEGORIES = ["brute_force", "malware", "phishing", "misconfiguration",
              "service_outage", "benign", "other"]
SEVERITIES = ["low", "medium", "high", "critical"]
VERDICTS = ["likely_malicious", "suspicious", "likely_benign", "needs_more_data"]
CONFIDENCE = ["low", "medium", "high"]
# The AI may only RECOMMEND one of these. The "_request" ones need a human.
ACTIONS = ["no_action", "monitor", "open_ticket", "escalate_to_l2",
           "block_ip_request", "isolate_host_request", "rollback_request"]
HIGH_IMPACT_ACTIONS = ["block_ip_request", "isolate_host_request", "rollback_request"]

SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "severity": {"type": "string", "enum": SEVERITIES},
        "verdict": {"type": "string", "enum": VERDICTS},
        "confidence": {"type": "string", "enum": CONFIDENCE},
        "recommended_action": {"type": "string", "enum": ACTIONS},
        "summary": {"type": "string", "maxLength": 400},
        "indicators": {"type": "array", "items": {"type": "string", "maxLength": 120},
                       "maxItems": 8},
    },
    "required": ["category", "severity", "verdict", "confidence",
                 "recommended_action", "summary", "indicators"],
    "additionalProperties": False,
}


# The copy we send to Ollama keeps only the parts every Ollama version understands
# (types, allowed values, required fields). Our own validate() checks the rest.
MODEL_SCHEMA = {
    "type": "object",
    "properties": {
        key: {k: v for k, v in rule.items() if k in ("type", "enum", "items")}
        for key, rule in SCHEMA["properties"].items()
    },
    "required": SCHEMA["required"],
}
MODEL_SCHEMA["properties"]["indicators"]["items"] = {"type": "string"}


def validate(obj):
    """Return a list of problems. An empty list means the answer is valid."""
    if not isinstance(obj, dict):
        return ["the answer is not a JSON object"]
    errors = []
    props = SCHEMA["properties"]
    for key in SCHEMA["required"]:
        if key not in obj:
            errors.append(f"missing field '{key}'")
    for key in obj:
        if key not in props:
            errors.append(f"unexpected field '{key}'")
    for key, rule in props.items():
        if key not in obj:
            continue
        value = obj[key]
        if rule["type"] == "string":
            if not isinstance(value, str):
                errors.append(f"'{key}' must be text")
            elif "enum" in rule and value not in rule["enum"]:
                errors.append(f"'{key}' has a value that is not allowed: {value!r}")
            elif len(value) > rule.get("maxLength", 10 ** 9):
                errors.append(f"'{key}' is too long ({len(value)} characters)")
            elif not value.strip():
                errors.append(f"'{key}' is empty")
        elif rule["type"] == "array":
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                errors.append(f"'{key}' must be a list of text items")
            elif len(value) > rule["maxItems"]:
                errors.append(f"'{key}' has too many items ({len(value)})")
            elif any(len(v) > rule["items"]["maxLength"] for v in value):
                errors.append(f"'{key}' has an item that is too long")
    return errors


def parse_reply(text):
    """Turn the model's reply into (object, problems). Never raises."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Some models wrap JSON in a markdown fence. Remove it, but only that.
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        obj = json.loads(cleaned)
    except ValueError:
        return None, ["the answer is not valid JSON"]
    return obj, validate(obj)
