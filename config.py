"""Scope, keyword, and source configuration for the omics dataset harvester.

Everything that controls *what* we collect lives here so the scope can be tuned
without touching adapter code.
"""

# How far back to look on the very first run (no previous meta.json).
DEFAULT_LOOKBACK_DAYS = 21

# ---------------------------------------------------------------------------
# Oncology scope
# ---------------------------------------------------------------------------
# A record is kept if it matches an oncology keyword OR is a spatial assay.
# Each canonical cancer type maps to lowercase substring patterns.
CANCER_TYPES = {
    "gastric": ["gastric", "stomach"],
    "colorectal": ["colorectal", "colon cancer", "rectal", "crc "],
    "breast": ["breast cancer", "breast carcinoma", "brca", "mammary carcinoma"],
    "lung": ["lung cancer", "nsclc", "sclc", "lung adenocarcinoma", "lung carcinoma"],
    "liver": ["hepatocellular", "liver cancer", "hcc ", "hepatic carcinoma"],
    "pancreatic": ["pancreatic cancer", "pdac", "pancreatic ductal"],
    "prostate": ["prostate cancer", "prostate carcinoma"],
    "ovarian": ["ovarian cancer", "ovarian carcinoma"],
    "melanoma": ["melanoma"],
    "glioma": ["glioma", "glioblastoma", "gbm "],
    "lymphoma": ["lymphoma"],
    "leukemia": ["leukemia", "leukaemia", "aml ", "cll "],
    "bladder": ["bladder cancer", "urothelial"],
    "kidney": ["renal cell", "kidney cancer", "rcc "],
    "head_neck": ["head and neck", "hnscc", "oral squamous"],
    "esophageal": ["esophageal", "oesophageal"],
    "cervical": ["cervical cancer", "cervical carcinoma"],
    "endometrial": ["endometrial", "uterine"],
    "sarcoma": ["sarcoma"],
    "neuroblastoma": ["neuroblastoma"],
    "pan_cancer": [
        "pan-cancer", "pan cancer", "tumor microenvironment",
        "tumour microenvironment", "tumor atlas", "cancer atlas",
    ],
}

# Generic cancer terms -> tags record as oncology (type "unspecified") when no
# specific type matched.
GENERIC_ONCOLOGY_TERMS = [
    "cancer", "tumor", "tumour", "carcinoma", "neoplasm", "malignant",
    "oncology", "metastasis", "metastatic", "adenocarcinoma", "oncogenic",
]

# ---------------------------------------------------------------------------
# Modality / platform normalization
# ---------------------------------------------------------------------------
# Lowercase substring -> normalized modality tag.
MODALITY_PATTERNS = {
    "spatial_transcriptomics": [
        "visium", "xenium", "merfish", "merscope", "slide-seq", "slideseq",
        "spatial transcriptom", "stereo-seq", "stereoseq", "cosmx", "geomx",
        "molecular cartography", "spatial gene expression", "curio",
        "seqfish", "dbit-seq", "hdst", "spatial rna",
    ],
    "spatial_proteomics": [
        "codex", "imaging mass cytometry", "imc ", "mibi", "cycif",
        "spatial proteom", "phenocycler", "akoya", "multiplexed ion beam",
        "co-detection by indexing", "immunofluorescence imaging",
    ],
    "scRNA_seq": [
        "single cell rna", "single-cell rna", "scrna", "10x 3'", "10x 5'",
        "chromium", "smart-seq", "drop-seq", "single-cell transcriptom",
        "single cell transcriptom", "snrna", "single-nucleus",
    ],
    "scATAC_seq": ["scatac", "single-cell atac", "single cell atac", "snatac"],
    "bulk_RNA_seq": [
        "rna-seq", "rna seq", "transcriptome profiling", "mrna-seq",
        "expression profiling by high throughput sequencing",
    ],
    "proteomics": ["mass spectrometry", "proteomic", "lc-ms", "tmt ", "itraq"],
    "wgs_wes": [
        "whole genome sequencing", "whole exome", "wgs ", "wes ",
        "variant calling", "dna-seq",
    ],
    "methylation": ["methylation", "bisulfite", "methylome", "epigenom"],
    "atac_seq": ["atac-seq", "atac seq"],
    "microarray": ["expression profiling by array", "microarray"],
}

# Platform display names (lowercase substring -> canonical label).
PLATFORM_PATTERNS = {
    "Visium": ["visium"],
    "Visium HD": ["visium hd"],
    "Xenium": ["xenium"],
    "MERFISH": ["merfish", "merscope"],
    "CosMx": ["cosmx"],
    "GeoMx": ["geomx"],
    "Stereo-seq": ["stereo-seq", "stereoseq"],
    "Slide-seq": ["slide-seq", "slideseq"],
    "seqFISH": ["seqfish"],
    "CODEX / PhenoCycler": ["codex", "phenocycler", "akoya"],
    "Imaging Mass Cytometry": ["imaging mass cytometry", "imc ", "hyperion"],
    "MIBI": ["mibi"],
    "CyCIF": ["cycif"],
    "10x Chromium": ["chromium", "10x 3'", "10x 5'"],
    "Smart-seq": ["smart-seq"],
    "Illumina": ["illumina"],
}

# Modalities that count as "spatial" for scope purposes.
SPATIAL_MODALITIES = {"spatial_transcriptomics", "spatial_proteomics"}

# ---------------------------------------------------------------------------
# Source toggles and per-source result caps (per harvest run)
# ---------------------------------------------------------------------------
SOURCES = {
    "GEO": {"enabled": True, "cap": 400},
    "Zenodo": {"enabled": True, "cap": 300},
    "CELLxGENE": {"enabled": True, "cap": 500},
    "HuBMAP": {"enabled": True, "cap": 400},
    "ENA": {"enabled": True, "cap": 300},
    "GDC": {"enabled": True, "cap": 120},      # ~93 projects (reference set)
    "figshare": {"enabled": True, "cap": 150},  # detail fetch per article (slower)
    "IDR": {"enabled": True, "cap": 300},      # projects + screens (reference set)
    # HTAN manifest is ~385 MB; run occasionally for seeding, not weekly.
    # Set HTAN_MANIFEST to a local cache to avoid re-downloading.
    "HTAN": {"enabled": False, "cap": 20},
    # Not yet integrated — no reliable public API:
    #   10xGenomics (bot-blocked HTML/Algolia), SODB (SPA, no public API found).
    "10xGenomics": {"enabled": False, "cap": 200},
    "SODB": {"enabled": False, "cap": 200},
}
