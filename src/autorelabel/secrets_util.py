"""Readable random passwords and tokens (lab-only credentials)."""

from __future__ import annotations

import secrets

_SYLLABLES = ["ra", "ve", "lo", "ki", "mu", "sa", "te", "no", "pi", "da", "fe", "go", "zu", "ri", "ma", "ne"]


def password(syllables: int = 3, digits: int = 2) -> str:
    """Pronounceable, easy to type on a console (e.g. 'kimuve47'), no shell metacharacters."""
    word = "".join(secrets.choice(_SYLLABLES) for _ in range(syllables))
    return word + "".join(secrets.choice("23456789") for _ in range(digits))
