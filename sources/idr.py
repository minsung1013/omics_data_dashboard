"""Image Data Resource (IDR) adapter via the OMERO JSON API.

IDR is a strong source for imaging-based assays including SPATIAL PROTEOMICS
(Imaging Mass Cytometry, CODEX, MIBI, CyCIF) and cancer histopathology. We list
study-level containers (projects + screens). IDR has no per-container date in
this API, so published_date is left null; records enter scope via oncology or
spatial tags detected from name/description. IDR data are CC-BY 4.0 by policy.
"""
from .base import SourceAdapter

BASE = "https://idr.openmicroscopy.org/api/v0/m"


class IDRAdapter(SourceAdapter):
    name = "IDR"

    def _containers(self, kind, cap):
        """kind: 'projects' (show=project-) or 'screens' (show=screen-)."""
        out = []
        data = self.http.get_json(f"{BASE}/{kind}/", params={"limit": cap})
        show = "project" if kind == "projects" else "screen"
        for c in data.get("data", []):
            cid = c.get("@id")
            name = c.get("Name") or ""
            out.append({
                "id": f"IDR:{show}-{cid}",
                "name": name or f"IDR {show} {cid}",
                "source": "IDR",
                "url": f"https://idr.openmicroscopy.org/webclient/?show={show}-{cid}",
                "organism": None,
                "size": None,
                "description": c.get("Description", ""),
                "assay_text": f"{name} {c.get('Description', '')}",
                "published_date": None,
                "updated_date": None,
                "owner": None,
                "organization": "Image Data Resource (EMBL-EBI)",
                "license_raw": "CC-BY-4.0",   # IDR default policy
                "access_level": "open",
            })
        return out

    def fetch_since(self, since, cap):
        half = max(1, cap // 2)
        records = self._containers("projects", half)
        records += self._containers("screens", half)
        return records
