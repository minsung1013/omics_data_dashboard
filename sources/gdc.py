"""NCI GDC adapter — project-level reference set (TCGA / CPTAC / TARGET / ...).

GDC projects are a stable, curated set (~90), so this is a reference landscape
rather than a stream of new deposits. We stamp every project with the current
GDC data-release date. Projects contain BOTH open and controlled-access tiers;
raw/germline data requires dbGaP, so we tag access conservatively.
"""
import re

from .base import SourceAdapter
from util import iso_date

PROJECTS = "https://api.gdc.cancer.gov/projects"
STATUS = "https://api.gdc.cancer.gov/status"


class GDCAdapter(SourceAdapter):
    name = "GDC"

    def _release_date(self):
        try:
            s = self.http.get_json(STATUS)
            m = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", s.get("data_release", ""))
            return iso_date(m.group(1)) if m else None
        except Exception:  # noqa: BLE001
            return None

    def fetch_since(self, since, cap):
        release = self._release_date()
        data = self.http.get_json(
            PROJECTS,
            params={
                "size": cap,
                "format": "json",
                "expand": "summary",
                "fields": "project_id,name,primary_site,disease_type,"
                          "released,dbgap_accession_number",
            },
        )
        hits = data.get("data", {}).get("hits", [])
        records = []
        for p in hits:
            pid = p.get("project_id")
            if not pid or not p.get("released"):
                continue
            summ = p.get("summary", {}) or {}
            cases = summ.get("case_count")
            sites = p.get("primary_site") or []
            dtypes = p.get("disease_type") or []
            controlled = bool(p.get("dbgap_accession_number"))
            records.append({
                "id": f"GDC:{pid}",
                "name": f"{pid} — {p.get('name', '')}",
                "source": "GDC",
                "url": f"https://portal.gdc.cancer.gov/projects/{pid}",
                "organism": "Homo sapiens",
                "size": f"{cases:,} cases" if cases else None,
                "description": f"Primary site: {', '.join(sites) if isinstance(sites, list) else sites}. "
                               f"Disease types: {', '.join(dtypes[:4])}"
                               f"{' …' if len(dtypes) > 4 else ''}. "
                               f"Files: {summ.get('file_count', 'n/a')}. "
                               f"Open + controlled-access tiers (raw/germline via dbGaP).",
                "assay_text": " ".join((sites if isinstance(sites, list) else [sites]) + dtypes),
                "cancer_type": None,  # tagging detects from primary_site/disease_type
                "published_date": release,
                "updated_date": release,
                "owner": None,
                "organization": "NCI Genomic Data Commons",
                # Mixed tiers → leave license unknown (open tier broadly usable,
                # controlled tier needs dbGaP); the nuance is in the description.
                "license_raw": None,
                "access_level": "open",
            })
        return records
