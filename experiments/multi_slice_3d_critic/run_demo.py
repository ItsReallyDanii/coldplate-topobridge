"""Run the EXPERIMENTAL_SANDBOX multi-slice/simple-3D critic demo end-to-end."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from extract_descriptors import DEFAULT_LOW_SIGNAL_THRESHOLD, extract_case
from generate_stack import (
    DEFAULT_NX,
    DEFAULT_NY,
    DEFAULT_N_SLICES,
    EXPERIMENT_LABEL,
    PerturbationConfig,
    _normalize_perturbation_config,
    generate_cases,
)


def run_demo(
    output_root: Path,
    nx: int = DEFAULT_NX,
    ny: int = DEFAULT_NY,
    n_slices: int = DEFAULT_N_SLICES,
    low_signal_threshold: float = DEFAULT_LOW_SIGNAL_THRESHOLD,
    perturbation_config: PerturbationConfig | Dict[str, object] | None = None,
) -> Dict[str, object]:
    """Generate stacks, extract descriptors, and assemble a bounded critic summary."""
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    perturbation = _normalize_perturbation_config(perturbation_config)

    generated = generate_cases(
        output_root=output_root,
        nx=nx,
        ny=ny,
        n_slices=n_slices,
        perturbation_config=perturbation,
    )
    results_root = output_root / "results"
    results_root.mkdir(exist_ok=True)

    case_results: List[Dict[str, object]] = []
    for artifact in generated:
        case_output_dir = results_root / artifact.case_id
        case_results.append(
            extract_case(
                stack_artifact=artifact,
                output_dir=case_output_dir,
                low_signal_threshold=low_signal_threshold,
            )
        )

    critic_summary = _build_critic_summary(
        case_results=case_results,
        experimental_controls={
            "grid_nx": nx,
            "grid_ny": ny,
            "n_slices": n_slices,
            "low_signal_threshold_fraction": low_signal_threshold,
            "perturbation": perturbation.to_dict(),
        },
    )
    with open(output_root / "critic_comparison.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(critic_summary, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return critic_summary


def _build_critic_summary(
    case_results: List[Dict[str, object]],
    experimental_controls: Dict[str, object],
) -> Dict[str, object]:
    ranked = sorted(
        case_results,
        key=lambda item: item["case_summary"]["stack_descriptor_stats"]["stack_complexity_index"],
    )

    case_rows = []
    for item in case_results:
        stats = item["case_summary"]["stack_descriptor_stats"]
        case_rows.append(
            {
                "case_id": item["case_id"],
                "geometry_case": item["geometry_case"],
                "provenance_class": item["provenance_class"],
                "slice_count": item["case_summary"]["slice_count"],
                "stack_complexity_index": stats["stack_complexity_index"],
                "slice_complexity_mean": stats["slice_complexity_mean"],
                "slice_complexity_span": stats["slice_complexity_span"],
                "slice_theta_std_mean": stats["slice_theta_std_mean"],
                "slice_deflection_mean": stats["slice_deflection_mean"],
                "slice_stability_fraction": stats["slice_stability_fraction"],
                "descriptor_tokens": item["case_summary"]["descriptor_tokens"],
            }
        )

    low = ranked[0]
    mid = ranked[1]
    high = ranked[-1]
    low_score = low["case_summary"]["stack_descriptor_stats"]["stack_complexity_index"]
    mid_score = mid["case_summary"]["stack_descriptor_stats"]["stack_complexity_index"]
    high_score = high["case_summary"]["stack_descriptor_stats"]["stack_complexity_index"]

    return {
        "schema_version": "1.0.0",
        "summary_schema_id": "experimental_multi_slice_3d_critic_comparison",
        "experimental_label": EXPERIMENT_LABEL,
        "sandbox_status": "EXPERIMENTAL_SANDBOX",
        "format_note": (
            "This is a bounded comparison across deterministic slice stacks. "
            "It is a simple 3D proxy only, not a real-candidate ranking method."
        ),
        "experimental_controls": experimental_controls,
        "what_this_is": (
            "A stack of 2D slices with controlled variation, encoded slice-by-slice "
            "with the existing bridge-local path and aggregated with sandbox-only metrics."
        ),
        "case_summaries": case_rows,
        "bounded_critic_summary": {
            "ordering_rule": "ascending stack_complexity_index",
            "ordering_low_to_high": [item["case_id"] for item in ranked],
            "observations": [
                _case_observation(low, role="lowest"),
                _case_observation(mid, role="middle"),
                _case_observation(high, role="highest"),
            ],
            "recommendation": (
                "continue"
                if (mid_score - low_score) > 0.08 and (high_score - mid_score) > 0.08
                else "stop"
            ),
            "recommendation_note": (
                "Continue means only that descriptor separation remains stable enough "
                "in this bounded multi-slice proxy to justify a later experiment. "
                "It does not validate physical realism, 3D TPMS ranking, or TopoStream semantics."
            ),
        },
        "not_proven": [
            "Any physical realism for the synthetic slices or the stacked proxy",
            "Any mapping from descriptor separation to hydraulic, thermal, or structural performance",
            "Any equivalence between these descriptors and fluid vortices",
            "Any TopoStream semantic compatibility",
            "Any validated ranking of 3D TPMS coldplate candidates",
            "Any physics validation",
        ],
    }


def _render_cli_summary(critic_summary: Dict[str, object]) -> List[str]:
    rows = [EXPERIMENT_LABEL]
    for item in critic_summary["case_summaries"]:
        rows.append(
            (
                f"{item['case_id']}: {item['provenance_class']} | "
                f"stack_complexity={item['stack_complexity_index']:.6f} | "
                f"slice_mean={item['slice_complexity_mean']:.6f} | "
                f"slice_span={item['slice_complexity_span']:.6f}"
            )
        )
    rows.append(
        "ordering_low_to_high="
        + ",".join(critic_summary["bounded_critic_summary"]["ordering_low_to_high"])
    )
    rows.append(
        "recommendation=" + critic_summary["bounded_critic_summary"]["recommendation"]
    )
    return rows


def _case_observation(item: Dict[str, object], role: str) -> str:
    case_id = item["case_id"]
    if case_id == "straight_stack":
        detail = "an identical per-slice analytic baseline with near-zero directional spread"
    elif case_id == "obstruction_stack":
        detail = "localized turning that persists across slices as the obstruction shifts"
    elif case_id == "constriction_stack":
        detail = "broader slice-wide turning from the breathing constriction stack"
    else:
        detail = "descriptor behavior specific to this sandbox geometry"

    return f"{case_id} is the {role}-complexity case: {detail}."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the EXPERIMENTAL_SANDBOX multi-slice/simple-3D critic demo."
    )
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parent / "out"),
        help="Root directory for sandbox outputs.",
    )
    parser.add_argument("--nx", type=int, default=DEFAULT_NX, help="Grid columns.")
    parser.add_argument("--ny", type=int, default=DEFAULT_NY, help="Grid rows.")
    parser.add_argument(
        "--n-slices",
        type=int,
        default=DEFAULT_N_SLICES,
        help="Number of deterministic slices in each stack.",
    )
    parser.add_argument(
        "--low-signal-threshold",
        type=float,
        default=DEFAULT_LOW_SIGNAL_THRESHOLD,
        help="Fraction of max magnitude below which pixels are marked low-signal.",
    )
    args = parser.parse_args()

    critic_summary = run_demo(
        output_root=Path(args.output_root),
        nx=args.nx,
        ny=args.ny,
        n_slices=args.n_slices,
        low_signal_threshold=args.low_signal_threshold,
    )
    for row in _render_cli_summary(critic_summary):
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
