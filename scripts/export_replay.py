"""Export the light files of the 3D views of a recorded run (Li diffusion, MSD curves, relaxed structures).

    python scripts/export_replay.py results/<run> [--frames 400]

Reads result.json and the caches (never computes) and writes results/<run>/replay/ (index.json, structures/,
md/). Ids are written with "_" instead of ":" in file names.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autolab import config
from autolab.analysis.replay_export import export_run


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--frames", type=int, default=config.REPLAY_MD_FRAMES)
    args = ap.parse_args()
    result = json.loads((args.run / "result.json").read_text(encoding="utf-8"))
    index = export_run(result, args.run / "replay", args.frames)
    print(f"{len(index['structures'])} structures, {len(index['md'])} MD runs in {args.run / 'replay'}")


if __name__ == "__main__":
    main()
