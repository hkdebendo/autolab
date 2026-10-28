"""Save the structures used by the offline chem tests into tests/data (one MP request each)."""

import json
from pathlib import Path

from autolab.data import mp

DATA = Path(__file__).resolve().parent.parent / "tests" / "data"


def lowest_ehull_id(formula: str) -> str:
    with mp._rester() as mpr:
        docs = mpr.materials.summary.search(formula=formula, fields=["material_id", "energy_above_hull"])
    return str(min(docs, key=lambda d: d.energy_above_hull).material_id)


def save(name: str, material_id: str) -> None:
    structure = mp.get_structure(material_id)
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / f"{name}.json").write_text(json.dumps(structure.as_dict()), encoding="utf-8")
    print(f"{name}: {material_id}, {structure.composition.formula}")


if __name__ == "__main__":
    save("Li3PS4_mp-985583", "mp-985583")
    save("LiS4", lowest_ehull_id("LiS4"))
