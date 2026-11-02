"""Copy from the Modal volume the cached UMA relaxations of the hull references of some systems (no computation).

    python scripts/fetch_relax_cache.py Li-Mn-Ni-O-Ti Li-Mn-Al-O --ehull 0.0

A research run on Modal caches its relaxations in the volume, not on this computer; the error bars and the
benchmark read them from the local cache. Only the files of the listed systems' references are read (a few KB each).
"""

from __future__ import annotations

import argparse
import sys

from autolab import config
from autolab.data.mp import get_references
from autolab.sim.backend import _as_atoms_dict
from autolab.sim.serialize import atoms_key
from autolab.store.cache import JsonCache

VOLUME = "autolab-data"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("systems", nargs="+", help="chemical systems, e.g. Li-Mn-Ni-O")
    ap.add_argument("--ehull", type=float, default=config.CATHODE_HULL_REF_EHULL_MAX)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import modal

    vol = modal.Volume.from_name(VOLUME)
    cache = JsonCache(config.RELAX_CACHE_DIR)
    settings = {"model": config.UMA_MODEL, "precision": config.UMA_PRECISION_ENERGY, "fmax": config.RELAX_FMAX,
                "steps": config.RELAX_STEPS}
    done = set()
    for system in args.systems:
        refs = get_references(system.split("-"), ehull_max=args.ehull)
        have = copied = absent = 0
        for r in refs:
            key = atoms_key(_as_atoms_dict(r["structure"]), **settings)
            if key in done or cache.get(key) is not None:
                have += 1
                continue
            try:
                data = b"".join(vol.read_file(f"cache/relax/{key}.json"))
            except Exception:  # not relaxed on Modal either
                absent += 1
                continue
            path = config.RELAX_CACHE_DIR / f"{key}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            done.add(key)
            copied += 1
        print(f"{system}: {len(refs)} references, {have} already here, {copied} copied, {absent} not relaxed yet")


if __name__ == "__main__":
    main()
