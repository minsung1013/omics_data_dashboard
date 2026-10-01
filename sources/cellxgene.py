"""CZI CELLxGENE Discover adapter via the public Curation API.

All CELLxGENE data is CC-BY 4.0, so these are reliably train-usable with
attribution. Joins the datasets listing (assay/disease/organism) with the
collections listing (dates/publisher) on collection_id.
"""
from .base import SourceAdapter
from util import iso_date, on_or_after

BASE = "https://api.cellxgene.cziscience.com/curation/v1"


def _labels(items):
    if not items:
        return []
    out = []
    for it in items:
        if isinstance(it, dict):
            lbl = it.get("label")
            if lbl:
                out.append(lbl)
        elif it:
            out.append(str(it))
    return out


class CellxgeneAdapter(SourceAdapter):
    name = "CELLxGENE"

    def fetch_since(self, since, cap):
        collections = {}
        for c in self.http.get_json(f"{BASE}/collections"):
            collections[c.get("collection_id")] = c

        datasets = self.http.get_json(f"{BASE}/datasets")
        records = []
        for d in datasets:
            cid = d.get("collection_id")
            coll = collections.get(cid, {})
            pub = iso_date(coll.get("published_at"))
            rev = iso_date(coll.get("revised_at")) or pub
            # Use the most recent of published/revised for the "new" signal.
            newest = max([x for x in (pub, rev) if x], default=None)
            if not on_or_after(newest, since):
                continue

            assays = _labels(d.get("assay"))
            diseases = _labels(d.get("disease"))
            organisms = _labels(d.get("organism"))
            tissues = _labels(d.get("tissue"))
            cell_count = d.get("cell_count")

            pub_meta = coll.get("publisher_metadata") or {}
            authors = pub_meta.get("authors") or []
            owner = None
            if authors:
                a = authors[0]
                owner = a.get("name") or " ".join(
                    x for x in (a.get("given"), a.get("family")) if x
                )
            consortia = coll.get("consortia") or []
            org = ", ".join(consortia) if consortia else pub_meta.get("journal")

            did = d.get("dataset_id")
            records.append({
                "id": f"CXG:{did}",
                "name": d.get("title") or coll.get("name") or did,
                "source": "CELLxGENE",
                "url": d.get("explorer_url")
                or f"https://cellxgene.cziscience.com/collections/{cid}",
                "organism": organisms[0] if organisms else None,
                "size": f"{cell_count:,} cells" if cell_count else None,
                "description": (coll.get("description") or "")[:600],
                "assay_text": " ".join(assays + diseases + tissues),
                "cancer_type": None,  # let tagging detect from disease labels
                "published_date": pub,
                "updated_date": rev,
                "owner": owner,
                "organization": org,
                "license_raw": "CC-BY-4.0",
                "access_level": "open",
            })
            if len(records) >= cap:
                break
        return records
