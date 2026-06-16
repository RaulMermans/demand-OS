import uuid


def new_id() -> str:
    return str(uuid.uuid4())


def short_id(prefix: str = "") -> str:
    """8-char hex short ID, optionally prefixed (e.g. 'prod_a1b2c3d4')."""
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}{suffix}" if prefix else suffix
