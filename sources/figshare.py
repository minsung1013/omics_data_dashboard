"""figshare adapter via the public REST API.

The search endpoint returns only skeletal records, so we fetch each article's
detail for license, description, authors, and size. License is explicit, which
makes figshare (like Zenodo) reliable for the train-usability tag.
"""
from .base import SourceAdapter
from util import iso_date, human_size, strip_html, on_or_after

SEARCH = "https://api.figshare.com/v2/articles/search"

_SEARCH_FOR = (
    'cancer OR tumor OR carcinoma OR "spatial transcriptomics" OR '
    '"spatial proteomics" OR Visium OR Xenium OR MERFISH OR CODEX'
)


class FigshareAdapter(SourceAdapter):
    name = "figshare"

    def fetch_since(self, since, cap):
        records = []
        page = 1
        page_size = 50
        while len(records) < cap:
            hits = self.http.post_json(
                SEARCH,
                json={
                    "search_for": _SEARCH_FOR,
                    "page": page,
                    "page_size": page_size,
                    "order": "published_date",
                    "order_direction": "desc",
                },
            )
            if not hits:
                break
            stop = False
            for h in hits:
                pub = iso_date(h.get("published_date"))
                if not on_or_after(pub, since):
                    stop = True
                    continue
                try:
                    d = self.http.get_json(h["url_public_api"])
                except Exception:  # noqa: BLE001 - skip unfetchable detail
                    continue
                lic = (d.get("license") or {}).get("name")
                authors = d.get("authors") or []
                owner = authors[0].get("full_name") if authors else None
                records.append({
                    "id": f"FIGSHARE:{h['id']}",
                    "name": d.get("title") or h.get("title"),
                    "source": "figshare",
                    "url": d.get("url_public_html") or h.get("url_public_html"),
                    "organism": None,
                    "size": human_size(d.get("size")),
                    "description": strip_html(d.get("description", "")),
                    "assay_text": f"{d.get('title', '')} "
                                  f"{' '.join(d.get('tags', []) or [])}",
                    "published_date": pub,
                    "updated_date": iso_date(d.get("modified_date")),
                    "owner": owner,
                    "organization": None,
                    "license_raw": lic,
                    "access_level": "open",
                })
                if len(records) >= cap:
                    break
            if stop or len(hits) < page_size:
                break
            page += 1
        return records
