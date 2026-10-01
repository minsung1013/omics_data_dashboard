"""Harvest orchestrator.

Runs every enabled source adapter, applies uniform tagging, filters to scope
(oncology OR spatial), merges with the existing catalog, flags items new in this
run, and writes docs/catalog.json + docs/meta.json.

Usage:
    python harvest.py                     # normal weekly run
    python harvest.py --only GEO --cap 5  # test one adapter
    python harvest.py --self-test         # run all enabled adapters, cap 5, no write
    python harvest.py --since-days 30      # override lookback
"""
import argparse
import json
import os
from datetime import date, datetime, timedelta, timezone

import config
import tagging
from sources.geo import GEOAdapter
from sources.zenodo import ZenodoAdapter
from sources.cellxgene import CellxgeneAdapter
from sources.hubmap import HubmapAdapter

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")
CATALOG = os.path.join(DOCS, "catalog.json")
META = os.path.join(DOCS, "meta.json")

REGISTRY = {
    "GEO": GEOAdapter,
    "Zenodo": ZenodoAdapter,
    "CELLxGENE": CellxgeneAdapter,
    "HuBMAP": HubmapAdapter,
}


def _load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def _determine_since(meta, override_days):
    if override_days is not None:
        return date.today() - timedelta(days=override_days)
    last_run = meta.get("last_run")
    if last_run:
        try:
            # small overlap to avoid missing boundary records
            return datetime.strptime(last_run, "%Y-%m-%d").date() - timedelta(days=2)
        except ValueError:
            pass
    return date.today() - timedelta(days=config.DEFAULT_LOOKBACK_DAYS)


def run_source(name, since, cap):
    adapter = REGISTRY[name]()
    raw = adapter.fetch_since(since, cap)
    kept = []
    for rec in raw:
        tagging.tag(rec)
        if rec.get("in_scope"):
            kept.append(rec)
    return raw, kept


def harvest(args):
    meta = _load_json(META, {})
    since = _determine_since(meta, args.since_days)
    print(f"[harvest] since={since}  sources={args.only or 'all-enabled'}")

    names = [args.only] if args.only else [
        n for n, cfg in config.SOURCES.items()
        if cfg.get("enabled") and n in REGISTRY
    ]

    fetched = []
    per_source = {}
    for name in names:
        cap = args.cap if args.cap else config.SOURCES.get(name, {}).get("cap", 100)
        try:
            raw, kept = run_source(name, since, cap)
            per_source[name] = len(kept)
            fetched.extend(kept)
            print(f"  [{name}] raw={len(raw)} in-scope={len(kept)} (cap={cap})")
        except Exception as e:  # noqa: BLE001 - isolate adapter failures
            per_source[name] = f"ERROR: {e}"
            print(f"  [{name}] ERROR: {e}")

    if args.self_test:
        print("\n[self-test] sample records:")
        for rec in fetched[:8]:
            print(f"  - {rec['id']} | {rec.get('modality')} | "
                  f"{rec.get('license_class')}/{rec.get('train_usability')} | "
                  f"{rec.get('published_date')} | {rec['name'][:60]}")
        print(f"\n[self-test] total in-scope: {len(fetched)} (not written)")
        return

    # Merge with existing catalog.
    existing = _load_json(CATALOG, [])
    by_id = {}
    for rec in existing:
        rec["new_this_week"] = False
        by_id[rec["id"]] = rec

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new_count = 0
    for rec in fetched:
        rec["fetched_at"] = now_iso
        if rec["id"] in by_id:
            # refresh fields but preserve first-seen date
            first_seen = by_id[rec["id"]].get("first_seen")
            rec["first_seen"] = first_seen or by_id[rec["id"]].get("fetched_at", now_iso)
            rec["new_this_week"] = False
            by_id[rec["id"]] = rec
        else:
            rec["first_seen"] = now_iso
            rec["new_this_week"] = True
            by_id[rec["id"]] = rec
            new_count += 1

    catalog = list(by_id.values())
    catalog.sort(key=lambda r: (r.get("published_date") or "", r.get("first_seen") or ""),
                 reverse=True)

    os.makedirs(DOCS, exist_ok=True)
    with open(CATALOG, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=1)

    meta_out = {
        "last_run": date.today().strftime("%Y-%m-%d"),
        "generated_at": now_iso,
        "since": since.strftime("%Y-%m-%d"),
        "total": len(catalog),
        "new_this_week": new_count,
        "per_source": per_source,
        "source_totals": _source_totals(catalog),
    }
    with open(META, "w", encoding="utf-8") as f:
        json.dump(meta_out, f, ensure_ascii=False, indent=1)

    print(f"\n[harvest] catalog total={len(catalog)}  new_this_week={new_count}")
    print(f"[harvest] wrote {CATALOG} and {META}")


def _source_totals(catalog):
    totals = {}
    for rec in catalog:
        totals[rec["source"]] = totals.get(rec["source"], 0) + 1
    return totals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="run a single source by name")
    ap.add_argument("--cap", type=int, help="override per-source result cap")
    ap.add_argument("--since-days", type=int, help="override lookback window (days)")
    ap.add_argument("--self-test", action="store_true",
                    help="run adapters and print samples without writing")
    args = ap.parse_args()
    if args.self_test and not args.cap:
        args.cap = 5
    harvest(args)


if __name__ == "__main__":
    main()
