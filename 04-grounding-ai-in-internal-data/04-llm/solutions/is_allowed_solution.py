"""Lab 4.7 solution: copy this function over is_allowed() in retriever.py."""


def is_allowed(chunk, role):
    from retriever import ROLE_ACCESS
    allowed_labels = ROLE_ACCESS.get(role, set())   # unknown role -> empty set -> sees nothing
    return chunk.get("access") in allowed_labels
