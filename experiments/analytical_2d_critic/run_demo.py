"""Run the EXPERIMENTAL_SANDBOX analytical 2D critic demo end-to-end."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from generate_fields import DEFAULT_NX, DEFAULT_NY, EXPERIMENT_LABEL, generate_cases
from extract_descriptors import DEFAULT_LOW_SIGNAL_THRESHOLD, extract_case


def run_demo(
    output_root: Path,
    nx: int = DEFAULT_NX,
    ny: int = DEFAULT_NY,
    low_signal_threshold: float = DEFAULT_LOW_SIGNAL_THRESHOLD,
) -> Dict[str, object]:
    """Generate fields, extract descriptors, and assemble a tiny critic summary."""
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    generated = generate_cases(output_root=output_root, nx=nx, ny=ny)
    results_root = output_root / "results"
    results_root.mkdir(exist_ok=True)

    case_results: List[Dict[str, object]] = []
    for artifact in generated:
        case_output_dir = results_root / artifact.case_id
        case_results.append(
            extract_case(
                artifact_path=artifact.npz_path,
                output_dir=case_output_dir,
                low_signal_threshold=low_signal_threshold,
            )
        )

    critic_summary = _build_critic_summary(case_results=case_results)
    with open(output_root / "critic_comparison.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(critic_summary, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return critic_summary


def _build_critic_summary(case_results: List[Dict[str, object]]) -> Dict[str, object]:
    ranked = sorted(
        case_results,
        key=lambda item: item["descriptor_summary"]["descriptor_stats"]["bounded_complexity_index"],
    )

    case_rows = []
    for item in case_results:
        stats = item["descriptor_summary"]["descriptor_stats"]
        case_rows.append(
            {
                "case_id": item["case_id"],
                "geometry_case": item["geometry_case"],
                "provenance_class": item["provenance_class"],
                "bounded_complexity_index": stats["bounded_complexity_index"],
                "theta_std_rad": stats["theta_std_rad"],
                "deflection_fraction": stats["deflection_fraction"],
                "acceleration_ratio": stats["acceleration_ratio"],
                "descriptor_tokens": item["descriptor_summary"]["descriptor_tokens"],
            }
        )

    best = ranked[0]
    mid = ranked[1]
    high = ranked[-1]

    return {
        "schema_version": "1.0.0",
        "summary_schema_id": "experimental_2d_critic_comparison",
        "experimental_label": EXPERIMENT_LABEL,
        "sandbox_status": "EXPERIMENTAL_SANDBOX",
        "format_note": (
            "This is a bounded comparison across three simple 2D sandbox cases. "
            "It is not a real-candidate ranking method."
        ),
        "case_summaries": case_rows,
        "bounded_critic_summary": {
            "ordering_rule": "ascending bounded_complexity_index",
            "ordering_low_to_high": [item["case_id"] for item in ranked],
            "observations": [
                _case_observation(best, role="lowest"),
                _case_observation(mid, role="middle"),
                _case_observation(high, role="highest"),
            ],
            "recommendation": (
                "continue"
                if (high["descriptor_summary"]["descriptor_stats"]["bounded_complexity_index"]
                    - best["descriptor_summary"]["descriptor_stats"]["bounded_complexity_index"]) > 0.25
                else "stop"
            ),
            "recommendation_note": (
                "Continue means only that the descriptor pipeline appears stable enough to justify "
                "a later multi-slice or 3D critic study. It does not validate physical ranking."
            ),
        },
        "not_proven": [
            "Any mapping from descriptor complexity to hydraulic performance",
            "Any equivalence between these descriptors and fluid vortices",
            "Any ranking validity for 3D TPMS coldplate candidates",
            "Any TopoStream semantic compatibility beyond superficial format resemblance",
        ],
    }


def _render_cli_summary(critic_summary: Dict[str, object]) -> List[str]:
    rows = [EXPERIMENT_LABEL]
    for item in critic_summary["case_summaries"]:
        rows.append(
            (
                f"{item['case_id']}: {item['provenance_class']} | "
                f"theta_std={item['theta_std_rad']:.6f} | "
                f"deflection={item['deflection_fraction']:.6f} | "
                f"complexity={item['bounded_complexity_index']:.6f}"
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
    if case_id == "straight_channel":
        detail = "mostly axial flow with near-zero directional spread"
    elif case_id == "single_obstruction":
        detail = "localized turning around the internal blockage"
    elif case_id == "constricted_channel":
        detail = "smooth throat-driven acceleration with broader directional change"
    else:
        detail = "descriptor behavior specific to this sandbox geometry"

    return f"{case_id} is the {role}-complexity case: {detail}."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the EXPERIMENTAL_SANDBOX analytical 2D critic demo."
    )
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parent / "out"),
        help="Root directory for sandbox outputs.",
    )
    parser.add_argument("--nx", type=int, default=DEFAULT_NX, help="Grid columns.")
    parser.add_argument("--ny", type=int, default=DEFAULT_NY, help="Grid rows.")
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
        low_signal_threshold=args.low_signal_threshold,
    )
    for row in _render_cli_summary(critic_summary):
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
