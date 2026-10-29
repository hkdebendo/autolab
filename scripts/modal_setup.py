"""Modal set-up and checks, one step at a time (deploy first: modal deploy modal_app/uma_app.py).

    python scripts/modal_setup.py download                 # B: UMA checkpoint into the volume (CPU, once)
    python scripts/modal_setup.py licl                     # C: LiCl truth test, one small structure (T4)
    python scripts/modal_setup.py speed --gpus L4 A10G A100 H100 [--ps 0.5]   # MD speed per GPU (Li7P3S11)

No automatic retry: an error (quota, payment, timeout) stops the step and is printed.
"""

from __future__ import annotations

import argparse
import json
import time

from autolab import config


def _fn(name: str):
    import modal

    return modal.Function.from_name(config.MODAL_APP, name)


def download() -> None:
    print(json.dumps(_fn("download_checkpoint").remote(), indent=1))


def licl() -> None:
    from pymatgen.core import Lattice, Structure
    from pymatgen.io.ase import AseAtomsAdaptor

    from autolab.sim.serialize import atoms_from_dict, atoms_to_dict

    s = Structure.from_spacegroup("Fm-3m", Lattice.cubic(5.0), ["Li", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    t0 = time.perf_counter()
    res = _fn("relax_chunk").remote([atoms_to_dict(AseAtomsAdaptor.get_atoms(s))], config.UMA_PRECISION_ENERGY,
                                    config.RELAX_FMAX, config.RELAX_STEPS)[0]
    a = atoms_from_dict(res["atoms"]).cell.lengths().mean()
    ok = res["converged"] and 5.135 <= a <= 5.145
    print(f"LiCl from a = 5.0: a = {a:.4f} A (expected 5.135-5.145), converged {res['converged']}, "
          f"{res['steps']} steps, relax {res['seconds']} s, model load {res['model_load_s']} s, GPU {res['gpu']}, "
          f"call {time.perf_counter() - t0:.0f} s -> {'ok' if ok else 'WRONG'}")
    raise SystemExit(0 if ok else 1)


def speed(gpus: list[str], ps: float, deadline_s: float = config.MODAL_SPEED_DEADLINE_S) -> None:
    """One call per GPU, all at once; each result is saved as soon as it arrives. Calls still unfinished at the
    deadline (e.g. a GPU type that never got a container) are cancelled, so they cannot start later."""
    import modal.exception

    from autolab.agent.dynamics import parent_job

    job = parent_job(config.MD_CALIBRATION_PARENTS["fast"])  # Li7P3S11, UMA-relaxed (cache)
    n_steps = round(ps * 1000 / config.MD_TIMESTEP_FS)
    out = config.CACHE_DIR / "modal_speed.json"
    rows: dict[str, dict] = {}
    calls, t0 = {}, time.perf_counter()

    def save() -> None:
        out.write_text(json.dumps(list(rows.values()), indent=1), encoding="utf-8")

    for gpu in gpus:
        try:
            calls[gpu] = _fn("md_speed").with_options(gpu=gpu).spawn(
                job["atoms"], precision=config.UMA_PRECISION_MD, temperature_K=config.MD_SCREEN_TEMPERATURE_K,
                n_steps=n_steps)
        except Exception as e:  # quota, payment: reported, never retried
            rows[gpu] = {"requested": gpu, "error": f"{type(e).__name__}: {e}"[:300]}
            save()
    while calls:
        for gpu, call in list(calls.items()):
            try:
                rows[gpu] = {"requested": gpu, **call.get(timeout=0), "call_s": round(time.perf_counter() - t0, 1)}
            except modal.exception.FunctionTimeoutError as e:
                rows[gpu] = {"requested": gpu, "error": f"function timeout: {e}"[:300]}
            except (modal.exception.TimeoutError, TimeoutError):
                continue  # not finished yet
            except Exception as e:
                rows[gpu] = {"requested": gpu, "error": f"{type(e).__name__}: {e}"[:300]}
            del calls[gpu]
            save()
            print(json.dumps(rows[gpu]), flush=True)
        if calls and time.perf_counter() - t0 > deadline_s:
            for gpu, call in calls.items():
                call.cancel(terminate_containers=True)
                rows[gpu] = {"requested": gpu, "error": f"cancelled: no result after {deadline_s:.0f} s"}
                print(json.dumps(rows[gpu]), flush=True)
            calls.clear()
            save()
        time.sleep(5)
    print(f"saved to {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=["download", "licl", "speed"])
    ap.add_argument("--gpus", nargs="*", default=["L4", "A10G", "A100", "H100"])
    ap.add_argument("--ps", type=float, default=0.5)
    args = ap.parse_args()
    if args.step == "download":
        download()
    elif args.step == "licl":
        licl()
    else:
        speed(args.gpus, args.ps)


if __name__ == "__main__":
    main()
