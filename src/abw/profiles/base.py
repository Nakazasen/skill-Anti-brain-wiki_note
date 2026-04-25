from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConflictProfile:
    name: str
    synonyms: dict[str, str]
    comparable_numeric_keys: frozenset[str]
    ignore_numeric_contexts: frozenset[str]
