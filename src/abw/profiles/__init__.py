from __future__ import annotations

from .base import ConflictProfile
from .generic import PROFILE as GENERIC_PROFILE
from .manufacturing import PROFILE as MANUFACTURING_PROFILE


_PROFILES: dict[str, ConflictProfile] = {
    GENERIC_PROFILE.name: GENERIC_PROFILE,
    MANUFACTURING_PROFILE.name: MANUFACTURING_PROFILE,
}


def get_profile(name: str | None) -> ConflictProfile:
    normalized = str(name or "").strip().lower()
    if not normalized:
        return GENERIC_PROFILE
    return _PROFILES.get(normalized, GENERIC_PROFILE)
