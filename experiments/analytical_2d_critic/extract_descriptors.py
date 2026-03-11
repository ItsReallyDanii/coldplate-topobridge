"""Extract bridge-style descriptors for the EXPERIMENTAL_SANDBOX 2D critic demo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from topobridge.adapters.coldplate_field_loader import load_field_bundle
from topobridge.encode.field_to_signature import field_to_signatures
from topobridge.io.schema_validate import validate_field_frame, validate_signature_record


EXPERIMENT_LABEL = "EXPERIMENTAL_SANDBOX_ANALYTICAL_2D_CRITIC"
DEFAULT_LOW_SIGNAL_THRESHOLD = 0.01


def extract_case(
    artifact_path: Path,
    output_dir: Path,
    low_signal_threshold: float = DEFAULT_LOW_SIGNAL_THRESHOLD,
) -> Dict[str, object]:
    """Encode one generated field and emit sandbox descriptor files."""
    artifact_path = Path(artifact_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    sidecar_path = artifact_path.with_suffix(".meta.json")
    with open(sidecar_path, "r", encoding="utf-8") as handle:
        raw_meta = json.load(handle)

    case_meta = raw_meta["experimental_case"]
    bundle = load_field_bundle(str(artifact_path), sidecar_path=str(sidecar_path))
    encoder_output = field_to_signatures(
        bundle,
        low_signal_threshold_fraction=low_signal_threshold,
    )

    field_contract = _build_field_contract(
        artifact_path=artifact_path,
        bundle=bundle,
        encoder_output=encoder_output,
        raw_meta=raw_meta,
    )
    validate_field_frame(field_contract)

    summary = dict(encoder_output.summary)
    summary.update(
        {
            "experimental_label": EXPERIMENT_LABEL,
            "sandbox_status": "EXPERIMENTAL_SANDBOX",
            "provenance_class": case_meta["provenance_class"],
            "geometry_case": case_meta["geometry_case"],
            "scope_guardrail": (
                "Bridge-style summary only. This does NOT validate TopoStream semantics, "
                "fluid vortices, or 3D TPMS ranking."
            ),
        }
    )

    descriptor_summary = _build_descriptor_summary(
        bundle=bundle,
        encoder_output=encoder_output,
        case_meta=case_meta,
    )

    _write_json(output_dir / "field_contract.json", field_contract)
    with open(output_dir / "signatures.jsonl", "w", encoding="utf-8", newline="\n") as handle:
        for record in encoder_output.records:
            record_dict = record.to_dict()
            validate_signature_record(record_dict)
            handle.write(json.dumps(record_dict, sort_keys=True) + "\n")
    _write_json(output_dir / "summary.json", summary)
    _write_json(output_dir / "descriptor_summary.json", descriptor_summary)

    return {
        "case_id": case_meta["case_id"],
        "geometry_case": case_meta["geometry_case"],
        "provenance_class": case_meta["provenance_class"],
        "field_contract_path": str(output_dir / "field_contract.json"),
        "summary_path": str(output_dir / "summary.json"),
        "descriptor_summary_path": str(output_dir / "descriptor_summary.json"),
        "summary": summary,
        "descriptor_summary": descriptor_summary,
    }


def _build_field_contract(artifact_path, bundle, encoder_output, raw_meta: Dict[str, object]) -> Dict[str, object]:
    mag = encoder_output.magnitude_field
    fluid_mask = ~bundle.solid_mask.astype(bool)
    if fluid_mask.any():
        fluid_mag = mag[fluid_mask]
        magnitude_stats = {
            "mean": float(fluid_mag.mean()),
            "std": float(fluid_mag.std()),
            "min": float(fluid_mag.min()),
            "max": float(fluid_mag.max()),
        }
    else:
        magnitude_stats = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

    return {
        "schema_version": "1.0.0",
        "bridge_schema_id": "bridge_field_frame",
        "input_file": str(artifact_path),
        "input_sha256": bundle.input_sha256,
        "provenance": raw_meta,
        "field_shape": [int(bundle.shape[0]), int(bundle.shape[1])],
        "field_dtype": "float64",
        "has_scalar": bundle.scalar is not None,
        "solid_mask_fraction": float(bundle.solid_mask.mean()),
        "low_signal_fraction": float(encoder_output.summary["low_signal_fraction"]),
        "low_signal_threshold": float(encoder_output.low_signal_threshold),
        "magnitude_stats": magnitude_stats,
    }


def _build_descriptor_summary(bundle, encoder_output, case_meta: Dict[str, object]) -> Dict[str, object]:
    active_mask = (~bundle.solid_mask.astype(bool)) & (~encoder_output.low_signal_mask)
    magnitude = encoder_output.magnitude_field
    theta = encoder_output.theta_field
    u_active = bundle.u[active_mask]
    v_active = bundle.v[active_mask]
    mag_active = magnitude[active_mask]
    theta_active = theta[active_mask]

    if mag_active.size:
        mean_speed = float(mag_active.mean())
        speed_std = float(mag_active.std())
        speed_p95 = float(np.percentile(mag_active, 95))
        acceleration_ratio = float(speed_p95 / mean_speed) if mean_speed > 0.0 else 0.0
        deflection_fraction = float(np.mean(np.abs(theta_active) > 0.12))
        reverse_fraction = float(np.mean(u_active < 0.0))
        non_axiality = float(np.mean(np.abs(v_active) / np.maximum(np.abs(u_active), 1e-9)))
    else:
        mean_speed = 0.0
        speed_std = 0.0
        speed_p95 = 0.0
        acceleration_ratio = 0.0
        deflection_fraction = 0.0
        reverse_fraction = 0.0
        non_axiality = 0.0

    if np.isfinite(theta).any():
        grad_i, grad_j = np.gradient(theta)
        grad_mag = np.sqrt(grad_i**2 + grad_j**2)
        finite_grad = np.isfinite(grad_mag) & active_mask
        mean_grad = float(grad_mag[finite_grad].mean()) if finite_grad.any() else 0.0
        max_grad = float(grad_mag[finite_grad].max()) if finite_grad.any() else 0.0
    else:
        mean_grad = 0.0
        max_grad = 0.0

    complexity_index = _bounded_complexity_index(
        theta_std=float(encoder_output.summary["theta_stats"]["std_rad"]),
        mean_grad=mean_grad,
        deflection_fraction=deflection_fraction,
        acceleration_ratio=acceleration_ratio,
    )
    descriptor_tokens = _descriptor_tokens(
        case_meta=case_meta,
        complexity_index=complexity_index,
        deflection_fraction=deflection_fraction,
        acceleration_ratio=acceleration_ratio,
        theta_std=float(encoder_output.summary["theta_stats"]["std_rad"]),
        solid_fraction=float(bundle.solid_mask.mean()),
    )

    return {
        "schema_version": "1.0.0",
        "descriptor_schema_id": "experimental_2d_critic_descriptor_summary",
        "experimental_label": EXPERIMENT_LABEL,
        "sandbox_status": "EXPERIMENTAL_SANDBOX",
        "case_id": case_meta["case_id"],
        "geometry_case": case_meta["geometry_case"],
        "provenance_class": case_meta["provenance_class"],
        "format_note": (
            "Bridge-style descriptor summary only. Field records resemble the existing bridge "
            "format, but this is not a TopoStream semantic integration."
        ),
        "descriptor_stats": {
            "solid_fraction": float(bundle.solid_mask.mean()),
            "active_fraction": float(encoder_output.summary["active_fraction"]),
            "low_signal_fraction": float(encoder_output.summary["low_signal_fraction"]),
            "theta_std_rad": float(encoder_output.summary["theta_stats"]["std_rad"]),
            "theta_abs_mean_rad": float(encoder_output.summary["theta_stats"]["abs_mean_rad"]),
            "mean_speed": mean_speed,
            "speed_p95": speed_p95,
            "speed_cv": (speed_std / mean_speed) if mean_speed > 0.0 else 0.0,
            "acceleration_ratio": acceleration_ratio,
            "mean_theta_gradient": mean_grad,
            "max_theta_gradient": max_grad,
            "deflection_fraction": deflection_fraction,
            "reverse_fraction": reverse_fraction,
            "non_axiality_ratio": non_axiality,
            "bounded_complexity_index": complexity_index,
        },
        "descriptor_tokens": descriptor_tokens,
        "critic_interpretation": {
            "local_only": True,
            "note": (
                "The bounded_complexity_index is an internal sandbox ordering aid for these three "
                "cases only. It is not a performance score and not a TPMS ranking signal."
            ),
        },
    }


def _bounded_complexity_index(
    theta_std: float,
    mean_grad: float,
    deflection_fraction: float,
    acceleration_ratio: float,
) -> float:
    theta_term = min(theta_std / 0.45, 1.0)
    grad_term = min(mean_grad / 0.20, 1.0)
    deflection_term = min(deflection_fraction / 0.30, 1.0)
    speed_term = min(max(acceleration_ratio - 1.5, 0.0) / 0.35, 1.0)
    score = 0.40 * theta_term + 0.30 * grad_term + 0.20 * deflection_term + 0.10 * speed_term
    return float(np.clip(score, 0.0, 1.0))


def _descriptor_tokens(
    case_meta: Dict[str, object],
    complexity_index: float,
    deflection_fraction: float,
    acceleration_ratio: float,
    theta_std: float,
    solid_fraction: float,
) -> List[str]:
    tokens = [
        "EXPERIMENTAL_SANDBOX",
        f"GEOMETRY_{str(case_meta['geometry_case']).upper()}",
        f"PROVENANCE_{str(case_meta['provenance_class']).upper()}",
    ]

    if theta_std < 0.03:
        tokens.append("AXIAL_VARIATION_LOW")
    elif theta_std < 0.20:
        tokens.append("AXIAL_VARIATION_MEDIUM")
    else:
        tokens.append("AXIAL_VARIATION_HIGH")

    if deflection_fraction < 0.05:
        tokens.append("DEFLECTION_LOCALIZED_NONE")
    elif deflection_fraction < 0.20:
        tokens.append("DEFLECTION_LOCALIZED_MODERATE")
    else:
        tokens.append("DEFLECTION_LOCALIZED_STRONG")

    if acceleration_ratio < 1.50:
        tokens.append("ACCELERATION_BAND_LOW")
    elif acceleration_ratio < 1.65:
        tokens.append("ACCELERATION_BAND_MEDIUM")
    else:
        tokens.append("ACCELERATION_BAND_HIGH")

    if solid_fraction < 0.34:
        tokens.append("SOLID_IMPRINT_LOW")
    elif solid_fraction < 0.42:
        tokens.append("SOLID_IMPRINT_MEDIUM")
    else:
        tokens.append("SOLID_IMPRINT_HIGH")

    if complexity_index < 0.15:
        tokens.append("CRITIC_COMPLEXITY_LOW")
    elif complexity_index < 0.45:
        tokens.append("CRITIC_COMPLEXITY_MEDIUM")
    else:
        tokens.append("CRITIC_COMPLEXITY_HIGH")

    return tokens


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _format_cli_rows(result: Dict[str, object]) -> Iterable[str]:
    descriptor_stats = result["descriptor_summary"]["descriptor_stats"]
    yield (
        f"{result['case_id']}: {result['provenance_class']} | "
        f"theta_std={descriptor_stats['theta_std_rad']:.6f} | "
        f"complexity={descriptor_stats['bounded_complexity_index']:.6f}"
    )
    yield f"  tokens={result['descriptor_summary']['descriptor_tokens']}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract sandbox descriptors from one generated 2D field case."
    )
    parser.add_argument("artifact", help="Path to a generated .npz field artifact.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for bridge-style sandbox outputs.",
    )
    parser.add_argument(
        "--low-signal-threshold",
        type=float,
        default=DEFAULT_LOW_SIGNAL_THRESHOLD,
        help="Fraction of max magnitude below which pixels are marked low-signal.",
    )
    args = parser.parse_args()

    result = extract_case(
        artifact_path=Path(args.artifact),
        output_dir=Path(args.output_dir),
        low_signal_threshold=args.low_signal_threshold,
    )
    print(EXPERIMENT_LABEL)
    for row in _format_cli_rows(result):
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
