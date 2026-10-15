from __future__ import annotations

import hashlib
import random


def deterministic_payload(size_bytes: int, seed: int = 2026) -> bytes:
    """Generate reproducible binary payloads without storing a fixture file."""
    if size_bytes < 0:
        raise ValueError("size_bytes must be non-negative")
    rng = random.Random(seed)
    block = bytes(rng.randrange(0, 256) for _ in range(min(size_bytes, 65536)))
    if not block and size_bytes:
        block = b"\x00"
    repeats, remainder = divmod(size_bytes, len(block)) if block else (0, 0)
    return (block * repeats) + block[:remainder]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
