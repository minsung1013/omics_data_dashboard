"""Uniform tagging applied to every raw record: modality, platform, cancer type,
license class, and scope decision. Keeps classification consistent across sources.
"""
from datetime import date as _date

import config
from license import classify_license


def _text_blob(record):
    parts = [
        record.get("name", ""),
        record.get("description", ""),
        record.get("assay_text", ""),
        record.get("platform", ""),
        " ".join(record.get("cancer_type", []) or []),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def detect_modalities(blob, hint=None):
    found = []
    search = blob + (" " + hint.lower() if hint else "")
    for modality, patterns in config.MODALITY_PATTERNS.items():
        if any(p in search for p in patterns):
            found.append(modality)
    return found


def detect_platform(blob, explicit=None):
    if explicit:
        return explicit
    for label, patterns in config.PLATFORM_PATTERNS.items():
        if any(p in blob for p in patterns):
            return label
    return None


def detect_cancer_types(blob):
    types = []
    for ctype, patterns in config.CANCER_TYPES.items():
        if any(p in blob for p in patterns):
            types.append(ctype)
    if not types and any(t in blob for t in config.GENERIC_ONCOLOGY_TERMS):
        types.append("unspecified")
    return types


def tag(record):
    """Mutate `record` in place, adding normalized tags. Returns the record.

    Sets: modality, platform, cancer_type, license_class, train_usability,
    is_oncology, is_spatial, in_scope.
    """
    blob = _text_blob(record)

    modalities = record.get("modality") or detect_modalities(blob, record.get("assay_text"))
    record["modality"] = modalities

    record["platform"] = detect_platform(blob, record.get("platform"))

    cancer_types = record.get("cancer_type") or detect_cancer_types(blob)
    record["cancer_type"] = cancer_types

    lic_class, usability = classify_license(
        record.get("license_raw"), record.get("access_level")
    )
    record["license_class"] = lic_class
    record["train_usability"] = usability

    # Sanitize placeholder/future publication dates (some Zenodo records use
    # e.g. 2099-01-01); fall back to the update date when available.
    today = _date.today().isoformat()
    pub = record.get("published_date")
    if pub and pub > today:
        upd = record.get("updated_date")
        record["published_date"] = upd if (upd and upd <= today) else None

    is_spatial = any(m in config.SPATIAL_MODALITIES for m in modalities)
    is_oncology = bool(cancer_types)
    record["is_spatial"] = is_spatial
    record["is_oncology"] = is_oncology
    # Scope: oncology OR spatial (spatial kept even when non-cancer).
    record["in_scope"] = is_oncology or is_spatial

    record.setdefault("access_level", "open")
    return record
