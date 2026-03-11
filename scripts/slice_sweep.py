"""
Slice sweep audit script for coldplate-topobridge metric usefulness analysis.

This script runs bridge encoding on Stage 4 candidates and controls across a set of slices
to evaluate metric sensitivity and robustness.
"""

import json
import sys
from pathlib import Path

# Robust path resolution relative to repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from topobridge.adapters.stage4_velocity_adapter import load_stage4_field_bundle, Stage4SliceConfig
from topobridge.encode.field_to_signature import field_to_signatures

# Assume sibling repo is at the same level as this repo
BASE = REPO_ROOT.parent / "coldplate-design-engine" / "results" / "stage4_sim_full"

CANDIDATES = {
    "cand01_diamond_s1127": {
        "vel": BASE / "candidate_01_diamond_2d_s1127" / "velocity_field.npz",
        "prov": BASE / "candidate_01_diamond_2d_s1127" / "provenance.json",
    },
    "cand02_diamond_s1045": {
        "vel": BASE / "candidate_02_diamond_2d_s1045" / "velocity_field.npz",
        "prov": BASE / "candidate_02_diamond_2d_s1045" / "provenance.json",
    },
}

CONTROLS = {
    "ctrl_uniform_channel": {
        "vel": BASE / "baseline_uniform_channel_ctrl" / "velocity_field.npz",
        "prov": BASE / "baseline_uniform_channel_ctrl" / "provenance.json",
    },
    "ctrl_single_obstruction": {
        "vel": BASE / "baseline_single_obstruction_ctrl" / "velocity_field.npz",
        "prov": BASE / "baseline_single_obstruction_ctrl" / "provenance.json",
    },
}

SLICE_INDICES = [10, 15, 20, 25, 30, 35, 40]
SOLID_THRESHOLD = 1e-3


def extract_metrics(summary):
    ts = summary["theta_stats"]
    ms = summary["magnitude_stats"]
    gs = summary["gradient_stats"]
    return {
        "n_total": summary["n_total_pixels"],
        "n_solid": summary["n_solid_pixels"],
        "n_low_signal": summary["n_low_signal_pixels"],
        "n_active": summary["n_active_pixels"],
        "solid_frac": summary["solid_fraction"],
        "low_signal_frac": summary["low_signal_fraction"],
        "active_frac": summary["active_fraction"],
        "low_signal_threshold": summary["low_signal_threshold"],
        "theta_mean": ts["mean_rad"],
        "theta_std": ts["std_rad"],
        "theta_abs_mean": ts["abs_mean_rad"],
        "mag_mean": ms["mean"],
        "mag_std": ms["std"],
        "mag_global_max": ms["global_max"],
        "grad_mean": gs["mean_grad_mag"],
        "grad_max": gs["max_grad_mag"],
        "transverse_max_ratio": summary.get("transverse_max_ratio"),
    }


def run_sweep(name, vel_path, prov_path, slices):
    results = {}
    print(f"\n  {name}")
    for sidx in slices:
        cfg = Stage4SliceConfig(
            velocity_field_path=str(vel_path),
            provenance_path=str(prov_path),
            slice_axis="z",
            slice_index=sidx,
            solid_threshold_fraction=SOLID_THRESHOLD,
            include_axial_as_scalar=True,
        )
        bundle = load_stage4_field_bundle(cfg)
        output = field_to_signatures(bundle)
        m = extract_metrics(output.summary)
        results[sidx] = m
        print(f"    z={sidx:2d}: n_solid={m['n_solid']:4d}  n_active={m['n_active']:4d}  "
              f"theta_std={m['theta_std']:.5f}  grad_mean={m['grad_mean']:.5f}  "
              f"transverse_ratio={'N/A' if m['transverse_max_ratio'] is None else format(m['transverse_max_ratio'], '.3e')}")
    return results


if __name__ == "__main__":
    print("=== Bridge Metric Slice Sweep ===")
    print(f"Slice set: {SLICE_INDICES}")
    print(f"Solid threshold: {SOLID_THRESHOLD}")

    all_results = {}

    print("\n-- Candidates --")
    for name, paths in CANDIDATES.items():
        if not paths["vel"].exists():
            print(f"  SKIP {name}: {paths['vel']}")
            continue
        all_results[name] = run_sweep(name, paths["vel"], paths["prov"], SLICE_INDICES)

    print("\n-- Controls (single slice z=25 only) --")
    for name, paths in CONTROLS.items():
        if not paths["vel"].exists():
            print(f"  SKIP {name}: {paths['vel']}")
            continue
        all_results[name] = run_sweep(name, paths["vel"], paths["prov"], [25])

    out_path = REPO_ROOT / "artifacts" / "slice_sweep_metrics.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({str(k): {str(s): v for s, v in vv.items()} for k, vv in all_results.items()}, f, indent=2)
    print(f"\nMetrics JSON → {out_path}")
