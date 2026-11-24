"""Benchmark magnum.np on RTX 5070 (CUDA float64) against Phase 1 OOMMF baselines."""
import json
import math
import os
import time
from pathlib import Path

# Windows has no Triton backend for torch.compile; disable inductor compilation cleanly
# so all tensor/FFT operations execute directly via native PyTorch CUDA kernels.
os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")

import numpy as np
import torch
import magnumnp as mnp

MU0 = mnp.constants.mu_0
MS = 3e5
A_EX = 5e-12
KU = 8e4
ALPHA = 0.5
GAMMA = 2.21e5  # Match OOMMF gamma_G = 2.21e5 m/(A*s)

# Phase 1 OOMMF reference values
OOMMF_REF = {
    "square_2nm_Nx": 0.029568912837834117,
    "square_2nm_Nz": 0.940862174324332,
    "square_2nm_Ed_z_J": 8.512720401305783e-18,
    "square_2nm_relax_mz": 0.9999998468174442,
    "square_2nm_relax_E_J": 8.5125818092142e-18,
    "square_1nm_Nz": 0.940862174324332,
    "square_1nm_relax_mz": 0.9999998539201619,
    "square_1nm_relax_E_J": 8.512564403432529e-18,
    "circle_2nm_Nz": 0.943963748,
    "circle_2nm_area_nm2": 39936,
    "coercivity_bracket_mT": [180.0, 185.0],
}


def sync():
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def make_state(shape: str, cell_nm: float, dtype=torch.float64):
    torch.set_default_dtype(dtype)
    torch.set_default_device("cuda")
    if shape == "square":
        lx, ly = 200.0, 200.0
    elif shape == "circle":
        lx, ly = 228.0, 228.0
    else:
        raise ValueError(shape)
    nx, ny, nz = round(lx / cell_nm), round(ly / cell_nm), round(4.0 / cell_nm)
    dx = (cell_nm * 1e-9, cell_nm * 1e-9, cell_nm * 1e-9)
    origin = (-lx * 0.5e-9, -ly * 0.5e-9, 0.0)
    mesh = mnp.Mesh((nx, ny, nz), dx, origin=origin)
    state = mnp.State(mesh)

    x, y, z = state.SpatialCoordinate()
    if shape == "circle":
        # Match OOMMF mask: x^2 + y^2 < 40000 / pi (in nm^2)
        mask = (x * 1e9) ** 2 + (y * 1e9) ** 2 < (40000.0 / math.pi)
    else:
        mask = torch.ones((nx, ny, nz), dtype=torch.bool)

    ms_field = torch.zeros((nx, ny, nz, 1), dtype=dtype)
    ms_field[mask] = MS
    a_field = torch.zeros((nx, ny, nz, 1), dtype=dtype)
    a_field[mask] = A_EX
    ku_field = torch.zeros((nx, ny, nz, 1), dtype=dtype)
    ku_field[mask] = KU

    state.material = {
        "Ms": ms_field,
        "A": a_field,
        "Ku": ku_field,
        "Ku_axis": state.Constant([0.0, 0.0, 1.0]),
        "alpha": ALPHA,
    }
    vol = int(mask.sum().item()) * (cell_nm * 1e-9) ** 3
    area_nm2 = int(mask[:, :, 0].sum().item()) * (cell_nm ** 2)
    return state, mask, vol, area_nm2


def max_dm_dt_deg_ns(state, terms, mask):
    """Independent OOMMF-equivalent stopping metric: max |dm/dt| in deg/ns (no precession)."""
    h_tot = sum(term.h(state) for term in terms)
    m = state.m
    mxh = torch.linalg.cross(m, h_tot, dim=-1)
    mxh_mag = torch.linalg.norm(mxh[mask], dim=-1).max().item()
    # OOMMF RKF54 do_precess=0: |dm/dt| = gamma * alpha / (1 + alpha^2) * |m x H|
    rate_rad_s = GAMMA * ALPHA / (1.0 + ALPHA ** 2) * mxh_mag
    return rate_rad_s * (180.0 / math.pi) * 1e-9, mxh_mag


def test_static(shape: str, cell_nm: float, p: int = 20, dtype=torch.float64):
    sync()
    t0 = time.perf_counter()
    state, mask, vol, area_nm2 = make_state(shape, cell_nm, dtype=dtype)
    demag = mnp.DemagField(p=p)

    res = {"shape": shape, "cell_nm": cell_nm, "p": p, "dtype": str(dtype), "area_nm2": area_nm2}
    for idx, axis in enumerate("xyz"):
        vec = [0.0, 0.0, 0.0]
        vec[idx] = 1.0
        state.m = state.Constant(vec)
        state.m[~mask] = 0.0
        hd = demag.h(state)
        sync()
        mean_hd_i = hd[mask, idx].mean().item()
        ed = demag.E(state).item()
        n_field = -mean_hd_i / MS
        n_energy = 2.0 * ed / (MU0 * MS ** 2 * vol)
        res[f"N{axis}_field"] = n_field
        res[f"N{axis}_energy"] = n_energy
        res[f"Ed_{axis}_J"] = ed
    sync()
    res["elapsed_s"] = time.perf_counter() - t0
    res["trace_field"] = res["Nx_field"] + res["Ny_field"] + res["Nz_field"]
    res["max_field_energy_diff"] = max(abs(res[f"N{a}_field"] - res[f"N{a}_energy"]) for a in "xyz")
    return res


def relax_to_oommf_tol(state, terms, mask, stop_deg_ns=0.01, use_bb=True):
    """Relax with MinimizerBB (fast) or LLG, checking exact OOMMF max |dm/dt| <= stop_deg_ns."""
    # Convert stop_deg_ns -> |m x H| tolerance in A/m
    # OOMMF: 0.01 deg/ns -> |m x H| <= 1.974 A/m (exact: 0.01 / (gamma*alpha/(1+alpha^2) * 180/pi * 1e-9))
    factor = GAMMA * ALPHA / (1.0 + ALPHA ** 2) * (180.0 / math.pi) * 1e-9
    mxh_tol = stop_deg_ns / factor

    sync()
    t0 = time.perf_counter()
    if use_bb:
        minimizer = mnp.MinimizerBB(terms)
        # MinimizerBB checks max(|m x (m x H)|_component) < dm_tol.
        # Since |m x (m x H)| = |m x H|, use mxh_tol * 0.5 for safety margin.
        ok = minimizer.minimize(state, maxiter=5000, dm_tol=mxh_tol * 0.5)
    else:
        llg = mnp.LLGSolver(terms, no_precession=True)
        # Note: LLG.relax uses dm_tol in A/m scaled by gamma
        ok = llg.relax(state, maxiter=2000, dm_tol=mxh_tol * 0.5, dt=1e-11)
    sync()
    elapsed = time.perf_counter() - t0
    rate, mxh_max = max_dm_dt_deg_ns(state, terms, mask)
    e_total = sum(term.E(state).item() for term in terms)
    mean_m = state.m[mask].mean(dim=0).detach().cpu().numpy().tolist()
    return {
        "converged": bool(ok and rate <= stop_deg_ns * 1.01),
        "elapsed_s": elapsed,
        "max_dm_dt_deg_ns": rate,
        "max_mxh_A_m": mxh_max,
        "mean_m": mean_m,
        "energy_J": e_total,
    }


def test_zero_relax(cell_nm: float, p: int = 20, use_bb: bool = True, dtype=torch.float64):
    state, mask, vol, _ = make_state("square", cell_nm, dtype=dtype)
    v = np.array([0.01, 0.0, 1.0], dtype=np.float64)
    v /= np.linalg.norm(v)
    state.m = state.Constant(v.tolist())
    state.m[~mask] = 0.0

    demag = mnp.DemagField(p=p)
    exch = mnp.ExchangeField()
    anis = mnp.UniaxialAnisotropyField()
    terms = [demag, exch, anis]

    out = relax_to_oommf_tol(state, terms, mask, stop_deg_ns=0.01, use_bb=use_bb)
    out.update({"cell_nm": cell_nm, "p": p, "method": "MinimizerBB" if use_bb else "LLGSolver", "dtype": str(dtype)})
    return out


def test_reversal_bracket(cell_nm: float, p: int = 20, use_bb: bool = True, dtype=torch.float64):
    """Test seeded descending sweep matching Phase 1 protocol (+0.6 -> 0 -> -0.17 -> -0.18 -> -0.185 -> -0.19 -> -0.20 T)."""
    state, mask, vol, _ = make_state("square", cell_nm, dtype=dtype)
    v = np.array([0.01, 0.0, 1.0], dtype=np.float64)
    v /= np.linalg.norm(v)
    state.m = state.Constant(v.tolist())
    state.m[~mask] = 0.0

    demag = mnp.DemagField(p=p)
    exch = mnp.ExchangeField()
    anis = mnp.UniaxialAnisotropyField()
    ext = mnp.ExternalField([0.0, 0.0, 0.0])
    terms = [demag, exch, anis, ext]

    # Sweep fields (T) matching Phase 1 down-branch checkpoints + 5 mT refined window
    fields_T = [0.60, 0.20, 0.00, -0.160, -0.175, -0.180, -0.185, -0.190, -0.200]
    eps = 1e-3
    records = []
    sync()
    t_total0 = time.perf_counter()

    for b_T in fields_T:
        prev_mz = state.m[mask, 2].mean().item()
        # Apply Phase 1 seeded perturbation when field opposes current mean mz
        seeded = False
        if b_T * prev_mz < 0.0:
            seeded = True
            m_new = state.m.clone()
            m_new[mask, 0] += eps
            m_new[mask, 1] += 0.37 * eps
            norms = torch.linalg.norm(m_new[mask], dim=-1, keepdim=True)
            m_new[mask] = m_new[mask] / norms
            state.m = m_new

        ext.h = [0.0, 0.0, b_T / MU0]
        res = relax_to_oommf_tol(state, terms, mask, stop_deg_ns=0.01, use_bb=use_bb)
        records.append({
            "b_T": b_T,
            "seeded": seeded,
            "mean_mz": res["mean_m"][2],
            "elapsed_s": round(res["elapsed_s"], 4),
            "max_dm_dt_deg_ns": res["max_dm_dt_deg_ns"],
            "converged": res["converged"],
        })

    sync()
    total_s = time.perf_counter() - t_total0
    return {
        "cell_nm": cell_nm,
        "p": p,
        "method": "MinimizerBB" if use_bb else "LLGSolver",
        "dtype": str(dtype),
        "total_elapsed_s": total_s,
        "steps": records,
    }


def main():
    print(f"GPU: {torch.cuda.get_device_name(0)} | PyTorch: {torch.__version__} | magnum.np: {mnp.__version__}")
    results = {"gpu": torch.cuda.get_device_name(0), "torch": torch.__version__, "magnumnp": mnp.__version__}

    # 1. Static demag checks: square 2nm (p=20 and p=100), circle 2nm (p=20 and p=100), square 1nm (p=20)
    print("\n=== 1. STATIC DEMAG FACTORS ===")
    static_runs = [
        test_static("square", 2.0, p=20),
        test_static("square", 2.0, p=100),
        test_static("circle", 2.0, p=20),
        test_static("circle", 2.0, p=100),
        test_static("square", 1.0, p=20),
        test_static("square", 2.0, p=100, dtype=torch.float32),
    ]
    results["static"] = static_runs
    for r in static_runs:
        ref_key = f"{r['shape']}_{int(r['cell_nm'])}nm_Nz"
        ref_nz = OOMMF_REF[ref_key]
        err = abs(r["Nz_field"] - ref_nz)
        print(
            f"{r['shape']:6s} {r['cell_nm']:.0f}nm p={r['p']:3d} {r['dtype']:13s} | "
            f"Nz={r['Nz_field']:.9f} (OOMMF {ref_nz:.9f}, |dN|={err:.2e}) | "
            f"trace-1={r['trace_field']-1:.2e} | F-E diff={r['max_field_energy_diff']:.2e} | {r['elapsed_s']:.2f}s"
        )

    # 2. Zero-field relaxation (2nm & 1nm)
    print("\n=== 2. ZERO-FIELD RELAXATION (Square) ===")
    relax_runs = [
        test_zero_relax(2.0, p=100, use_bb=True),
        test_zero_relax(1.0, p=20, use_bb=True),
        test_zero_relax(2.0, p=100, use_bb=False),
    ]
    results["relax"] = relax_runs
    for r in relax_runs:
        ref_mz = OOMMF_REF[f"square_{int(r['cell_nm'])}nm_relax_mz"]
        ref_e = OOMMF_REF[f"square_{int(r['cell_nm'])}nm_relax_E_J"]
        print(
            f"{r['cell_nm']:.0f}nm {r['method']:11s} p={r['p']:3d} | "
            f"mz={r['mean_m'][2]:.9f} (d_mz={abs(r['mean_m'][2]-ref_mz):.2e}) | "
            f"E={r['energy_J']:.6e} (rel_dE={abs(r['energy_J']-ref_e)/ref_e:.2e}) | "
            f"rate={r['max_dm_dt_deg_ns']:.4f} deg/ns | conv={r['converged']} | {r['elapsed_s']:.2f}s"
        )

    # 3. Coercivity bracket test (2nm & 1nm)
    print("\n=== 3. REVERSAL BRACKET TEST (Square, seeded eps=1e-3) ===")
    rev_runs = [
        test_reversal_bracket(2.0, p=100, use_bb=True),
        test_reversal_bracket(1.0, p=20, use_bb=True),
    ]
    results["reversal"] = rev_runs
    for r in rev_runs:
        print(f"\nSquare {r['cell_nm']:.0f}nm ({r['method']}, p={r['p']}) total={r['total_elapsed_s']:.2f}s:")
        for s in r["steps"]:
            print(
                f"  b={s['b_T']:+7.3f} T | seeded={str(s['seeded']):5s} | "
                f"mz={s['mean_mz']:+12.9f} | rate={s['max_dm_dt_deg_ns']:.4f} | "
                f"conv={s['converged']} | {s['elapsed_s']:.2f}s"
            )

    out_path = Path("simulations/shape_design/benchmark_magnumnp.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved benchmark results to {out_path}")


if __name__ == "__main__":
    main()
