"""The rules each domain decides with, for the Settings page (read only): value from config.py, unit, why, status.

Status: "validated" (fixed by a truth test or a calibration, see SPEC 7), "justified" (a convention or a literature
value, reason given), "budget" (a cost or time limit of a research). Values are read from config at each call.
"""

from __future__ import annotations

from autolab import config

# (config name, label, unit, why, status); grouped by the step of the funnel they decide
_FUNNEL = "Screening"
_SLOW = "Slow tests"
_RANK = "Ranking and report"
_BUDGET = "Budgets of one research"

_MD = [
    ("MD_SCREEN_TEMPERATURE_K", "Molecular dynamics temperature", "K",
     "known parents separate at 600 K, not at 1000 K (calibration v2)", "validated"),
    ("MD_SCREEN_PS", "Length of one run", "ps", "calibration v2: enough hops for a diffusion coefficient", "validated"),
    ("MD_SCREEN_SEEDS", "Independent runs per structure", "", "calibration v2: blocks of the runs pooled", "validated"),
    ("MD_TIE_SIGMA", "Tie between a candidate and its parent", "combined errors",
     "|D − D(parent)| within this many standard errors = tied (calibration v2)", "validated"),
    ("MD_FRAMEWORK_D_RATIO_MAX", "Framework must stay intact", "of the ion's D",
     "an element of the framework diffusing faster than this means the crystal melts", "justified"),
]

RULES: dict[str, list[tuple[str, list[tuple]]]] = {
    "electrolyte": [
        (_FUNNEL, [
            ("EHULL_SYNTHESIZABLE", "Energy above the hull, at most", "eV/atom",
             "usual limit of possibly synthesizable predicted crystals", "justified"),
            ("BANDGAP_MIN", "Electronic band gap, at least", "eV",
             "an electrolyte must block electrons (DFT PBE gap of the champion)", "justified"),
            ("GENERATOR_N_ARRANGEMENTS", "Atomic arrangements per substitution", "",
             "random placements relaxed, the lowest in energy kept", "justified"),
        ]),
        (_SLOW, [
            ("ELECTRODES_TOP", "Candidates sent to the electrode tests", "", "lowest E_hull per substitution first", "justified"),
            ("ELECTRODE_EXCLUDED_PASSIVATION", "Excluded at lithium metal", "",
             "metallic products and a reaction of at least 0.1 eV/atom (Zhu, He and Mo 2015)", "justified"),
            ("AGENT_CATHODES", "Cathode tested against", "", "cobalt-free cathode, interface calibrated against MP", "justified"),
            *_MD,
            ("ITERATION_MD_SELECT_MAX", "Candidates simulated per round", "", "the model chooses which one", "budget"),
        ]),
        (_RANK, [
            ("CONDUCTIVITY_RANK_ORDER", "Order of the levels against the parent at 300 K", "",
             "ranges compared: overlap = tied; candidates without their own fit last", "justified"),
            ("RANK_TIE_BREAK", "Inside a level", "", "a stated convention, not a significant difference", "justified"),
            ("FINALISTS_MAX", "Finalists in the report", "", "", "justified"),
        ]),
        (_BUDGET, [
            ("LIVE_ITERATIONS", "Rounds of the error-driven loop", "", "", "budget"),
            ("LIVE_CANDIDATES", "Proposals per round", "", "", "budget"),
        ]),
    ],
    "cathode": [
        (_FUNNEL, [
            ("CATHODE_FORBIDDEN", "Forbidden elements", "", "cobalt-free cathodes", "justified"),
            ("CATHODE_EHULL_MAX", "Energy above the hull, at most", "eV/atom",
             "the commercial spinel LiMn2O4 sits at 0.045 above the MP hull", "justified"),
            ("CATHODE_VOLTAGE_MIN", "Average voltage, at least", "V vs Li/Li⁺", "useful energy", "justified"),
            ("CATHODE_VOLTAGE_MAX", "Average voltage, at most", "V vs Li/Li⁺", "above, common electrolytes decompose", "justified"),
            ("CATHODE_CAPACITY_MIN", "Theoretical capacity, at least", "mAh/g", "commercial cathodes store 140-200 mAh/g", "justified"),
            ("CATHODE_VOLUME_CHANGE_MAX", "Volume change on charge, at most", "%", "mechanical stability on cycling", "justified"),
            ("CATHODE_N_ARRANGEMENTS", "Atomic arrangements per substitution", "", "the lowest in energy kept", "justified"),
        ]),
        (_RANK, [
            ("CATHODE_VOLTAGE_SIGNIFICANT_V", "Voltage difference that counts against the parent", "V",
             "largest truth-test error (0.31 V on four known cathodes) rounded up", "validated"),
            ("CATHODE_FINALISTS_MAX", "Finalists in the report", "", "ranked by energy density", "justified"),
        ]),
        (_BUDGET, [
            ("LIVE_ITERATIONS", "Rounds of the error-driven loop", "", "", "budget"),
            ("LIVE_CANDIDATES", "Proposals per round", "", "", "budget"),
        ]),
    ],
    "sodium": [
        (_FUNNEL, [
            ("SODIUM_EHULL_MAX", "Energy above the hull, at most", "eV/atom", "as for the lithium electrolytes", "justified"),
            ("SODIUM_BANDGAP_MIN", "Electronic band gap, at least", "eV",
             "Na3SbS4, a working electrolyte, sits at 1.93 eV in DFT: 2.0 would reject it", "justified"),
        ]),
        (_SLOW, [
            ("ELECTRODE_EXCLUDED_PASSIVATION", "Excluded at sodium metal", "",
             "metallic products and a reaction of at least 0.1 eV/atom", "justified"),
            *_MD,
            ("SODIUM_MD_CAN_EXCLUDE", "Diffusion verdict may exclude and rank", "",
             "sodium calibration v2: Na vacancies in Na3SbS4 seen faster by 2.8 combined errors", "validated"),
            ("ITERATION_MD_SELECT_MAX", "Candidates simulated per round", "", "the model chooses which one", "budget"),
        ]),
        (_RANK, [
            ("FINALISTS_MAX", "Finalists in the report", "", "diffusion verdict, then E_hull per substitution", "justified"),
        ]),
        (_BUDGET, [
            ("LIVE_ITERATIONS", "Rounds of the error-driven loop", "", "", "budget"),
            ("LIVE_CANDIDATES", "Proposals per round", "", "", "budget"),
        ]),
    ],
}


def _shown(v):
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (tuple, list)):
        return ", ".join(str(x) for x in v)
    return v


def settings() -> dict:
    """Every domain with its rules grouped by step, values read from config now (JSON-serialisable)."""
    out = []
    for key, groups in RULES.items():
        label = config.DOMAIN_LABELS.get(key, {})
        out.append({"key": key, "label": label.get("label", key), "kind": label.get("kind"),
                    "groups": [{"title": title, "rules": [
                        {"name": name, "label": text, "value": _shown(getattr(config, name)), "unit": unit, "why": why,
                         "status": status} for name, text, unit, why, status in rules]} for title, rules in groups]})
    return {"domains": out, "source": "autolab/config.py",
            "note": "Read only: the rules are set in config.py; a change of a validated rule needs its truth test again."}
