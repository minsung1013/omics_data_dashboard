"""Zenodo adapter via the public REST API.

Zenodo exposes an explicit license id per record, which makes it one of the most
reliable sources for the train-usability classification.
"""
from .base import SourceAdapter
from util import iso_date, human_size, strip_html, on_or_after

API = "https://zenodo.org/api/records"

# NOTE: no hyphenated tokens — hyphens are operators in Zenodo's query_string
# parser (even quoted) and trigger HTTP 400.
_QUERY = (
    '(cancer OR tumor OR tumour OR carcinoma OR neoplasm OR '
    '"spatial transcriptomics" OR "spatial proteomics" OR Visium OR Xenium OR '
    'MERFISH OR CODEX OR CosMx OR GeoMx) AND '
    '(omics OR transcriptomics OR proteomics OR "single cell" OR spatial OR '
    'scRNA OR genomics)'
)


class ZenodoAdapter(SourceAdapter):
    name = "Zenodo"

    def fetch_since(self, since, cap):
        records = []
        page = 1
        page_size = 25  # Zenodo caps unauthenticated page size at 25
        while len(records) < cap:
            data = self.http.get_json(
                API,
                params={
                    "q": _QUERY,
                    "size": page_size,
                    "page": page,
                    "sort": "newest",
                    "all_versions": "false",
                },
            )
            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                break
            stop = False
            for h in hits:
                meta = h.get("metadata", {})
                # "newly added" signal = when it landed on Zenodo (created),
                # which is monotonic under sort=newest. publication_date is shown.
                added = iso_date(h.get("created"))
                pub = iso_date(meta.get("publication_date")) or added
                if not on_or_after(added, since):
                    stop = True  # newest-sorted: everything after is older
                    continue
                rtype = (meta.get("resource_type") or {}).get("type", "")
                if rtype in ("publication", "poster", "presentation", "lesson"):
                    continue  # keep datasets / software / images
                lic = meta.get("license") or {}
                lic_id = lic.get("id") if isinstance(lic, dict) else lic
                creators = meta.get("creators") or []
                owner = creators[0].get("name") if creators else None
                org = creators[0].get("affiliation") if creators else None
                total_bytes = sum(f.get("size", 0) for f in h.get("files", []) or [])
                recid = h.get("id") or h.get("conceptrecid")
                records.append({
                    "id": f"ZENODO:{recid}",
                    "name": meta.get("title", str(recid)),
                    "source": "Zenodo",
                    "url": h.get("links", {}).get("self_html")
                    or f"https://zenodo.org/records/{recid}",
                    "organism": None,
                    "size": human_size(total_bytes),
                    "description": strip_html(meta.get("description", "")),
                    "assay_text": f"{meta.get('title', '')} {' '.join(meta.get('keywords', []) or [])}",
                    "published_date": pub,
                    "updated_date": iso_date(h.get("updated")),
                    "owner": owner,
                    "organization": org,
                    "license_raw": lic_id,
                    "access_level": "open"
                    if h.get("metadata", {}).get("access_right", "open") == "open"
                    else "controlled",
                })
                if len(records) >= cap:
                    break
            if stop or len(hits) < page_size:
                break
            page += 1
        return records
