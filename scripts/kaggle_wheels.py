"""Build the wheels for the Kaggle GPU sessions once (CPU session, no GPU quota, no secret).

    python scripts/kaggle_wheels.py

Pushes the notebook config.KAGGLE_WHEELS_KERNEL, waits for it and prints its status (files, size, offline install
check). Only the small status file comes back to the PC; the wheels stay on Kaggle.
"""

from __future__ import annotations

import json

from autolab.sim.kaggle_gpu import build_wheels


def main() -> None:
    status = build_wheels()
    print(json.dumps({k: v for k, v in status.items() if k != "requirements"}, indent=1))
    if not status.get("ok"):
        raise SystemExit("the wheels notebook failed: see its log on Kaggle")


if __name__ == "__main__":
    main()
