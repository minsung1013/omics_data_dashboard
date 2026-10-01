"""EBI ENA adapter via the Portal API (study-level).

ENA (the European mirror of SRA) exposes a clean REST search. We query
study-level records whose title matches oncology/spatial terms and that became
public on/after the window. ENA carries no explicit license (open access).
"""
from .base import SourceAdapter
from util import iso_date

API = "https://www.ebi.ac.uk/ena/portal/api/search"

_TITLE_TERMS = [
    "cancer", "tumor", "tumour", "carcinoma", "neoplasm",
    "spatial", "Visium", "Xenium", "MERFISH", "CODEX", "GeoMx",
]


class ENAAdapter(SourceAdapter):
    name = "ENA"

    def fetch_since(self, since, cap):
        # ENA query_string: OR of wildcarded title matches + public-date bound.
        ors = " OR ".join(f'study_title="*{term}*"' for term in _TITLE_TERMS)
        query = f'({ors}) AND first_public>="{since.strftime("%Y-%m-%d")}"'
        rows = self.http.get_json(
            API,
            params={
                "result": "study",
                "query": query,
                "fields": "study_accession,study_title,study_description,"
                          "first_public,last_updated,center_name,scientific_name",
                "limit": cap,
                "format": "json",
            },
        )
        records = []
        for r in rows or []:
            acc = r.get("study_accession")
            if not acc:
                continue
            records.append({
                "id": f"ENA:{acc}",
                "name": r.get("study_title") or acc,
                "source": "ENA",
                "url": f"https://www.ebi.ac.uk/ena/browser/view/{acc}",
                "organism": r.get("scientific_name") or None,
                "size": None,
                "description": r.get("study_description", ""),
                "assay_text": r.get("study_title", ""),
                "published_date": iso_date(r.get("first_public")),
                "updated_date": iso_date(r.get("last_updated")),
                "owner": None,
                "organization": r.get("center_name") or None,
                "license_raw": None,       # ENA/SRA: no explicit license
                "access_level": "open",
            })
        return records
