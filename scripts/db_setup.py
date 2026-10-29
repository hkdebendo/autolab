"""Create or update the database tables (db/migrations) and import the recorded researches into the history.

    python scripts/db_setup.py [--no-import]

Needs DATABASE_URL in .env (Supabase session pooler). The 3D files of each recorded research are copied to the Modal
volume (runs/<conversation id>/...), where the service reads them. Safe to run again: applied migrations and
conversations already imported are left as they are.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from autolab import config
from autolab.agent.importer import RECORDED, import_run
from autolab.agent.service import Service
from autolab.store.conversations import PostgresStore

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-import", action="store_true")
    args = ap.parse_args()
    store = PostgresStore()
    applied = store.migrate()
    print(f"migrations applied: {applied or 'none (already up to date)'}")
    if args.no_import:
        return
    import modal

    volume = modal.Volume.from_name(config.MODAL_DATA_VOLUME)
    svc = Service(store, lambda: [], lambda cid: None)
    for folder, cid, title, request in RECORDED:
        run = ROOT / folder
        if not (run / "result.json").exists():
            continue
        new = store.get(cid) is None
        import_run(svc, run, cid, title, request, file_path=lambda c, name: f"runs/{c}/{name}")
        if new and (run / "replay").exists():
            with volume.batch_upload(force=True) as batch:
                batch.put_directory(str(run / "replay"), f"/runs/{cid}")
        print(f"{'imported' if new else 'already there'}: {title} ({cid})")
    print(f"history: {[c['title'] for c in store.list()]}")


if __name__ == "__main__":
    main()
