"""CLI entrypoint for coldplate-topobridge.

Usage:
    python -m topobridge.cli run <artifact.npz> --output <dir> [options]
    python -m topobridge.cli validate <output_dir_or_manifest.json>
    python -m topobridge.cli stage4 <velocity_field.npz> <provenance.json> --output <dir> [options]

IMPLEMENTED: run + validate + stage4 subcommands.
NOT_PROVEN: any physical interpretation of outputs.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from topobridge.adapters.coldplate_field_loader import load_field_bundle
from topobridge.adapters.stage4_velocity_adapter import load_stage4_field_bundle, Stage4SliceConfig
from topobridge.encode.field_to_signature import field_to_signatures
from topobridge.io.schema_validate import validate_bundle_dir
from topobridge.io.provenance import build_run_provenance, build_manifest


def cmd_run(args) -> int:
    """Execute the bridge pipeline on a single field artifact.

    Returns 0 on success, 1 on error.
    """
    artifact_path = Path(args.artifact).resolve()
    output_dir = Path(args.output).resolve()
    sidecar_path = Path(args.sidecar).resolve() if args.sidecar else None
    threshold = args.low_signal_threshold

    print(f"[bridge:run] Input: {artifact_path}")
    print(f"[bridge:run] Output: {output_dir}")

    # Step 1: Load field bundle
    try:
        bundle = load_field_bundle(
            str(artifact_path),
            sidecar_path=str(sidecar_path) if sidecar_path else None,
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"ESCALATE: Field loading failed: {e}", file=sys.stderr)
        return 1

    print(f"[bridge:run] Loaded field: shape={bundle.shape}, sha256={bundle.input_sha256[:12]}...")

    # Step 2: Encode to signature stream
    try:
        encoder_output = field_to_signatures(bundle, low_signal_threshold_fraction=threshold)
    except Exception as e:
        print(f"ESCALATE: Encoding failed: {e}", file=sys.stderr)
        return 1

    summary = encoder_output.summary
    print(
        f"[bridge:run] Encoded: "
        f"n_active={summary['n_active_pixels']}, "
        f"n_solid={summary['n_solid_pixels']}, "
        f"n_low_signal={summary['n_low_signal_pixels']}, "
        f"theta_std={summary['theta_stats']['std_rad']:.4f}"
    )

    # Step 3: Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- field_contract.json ---
    ny, nx = bundle.shape
    mag = encoder_output.magnitude_field
    fluid_mask = ~bundle.solid_mask.astype(bool)
    if fluid_mask.any():
        fluid_mags = mag[fluid_mask]
        mag_stats = {
            "mean": float(fluid_mags.mean()),
            "std": float(fluid_mags.std()),
            "min": float(fluid_mags.min()),
            "max": float(fluid_mags.max()),
        }
    else:
        mag_stats = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

    field_contract = {
        "schema_version": "1.0.0",
        "bridge_schema_id": "bridge_field_frame",
        "input_file": str(artifact_path),
        "input_sha256": bundle.input_sha256,
        "provenance": bundle.provenance.to_dict(),
        "field_shape": [ny, nx],
        "field_dtype": "float64",
        "has_scalar": bundle.scalar is not None,
        "solid_mask_fraction": float(bundle.solid_mask.mean()),
        "low_signal_fraction": summary["low_signal_fraction"],
        "low_signal_threshold": encoder_output.low_signal_threshold,
        "magnitude_stats": mag_stats,
    }

    with open(output_dir / "field_contract.json", "w", encoding="utf-8") as f:
        json.dump(field_contract, f, indent=2, sort_keys=True)

    # --- signatures.jsonl ---
    with open(output_dir / "signatures.jsonl", "w", encoding="utf-8") as f:
        for rec in encoder_output.records:
            f.write(json.dumps(rec.to_dict(), sort_keys=True) + "\n")

    # --- summary.json ---
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(encoder_output.summary, f, indent=2, sort_keys=True)

    # --- manifest.json ---
    run_prov = build_run_provenance(
        input_sha256=bundle.input_sha256,
        source_repo=bundle.provenance.source_repo,
        source_stage=bundle.provenance.source_stage,
        source_artifact=bundle.provenance.source_artifact,
        source_commit=bundle.provenance.source_commit,
        preprocessing=bundle.provenance.preprocessing,
        grid_shape=bundle.shape,
        low_signal_threshold=encoder_output.low_signal_threshold,
    )
    manifest = build_manifest(output_dir, bundle.input_sha256, run_prov)
    with open(output_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    print(f"[bridge:run] Artifact bundle written to: {output_dir}")
    print(f"[bridge:run] Run SHA256: {manifest['bridge_run_sha256'][:12]}...")
    print(f"[bridge:run] Files: {list(manifest['files'].keys())}")
    return 0


def cmd_validate(args) -> int:
    """Validate a bridge artifact bundle directory.

    Returns 0 if valid, 1 if validation fails.
    """
    target = Path(args.target).resolve()

    # Accept either a directory or manifest.json
    if target.is_file() and target.name == "manifest.json":
        output_dir = target.parent
    elif target.is_dir():
        output_dir = target
    else:
        print(f"Error: {target} is not a directory or manifest.json", file=sys.stderr)
        return 1

    print(f"[bridge:validate] Validating: {output_dir}")

    results = validate_bundle_dir(output_dir)

    if results["valid"]:
        print("[bridge:validate] PASS — all checks passed")
        for fname in results["files_checked"]:
            print(f"  ✓ {fname}")
        return 0
    else:
        print("[bridge:validate] FAIL — validation errors:", file=sys.stderr)
        for err in results["errors"]:
            print(f"  ✗ {err}", file=sys.stderr)
        return 1



def cmd_stage4(args) -> int:
    """Run bridge pipeline on a Stage 4 coldplate-design-engine velocity artifact.

    Slices a 3D velocity_field.npz to a 2D cross-section, detects solid region
    via velocity threshold, encodes to bridge-local signature stream.

    IMPLEMENTED: reads velocity_field.npz + provenance.json, slices, encodes.
    NOT_PROVEN: any physical interpretation of bridge signatures.
    NOT_PROVEN: solid detection accuracy from velocity threshold.
    Returns 0 on success, 1 on error.
    """
    vel_path = Path(args.velocity_field).resolve()
    prov_path = Path(args.provenance).resolve()
    output_dir = Path(args.output).resolve()

    print(f"[bridge:stage4] Input: {vel_path}")
    print(f"[bridge:stage4] Provenance: {prov_path}")
    print(f"[bridge:stage4] Slice: axis={args.slice_axis}, index={args.slice_index}")
    print(f"[bridge:stage4] Output: {output_dir}")

    # Step 1: Load via stage4 adapter
    try:
        config = Stage4SliceConfig(
            velocity_field_path=str(vel_path),
            provenance_path=str(prov_path),
            slice_axis=args.slice_axis,
            slice_index=args.slice_index,
            solid_threshold_fraction=args.solid_threshold,
            include_axial_as_scalar=args.include_axial_scalar,
        )
        bundle = load_stage4_field_bundle(config)
    except (FileNotFoundError, ValueError) as e:
        print(f"ESCALATE: Stage4 loading failed: {e}", file=sys.stderr)
        return 1

    print(
        f"[bridge:stage4] Loaded: shape={bundle.shape}, "
        f"sha256={bundle.input_sha256[:12]}..., "
        f"solid_fraction={bundle.solid_mask.mean():.3f}"
    )

    # Step 2: Encode
    try:
        encoder_output = field_to_signatures(bundle, low_signal_threshold_fraction=args.low_signal_threshold)
    except Exception as e:
        print(f"ESCALATE: Encoding failed: {e}", file=sys.stderr)
        return 1

    summary = encoder_output.summary
    print(
        f"[bridge:stage4] Encoded: "
        f"n_active={summary['n_active_pixels']}, "
        f"n_solid={summary['n_solid_pixels']}, "
        f"n_low_signal={summary['n_low_signal_pixels']}, "
        f"theta_std={summary['theta_stats']['std_rad']:.4f}"
    )

    # Step 3: Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)

    ny, nx = bundle.shape
    mag = encoder_output.magnitude_field
    fluid_mask_arr = ~bundle.solid_mask.astype(bool)
    if fluid_mask_arr.any():
        fluid_mags = mag[fluid_mask_arr]
        mag_stats = {
            "mean": float(fluid_mags.mean()),
            "std": float(fluid_mags.std()),
            "min": float(fluid_mags.min()),
            "max": float(fluid_mags.max()),
        }
    else:
        mag_stats = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

    field_contract = {
        "schema_version": "1.0.0",
        "bridge_schema_id": "bridge_field_frame",
        "input_file": str(vel_path),
        "input_sha256": bundle.input_sha256,
        "provenance": bundle.provenance.to_dict(),
        "field_shape": [ny, nx],
        "field_dtype": "float64",
        "has_scalar": bundle.scalar is not None,
        "solid_mask_fraction": float(bundle.solid_mask.mean()),
        "low_signal_fraction": summary["low_signal_fraction"],
        "low_signal_threshold": encoder_output.low_signal_threshold,
        "magnitude_stats": mag_stats,
    }

    with open(output_dir / "field_contract.json", "w", encoding="utf-8") as f:
        json.dump(field_contract, f, indent=2, sort_keys=True)

    with open(output_dir / "signatures.jsonl", "w", encoding="utf-8") as f:
        for rec in encoder_output.records:
            f.write(json.dumps(rec.to_dict(), sort_keys=True) + "\n")

    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(encoder_output.summary, f, indent=2, sort_keys=True)

    run_prov = build_run_provenance(
        input_sha256=bundle.input_sha256,
        source_repo=bundle.provenance.source_repo,
        source_stage=bundle.provenance.source_stage,
        source_artifact=bundle.provenance.source_artifact,
        source_commit=bundle.provenance.source_commit,
        preprocessing=bundle.provenance.preprocessing,
        grid_shape=bundle.shape,
        low_signal_threshold=encoder_output.low_signal_threshold,
    )
    manifest = build_manifest(output_dir, bundle.input_sha256, run_prov)
    with open(output_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    print(f"[bridge:stage4] Artifact bundle written to: {output_dir}")
    print(f"[bridge:stage4] Run SHA256: {manifest['bridge_run_sha256'][:12]}...")
    print(f"[bridge:stage4] Files: {list(manifest['files'].keys())}")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="topobridge",
        description=(
            "coldplate-topobridge Stage 1 CLI — read-only bridge layer.\n"
            "Reads frozen 2D field artifacts, validates provenance, "
            "encodes to bridge-local signature stream, emits artifact bundle.\n\n"
            "CLAIM TIER: IMPLEMENTED. See CLAIM_TIERS.md for constraints."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run subcommand
    run_p = sub.add_parser("run", help="Run bridge pipeline on a field artifact")
    run_p.add_argument("artifact", help="Path to .npz field artifact")
    run_p.add_argument(
        "--output", "-o", required=True,
        help="Output directory for artifact bundle"
    )
    run_p.add_argument(
        "--sidecar", default=None,
        help="Path to .meta.json provenance sidecar (default: auto-detected)"
    )
    run_p.add_argument(
        "--low-signal-threshold", type=float, default=0.01,
        dest="low_signal_threshold",
        help="Fraction of max magnitude below which pixels are flagged low-signal (default: 0.01)"
    )

    # validate subcommand
    val_p = sub.add_parser("validate", help="Validate a bridge artifact bundle")
    val_p.add_argument("target", help="Path to output directory or manifest.json")

    # stage4 subcommand
    s4_p = sub.add_parser(
        "stage4",
        help="Ingest a Stage 4 coldplate velocity artifact (read-only)",
        description=(
            "Read a Stage 4 velocity_field.npz + provenance.json from "
            "coldplate-design-engine (read-only). Slice to 2D cross-section, "
            "detect solid from velocity threshold, run bridge pipeline.\n\n"
            "CLAIM TIER: IMPLEMENTED. NOT_PROVEN: physical interpretation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    s4_p.add_argument("velocity_field", help="Path to velocity_field.npz")
    s4_p.add_argument("provenance", help="Path to provenance.json sidecar")
    s4_p.add_argument("--output", "-o", required=True, help="Output directory")
    s4_p.add_argument(
        "--slice-axis", default="z", choices=["x", "y", "z"],
        dest="slice_axis",
        help="Axis to slice: 'z'=cross-section ⊥ flow (default), 'x'/'y'=other planes"
    )
    s4_p.add_argument(
        "--slice-index", type=int, default=None,
        dest="slice_index",
        help="Index along slice axis (default: midpoint)"
    )
    s4_p.add_argument(
        "--solid-threshold", type=float, default=1e-3,
        dest="solid_threshold",
        help="Fraction of max velocity magnitude below which pixels are flagged solid (default: 1e-3)"
    )
    s4_p.add_argument(
        "--include-axial-scalar", action="store_true", default=True,
        dest="include_axial_scalar",
        help="Include axial velocity (vz when slicing z) as optional scalar field"
    )
    s4_p.add_argument(
        "--low-signal-threshold", type=float, default=0.01,
        dest="low_signal_threshold",
        help="Bridge low-signal threshold (fraction of max magnitude, default: 0.01)"
    )

    return parser


def main():
    parser = make_parser()
    args = parser.parse_args()

    if args.command == "run":
        sys.exit(cmd_run(args))
    elif args.command == "validate":
        sys.exit(cmd_validate(args))
    elif args.command == "stage4":
        sys.exit(cmd_stage4(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
