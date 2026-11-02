"""The truth tests, calibrations and benchmarks of each domain, for the Benchmark & Tests page (read only).

Numbers copied from the recorded reports (results/ folders named in "source", SPEC section 7); verdict: "passed",
"failed" or "measured" (a measurement without a pass/fail criterion).
"""

from __future__ import annotations

from autolab import config


def _t(test, criterion, result, verdict, source=None, table=None):
    return {"test": test, "criterion": criterion, "result": result, "verdict": verdict, "source": source, "table": table}


TESTS: dict[str, list[dict]] = {
    "electrolyte": [
        _t("LiCl lattice parameter (UMA relaxation)", "5.10–5.18 Å", "5.135 Å (experiment ≈ 5.13)", "passed"),
        _t("E_hull of Li3PS4 polymorphs", "within 0.01 eV/atom of MP", "0.000 / 0.007 / 0.015 eV/atom (MP 0.000 / 0.007 / 0.014)",
           "passed"),
        _t("Electrochemical window of Li3PS4", "1.6–1.9 V to 2.2–2.5 V", "1.74–2.36 V (literature 1.71–2.31)", "passed"),
        _t("Li3PS4 / LiFePO4 interface", "within 0.05 eV/atom of MP", "−0.144 eV/atom (MP −0.133)", "passed"),
        _t("MD calibration, plan A", "Li7P3S11 faster than β-Li3PS4 by > 2σ at 600 and 700 K",
           "right order, 1.9σ and 0.4σ", "failed"),
        _t("MD calibration v2", "Li7P3S11 faster than β-Li3PS4 by > 2σ at 600 K, frameworks intact",
           "D ratio 2.04, 3.6σ, frameworks intact", "passed", "results/2026-10-29_md_calibration"),
        _t("MD on two GPUs (A10G vs H100)", "same D within 2σ", "−0.0σ and +0.4σ", "passed"),
        _t("Conductivity at 300 K", "Li7P3S11 > β-Li3PS4, each within ×10 of experiment",
           "100 mS/cm (58–170) and 1.2 (0.43–3.2)", "passed", None,
           {"head": ["Compound", "UMA (mS/cm)", "Experiment (mS/cm)"],
            "rows": [["Li7P3S11", "100 (58–170)", "3.2–17"], ["β-Li3PS4", "1.2 (0.43–3.2)", "0.16"]]}),
        _t("UMA vs DFT on known compounds", "—", "0.004–0.006 eV/atom (sulfides), ≤ 0.012 (polysulfides)", "measured",
           "results/2026-11-01_uma_error_bars"),
        _t("Blind benchmark (known compounds through the funnel)", "—", "good 2/4 pass · bad 8/8 rejected · hard negatives 5/5 rejected",
           "measured", "results/2026-11-01_benchmark_hard",
           {"head": ["Group", "After stability + band gap", "After Li metal + diffusion"],
            "rows": [["4 good electrolytes", "3/4 pass", "2/4 pass"], ["8 bad compounds", "8/8 rejected", "8/8 rejected"],
                     ["5 hard negatives", "0/5 rejected", "5/5 rejected"]]}),
    ],
    "cathode": [
        _t("Average voltage of 4 known cathodes", "each within 0.4 V of experiment, right order",
           "largest error 0.31 V, order right", "passed", "results/2026-11-02_cathode_truth",
           {"head": ["Cathode", "UMA (V)", "Experiment (V)", "Capacity (mAh/g)"],
            "rows": [["LiFePO4", "3.45", "3.45", "169.9"], ["LiMnPO4", "3.79", "4.10", "170.9"],
                     ["LiMn2O4", "3.82", "4.05", "148.2"], ["LiNi₀.₅Mn₁.₅O₄", "4.72", "4.70", "146.7"]]}),
        _t("Blind benchmark (10 known compounds)", "expected outcome fixed before the runs", "9/10 as expected",
           "measured", "results/2026-11-02_cathode_benchmark",
           {"head": ["Group", "As expected"],
            "rows": [["Good cathodes (LiNiO2, Li3V2(PO4)3)", "2/2"], ["Bad compounds (cobalt, no removable Li)", "6/6"],
                     ["Hard negatives (LiTiO2, Li2FeSiO4)", "1/2 — Li2FeSiO4 3.29 V vs 2.8 V"]]}),
        _t("UMA vs DFT on the cathode systems", "—", "0.005–0.010 eV/atom on 8 systems", "measured",
           "results/2026-11-02_cathode_error_bars"),
    ],
    "sodium": [
        _t("MD calibration 1: two different crystals", "Na3SbS4 faster than Na3PS4 by > 2σ at 600 K",
           "reverse order, ratio 0.33 ± 0.29", "failed", "results/2026-11-02_sodium_md_calibration"),
        _t("MD calibration 2: crystal against its own parent", "Na vacancies (W on Sb) speed Na up by > 2σ",
           "28× faster, +2.8σ, frameworks intact", "passed", "results/2026-11-02_sodium_md_calibration_v2",
           {"head": ["Structure", "D (cm²/s)"],
            "rows": [["Na23Sb7WS32 (vacancies)", "2.1 ± 0.7 × 10⁻⁶"], ["Na3SbS4", "7.6 ± 6.0 × 10⁻⁸"]]}),
    ],
}


def benchmarks() -> dict:
    """Every domain with its tests (JSON-serialisable)."""
    out = []
    for key, tests in TESTS.items():
        label = config.DOMAIN_LABELS.get(key, {})
        counts = {v: sum(t["verdict"] == v for t in tests) for v in ("passed", "failed", "measured")}
        out.append({"key": key, "label": label.get("label", key), "tests": tests, "counts": counts})
    return {"domains": out}
