"""HTAN (Human Tumor Atlas Network) adapter — atlas-level records.

HTAN's portal manifest is a single very large JSON (~385 MB). We summarize it to
one record per atlas (~14), enriched with the set of assays present (so spatial
imaging/transcriptomics atlases are tagged correctly). Because the download is
heavy, this adapter is intended to run occasionally (seed) rather than weekly;
set HTAN_MANIFEST to a local cached copy to avoid re-downloading.
"""
import json
import os

import requests

from .base import SourceAdapter

MANIFEST_URL = "https://humantumoratlas.org/processed_syn_data.json"


class HTANAdapter(SourceAdapter):
    name = "HTAN"

    def _load_manifest(self):
        local = os.environ.get("HTAN_MANIFEST")
        if local and os.path.exists(local):
            with open(local, encoding="utf-8") as f:
                return json.load(f)
        # Stream to a temp file then load (avoids holding the raw text twice).
        r = requests.get(MANIFEST_URL, timeout=600, stream=True)
        r.raise_for_status()
        return r.json()

    def fetch_since(self, since, cap):
        data = self._load_manifest()
        atlases = data.get("atlases", [])

        # Aggregate assay names present per atlas id.
        assays_by_atlas = {}
        for f in data.get("files", []):
            aid = f.get("atlasid")
            a = f.get("assayName") or f.get("Component")
            if aid and a:
                assays_by_atlas.setdefault(aid, set()).add(a)

        records = []
        for at in atlases[:cap]:
            hid = at.get("htan_id")
            meta = at.get("AtlasMeta", {}) or {}
            title = (meta.get("title", {}) or {}).get("rendered") or at.get("htan_name") or hid
            assays = sorted(assays_by_atlas.get(hid, set()))
            cases = at.get("num_cases")
            biosp = at.get("num_biospecimens")
            size = None
            if cases or biosp:
                size = f"{cases or '?'} cases / {biosp or '?'} biospecimens"
            records.append({
                "id": f"HTAN:{hid}",
                "name": f"{title} [{at.get('htan_name', hid)}]",
                "source": "HTAN",
                # Fragment keeps each atlas URL unique while still landing on
                # the HTAN data portal explore page.
                "url": f"https://data.humantumoratlas.org/explore#{hid}",
                "organism": "Homo sapiens",
                "size": size,
                "description": f"HTAN tumor atlas. Lead: {meta.get('lead_institutions', 'n/a')}. "
                               f"Assays: {', '.join(assays) if assays else 'n/a'}.",
                "assay_text": f"{title} {' '.join(assays)}",
                "published_date": None,
                "updated_date": None,
                "owner": None,
                "organization": meta.get("lead_institutions") or None,
                "license_raw": "CC-BY-4.0",   # HTAN open-access data
                "access_level": "open",
            })
        return records
