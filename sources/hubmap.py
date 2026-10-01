"""HuBMAP adapter via the public Search API.

HuBMAP is largely normal human tissue, but it is a strong source for SPATIAL
PROTEOMICS (CODEX/PhenoCycler, Imaging Mass Cytometry, MERFISH, etc.). Such
records enter scope via their spatial modality even without a cancer tag.
HuBMAP published data is CC-BY 4.0.
"""
from datetime import datetime, timezone

from .base import SourceAdapter
from util import iso_date

SEARCH = "https://search.api.hubmapconsortium.org/v3/portal/search"

_SPATIAL_ASSAYS = [
    "CODEX", "PhenoCycler", "IMC", "Imaging Mass Cytometry", "MERFISH",
    "MIBI", "CyCIF", "SeqFISH", "Visium", "Xenium", "Slide-seq",
]


class HubmapAdapter(SourceAdapter):
    name = "HuBMAP"

    def fetch_since(self, since, cap):
        since_ms = int(
            datetime(since.year, since.month, since.day, tzinfo=timezone.utc).timestamp() * 1000
        )
        query = {
            "size": cap,
            "_source": [
                "hubmap_id", "uuid", "data_types", "dataset_type", "title",
                "group_name", "created_timestamp", "last_modified_timestamp",
                "published_timestamp", "origin_samples.organ", "status",
                "mapped_data_types",
            ],
            "query": {
                "bool": {
                    "must": [
                        {"term": {"entity_type.keyword": "Dataset"}},
                        # Primary (user-submitted) datasets only — excludes
                        # processed derivatives ("Central Process",
                        # "Multi-Assay Split") that reuse the same titles and
                        # otherwise look like duplicates.
                        {"term": {"creation_action.keyword": "Create Dataset Activity"}},
                    ],
                    "should": [
                        {"match": {"data_types": a}} for a in _SPATIAL_ASSAYS
                    ] + [{"match": {"mapped_data_types": a}} for a in _SPATIAL_ASSAYS],
                    "minimum_should_match": 1,
                    "filter": [
                        {"range": {"last_modified_timestamp": {"gte": since_ms}}}
                    ],
                }
            },
            "sort": [{"last_modified_timestamp": {"order": "desc"}}],
        }
        data = self.http.post_json(SEARCH, json=query)
        hits = data.get("hits", {}).get("hits", [])
        records = []
        for h in hits:
            src = h.get("_source", {})
            uuid = src.get("uuid")
            if not uuid:
                continue
            dtypes = src.get("mapped_data_types") or src.get("data_types") or []
            if isinstance(dtypes, str):
                dtypes = [dtypes]
            organ = None
            osamples = src.get("origin_samples") or []
            if osamples and isinstance(osamples, list):
                organ = osamples[0].get("organ")
            hid = src.get("hubmap_id", uuid)
            base_title = src.get("title") or f"{', '.join(dtypes)} — {organ or 'tissue'}"
            # Always suffix the HuBMAP ID so near-identical auto-generated
            # titles remain distinguishable in the table.
            records.append({
                "id": f"HUBMAP:{hid}",
                "name": f"{base_title} [{hid}]",
                "source": "HuBMAP",
                "url": f"https://portal.hubmapconsortium.org/browse/dataset/{uuid}",
                "organism": "Homo sapiens",
                "size": None,
                "description": f"HuBMAP dataset. Assays: {', '.join(dtypes)}. Organ: {organ or 'n/a'}.",
                "assay_text": " ".join(dtypes + ([organ] if organ else [])),
                "published_date": iso_date(
                    src.get("published_timestamp") or src.get("last_modified_timestamp")
                ),
                "updated_date": iso_date(src.get("last_modified_timestamp")),
                "owner": None,
                "organization": src.get("group_name"),
                "license_raw": "CC-BY-4.0",
                "access_level": "open",
            })
        return records
