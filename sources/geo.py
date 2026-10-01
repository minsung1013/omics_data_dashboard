"""NCBI GEO adapter via E-utilities (db=gds, Series only).

GEO submissions carry no explicit license, so records are left license-unknown
(access is open). Captures oncology + spatial Series by publication date.
"""
import os

from .base import SourceAdapter
from util import iso_date

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

_TERM = (
    '("cancer"[All Fields] OR "tumor"[All Fields] OR "tumour"[All Fields] OR '
    '"carcinoma"[All Fields] OR "neoplasm"[All Fields] OR '
    '"spatial transcriptomic"[All Fields] OR "spatial transcriptomics"[All Fields] OR '
    '"spatial proteomic"[All Fields] OR "Visium"[All Fields] OR "Xenium"[All Fields] OR '
    '"MERFISH"[All Fields] OR "CODEX"[All Fields] OR "Slide-seq"[All Fields] OR '
    '"CosMx"[All Fields] OR "Stereo-seq"[All Fields]) AND "gse"[Entry Type]'
)


class GEOAdapter(SourceAdapter):
    name = "GEO"

    def _params(self, extra):
        p = dict(extra)
        key = os.environ.get("NCBI_API_KEY")
        if key:
            p["api_key"] = key
        return p

    def fetch_since(self, since, cap):
        search = self.http.get_json(
            ESEARCH,
            params=self._params({
                "db": "gds",
                "term": _TERM,
                "retmax": cap,
                "retmode": "json",
                "datetype": "pdat",
                "mindate": since.strftime("%Y/%m/%d"),
                "maxdate": "3000",
                "sort": "pub+date",
            }),
        )
        ids = search.get("esearchresult", {}).get("idlist", [])
        records = []
        for i in range(0, len(ids), 200):
            chunk = ids[i:i + 200]
            summ = self.http.get_json(
                ESUMMARY,
                params=self._params({
                    "db": "gds", "id": ",".join(chunk), "retmode": "json",
                }),
            )
            result = summ.get("result", {})
            for uid in result.get("uids", []):
                it = result.get(uid, {})
                acc = it.get("accession")
                if not acc:
                    continue
                n = it.get("n_samples")
                records.append({
                    "id": f"GEO:{acc}",
                    "name": it.get("title", acc),
                    "source": "GEO",
                    "url": f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={acc}",
                    "organism": it.get("taxon"),
                    "size": f"{n} samples" if n else None,
                    "description": it.get("summary", ""),
                    "assay_text": it.get("gdstype", ""),
                    "published_date": iso_date(it.get("pdat") or it.get("gdsdate")),
                    "updated_date": iso_date(it.get("pdat")),
                    "owner": None,
                    "organization": None,
                    "license_raw": None,          # GEO has no explicit license
                    "access_level": "open",
                })
        return records
