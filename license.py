"""License normalization and model-training usability classification.

Maps a raw license/access string to:
  - license_class:   CC0 | CC-BY | CC-BY-SA | CC-BY-NC | restricted | unknown
  - train_usability: usable | attribution | non_commercial | restricted | unknown

Philosophy: "public != trainable". Anything without an explicit permissive
license is treated conservatively (unknown => not usable by default in the UI).
"""
import re

# Ordered (first match wins). Patterns are matched against a lowercased,
# punctuation-normalized version of the raw string.
_RULES = [
    # Public domain / CC0
    (r"\bcc0\b|public domain|publicdomain|pddl|unlicense", "CC0", "usable"),
    # Non-commercial variants (check BEFORE plain CC-BY)
    (r"cc[\s\-]?by[\s\-]?nc|noncommercial|non[\s\-]?commercial", "CC-BY-NC", "non_commercial"),
    # Share-alike
    (r"cc[\s\-]?by[\s\-]?sa", "CC-BY-SA", "attribution"),
    # Attribution
    (r"cc[\s\-]?by\b|creative commons attribution|mit license|apache|bsd", "CC-BY", "attribution"),
    # Controlled / restricted access
    (
        r"controlled|dbgap|restricted|data use agreement|\bdua\b|managed access|"
        r"consent|embargo|request access|application required|ega[\s\-]|all rights reserved",
        "restricted",
        "restricted",
    ),
    # Generic "open access" with no explicit license -> treat as attribution-ish
    # but we keep it conservative: mark unknown unless a real license matched.
]

_CLASS_TO_USABILITY = {
    "CC0": "usable",
    "CC-BY": "attribution",
    "CC-BY-SA": "attribution",
    "CC-BY-NC": "non_commercial",
    "restricted": "restricted",
    "unknown": "unknown",
}


def classify_license(raw, access_level=None):
    """Return (license_class, train_usability) for a raw license string.

    access_level, if given ("open"/"controlled"), nudges the result: controlled
    access forces 'restricted' regardless of a permissive-looking label.
    """
    if access_level == "controlled":
        return "restricted", "restricted"

    if not raw:
        return "unknown", "unknown"

    text = re.sub(r"[_]+", " ", str(raw).strip().lower())
    for pattern, lic_class, usability in _RULES:
        if re.search(pattern, text):
            return lic_class, usability

    return "unknown", "unknown"


def usability_for_class(license_class):
    return _CLASS_TO_USABILITY.get(license_class, "unknown")
