"""Run the TPMS family SNR pilot (v1.1 constraints) on Stage 4 artifacts.

This script is read-only with respect to Stage 4 logic:
- Uses existing Stage 4 artifact files only (velocity_field.npz + provenance.json)
- Uses existing topobridge adapter + encoder modules
- Writes summary artifacts only (no copied velocity fields, no signatures.jsonl)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from topobridge.adapters.stage4_velocity_adapter import Stage4SliceConfig, load_stage4_field_bundle
from topobridge.encode.field_to_signature import field_to_signatures


BASE = REPO_ROOT.parent / "coldplate-design-engine" / "results" / "stage4_sim_full"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "tpms_family_snr_pilot_v1_1"
OUTPUT_JSON = OUTPUT_DIR / "pilot_summary.json"

SLICE_AXIS = "z"
SLICE_INDEX = 25
SOLID_THRESHOLD = 1e-3
LOW_SIGNAL_THRESHOLD = 0.01
SOLID_FRAC_GATE = (0.414, 0.453)
TRANSVERSE_MIN_GATE = 1e-4

DIAMOND_IDS = [
    "candidate_01_diamond_2d_s1127",
    "candidate_02_diamond_2d_s1045",
]
GYROID_ID = "candidate_gyroid_3d_s0000"


def _wrapped_angle_delta(delta: np.ndarray) -> np.ndarray:
    """Map angle deltas to [-pi, pi] to avoid branch-cut artifacts."""
    return np.arctan2(np.sin(delta), np.cos(delta))


def _circular_safe_mean_theta_gradient(theta_field: np.ndarray, active_mask: np.ndarray) -> float:
    """Compute circular-safe mean gradient magnitude of theta over active pixels.

    Uses wrapped angular differences on neighboring pixels to avoid 2pi wrap jumps.
    """
    if not np.any(active_mask):
        return 0.0

    gx = np.full(theta_field.shape, np.nan, dtype=np.float64)
    gy = np.full(theta_field.shape, np.nan, dtype=np.float64)

    dx_raw = _wrapped_angle_delta(theta_field[:, 1:] - theta_field[:, :-1])
    dy_raw = _wrapped_angle_delta(theta_field[1:, :] - theta_field[:-1, :])

    dx_valid = active_mask[:, 1:] & active_mask[:, :-1]
    dy_valid = active_mask[1:, :] & active_mask[:-1, :]

    dx_use = np.full(dx_raw.shape, np.nan, dtype=np.float64)
    dy_use = np.full(dy_raw.shape, np.nan, dtype=np.float64)
    dx_use[dx_valid] = dx_raw[dx_valid]
    dy_use[dy_valid] = dy_raw[dy_valid]

    gx[:, :-1] = dx_use
    gy[:-1, :] = dy_use

    grad_mag = np.sqrt(gx**2 + gy**2)
    valid = active_mask & np.isfinite(grad_mag)
    if not np.any(valid):
        return 0.0
    return float(np.mean(grad_mag[valid]))


def _artifact_paths(candidate_id: str) -> tuple[Path, Path]:
    vel_path = BASE / candidate_id / "velocity_field.npz"
    prov_path = BASE / candidate_id / "provenance.json"
    return vel_path, prov_path


def _load_candidate_metrics(candidate_id: str) -> dict:
    vel_path, prov_path = _artifact_paths(candidate_id)
    if not vel_path.exists():
        raise FileNotFoundError(f"Missing velocity artifact: {vel_path}")
    if not prov_path.exists():
        raise FileNotFoundError(f"Missing provenance artifact: {prov_path}")

    cfg = Stage4SliceConfig(
        velocity_field_path=str(vel_path),
        provenance_path=str(prov_path),
        slice_axis=SLICE_AXIS,
        slice_index=SLICE_INDEX,
        solid_threshold_fraction=SOLID_THRESHOLD,
        include_axial_as_scalar=True,
    )
    bundle = load_stage4_field_bundle(cfg)
    output = field_to_signatures(bundle, low_signal_threshold_fraction=LOW_SIGNAL_THRESHOLD)

    summary = output.summary
    active_mask = (~bundle.solid_mask.astype(bool)) & (~output.low_signal_mask)
    mean_theta_gradient_circular = _circular_safe_mean_theta_gradient(output.theta_field, active_mask)

    return {
        "candidate_id": candidate_id,
        "velocity_path": str(vel_path),
        "provenance_path": str(prov_path),
        "solid_fraction": float(summary["solid_fraction"]),
        "transverse_max_ratio": float(summary["transverse_max_ratio"])
        if summary.get("transverse_max_ratio") is not None
        else None,
        "n_active_pixels": int(summary["n_active_pixels"]),
        "theta_std_rad": float(summary["theta_stats"]["std_rad"]),
        "grad_mean_from_encoder": float(summary["gradient_stats"]["mean_grad_mag"]),
        "mean_theta_gradient_circular": mean_theta_gradient_circular,
    }


def _safe_snr(signal: float, noise_std: float) -> float | None:
    if noise_std <= 0.0:
        return None
    return float(signal / noise_std)


def main() -> int:
    if len(DIAMOND_IDS) != 2:
        raise RuntimeError("Pilot requires exactly two Diamond seeds.")

    candidate_metrics = {}
    for cid in DIAMOND_IDS + [GYROID_ID]:
        candidate_metrics[cid] = _load_candidate_metrics(cid)

    diamond_solid = np.array(
        [candidate_metrics[cid]["solid_fraction"] for cid in DIAMOND_IDS], dtype=np.float64
    )
    diamond_theta = np.array(
        [candidate_metrics[cid]["theta_std_rad"] for cid in DIAMOND_IDS], dtype=np.float64
    )
    diamond_grad = np.array(
        [candidate_metrics[cid]["mean_theta_gradient_circular"] for cid in DIAMOND_IDS],
        dtype=np.float64,
    )

    gyroid = candidate_metrics[GYROID_ID]
    gyroid_solid = float(gyroid["solid_fraction"])
    gyroid_theta = float(gyroid["theta_std_rad"])
    gyroid_grad = float(gyroid["mean_theta_gradient_circular"])

    diamond_theta_mean = float(np.mean(diamond_theta))
    diamond_theta_std = float(np.std(diamond_theta, ddof=0))
    diamond_grad_mean = float(np.mean(diamond_grad))
    diamond_grad_std = float(np.std(diamond_grad, ddof=0))

    theta_signal = abs(gyroid_theta - diamond_theta_mean)
    grad_signal = abs(gyroid_grad - diamond_grad_mean)

    snr_theta_std = _safe_snr(theta_signal, diamond_theta_std)
    snr_grad_mean = _safe_snr(grad_signal, diamond_grad_std)

    porosity_gate_pass = SOLID_FRAC_GATE[0] <= gyroid_solid <= SOLID_FRAC_GATE[1]
    transverse_gate_pass = (
        gyroid["transverse_max_ratio"] is not None
        and gyroid["transverse_max_ratio"] > TRANSVERSE_MIN_GATE
    )

    output = {
        "pilot_id": "tpms_family_snr_v1_1",
        "slice_policy": {
            "axis": SLICE_AXIS,
            "index": SLICE_INDEX,
            "solid_threshold_fraction": SOLID_THRESHOLD,
            "low_signal_threshold_fraction": LOW_SIGNAL_THRESHOLD,
        },
        "candidate_counts": {
            "diamond": len(DIAMOND_IDS),
            "gyroid": 1,
        },
        "inclusion_gates": {
            "solid_fraction_gate": list(SOLID_FRAC_GATE),
            "gyroid_solid_fraction": gyroid_solid,
            "porosity_gate_pass": porosity_gate_pass,
            "transverse_min_gate": TRANSVERSE_MIN_GATE,
            "gyroid_transverse_max_ratio": gyroid["transverse_max_ratio"],
            "transverse_gate_pass": transverse_gate_pass,
        },
        "metrics": {
            "per_candidate": candidate_metrics,
            "diamond_reference": {
                "solid_fraction_mean": float(np.mean(diamond_solid)),
                "theta_std_mean": diamond_theta_mean,
                "theta_std_std": diamond_theta_std,
                "mean_theta_gradient_circular_mean": diamond_grad_mean,
                "mean_theta_gradient_circular_std": diamond_grad_std,
            },
            "gyroid": {
                "theta_std": gyroid_theta,
                "mean_theta_gradient_circular": gyroid_grad,
            },
            "snr": {
                "theta_std_signal": float(theta_signal),
                "grad_mean_signal": float(grad_signal),
                "SNR_theta_std": snr_theta_std,
                "SNR_grad_mean": snr_grad_mean,
                "snr_formula": "abs(gyroid - mean(diamond)) / std(diamond), std=population(ddof=0)",
                "gradient_method": "circular_safe_wrapped_neighbor_deltas",
            },
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"Pilot summary written: {OUTPUT_JSON}")
    print(f"SNR_theta_std={snr_theta_std}")
    print(f"SNR_grad_mean={snr_grad_mean}")
    print(f"Porosity gate pass={porosity_gate_pass}")
    print(f"Transverse gate pass={transverse_gate_pass}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

