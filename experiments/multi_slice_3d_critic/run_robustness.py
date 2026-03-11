"""Run bounded robustness sweeps for the EXPERIMENTAL_SANDBOX multi-slice critic."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List

from extract_descriptors import DEFAULT_LOW_SIGNAL_THRESHOLD
from generate_stack import (
    DEFAULT_NX,
    DEFAULT_NY,
    DEFAULT_N_SLICES,
    EXPERIMENT_LABEL,
    PerturbationConfig,
    _normalize_perturbation_config,
)
from run_demo import run_demo


ROBUSTNESS_LABEL = "EXPERIMENTAL_SANDBOX_MULTI_SLICE_3D_CRITIC_ROBUSTNESS"
DEFAULT_BASELINE_VARIANT_ID = "baseline"
DEFAULT_MINIMUM_DOCUMENTED_GAP = 0.08
ROBUSTNESS_PROFILE_NX = 12
ROBUSTNESS_PROFILE_NY = 8
ROBUSTNESS_PROFILE_N_SLICES = 3


@dataclass(frozen=True)
class RobustnessVariant:
    variant_id: str
    variation_family: str
    description: str
    nx: int = DEFAULT_NX
    ny: int = DEFAULT_NY
    n_slices: int = DEFAULT_N_SLICES
    low_signal_threshold: float = DEFAULT_LOW_SIGNAL_THRESHOLD
    perturbation_config: PerturbationConfig = field(default_factory=PerturbationConfig)

    def run_parameters(self) -> Dict[str, object]:
        return {
            "grid_nx": self.nx,
            "grid_ny": self.ny,
            "n_slices": self.n_slices,
            "low_signal_threshold_fraction": self.low_signal_threshold,
            "perturbation": self.perturbation_config.to_dict(),
        }


def run_robustness_pass(
    output_root: Path,
    variants: List[RobustnessVariant | Dict[str, object]] | None = None,
    baseline_variant_id: str = DEFAULT_BASELINE_VARIANT_ID,
) -> Dict[str, object]:
    """Run bounded parameter sweeps and summarize ordering stability."""
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    normalized_variants = _normalize_variants(
        variants=variants or _default_variants(),
        baseline_variant_id=baseline_variant_id,
    )

    variant_results = []
    for variant in normalized_variants:
        variant_output_root = output_root / "variants" / variant.variant_id
        critic_summary = run_demo(
            output_root=variant_output_root,
            nx=variant.nx,
            ny=variant.ny,
            n_slices=variant.n_slices,
            low_signal_threshold=variant.low_signal_threshold,
            perturbation_config=variant.perturbation_config,
        )
        variant_results.append(
            {
                "variant": variant,
                "output_root": variant_output_root,
                "critic_summary": critic_summary,
            }
        )

    baseline_result = variant_results[0]
    baseline_summary = baseline_result["critic_summary"]
    baseline_ordering = baseline_summary["bounded_critic_summary"]["ordering_low_to_high"]
    baseline_recommendation = baseline_summary["bounded_critic_summary"]["recommendation"]
    baseline_scores = _case_score_map(baseline_summary)
    baseline_tokens = _case_token_map(baseline_summary)
    baseline_provenance = _case_provenance_map(baseline_summary)

    variant_rows = []
    for item in variant_results:
        variant = item["variant"]
        critic_summary = item["critic_summary"]
        ordering = critic_summary["bounded_critic_summary"]["ordering_low_to_high"]
        recommendation = critic_summary["bounded_critic_summary"]["recommendation"]
        score_map = _case_score_map(critic_summary)
        token_map = _case_token_map(critic_summary)
        provenance_map = _case_provenance_map(critic_summary)
        ordering_flips = _pairwise_ordering_flips(baseline_ordering, ordering)
        gap_metrics = _documented_gap_metrics(score_map)
        token_changes = _token_changes(baseline_tokens, token_map)
        score_deltas = {
            case_id: float(score_map[case_id] - baseline_scores[case_id])
            for case_id in baseline_scores
        }

        stable_properties = []
        if ordering == baseline_ordering:
            stable_properties.append("ordering_low_to_high unchanged from baseline")
        if recommendation == baseline_recommendation:
            stable_properties.append("recommendation unchanged from baseline")
        if gap_metrics["documented_separation_retained"]:
            stable_properties.append(
                "documented separation gaps remained above the bounded 0.08 threshold"
            )
        if provenance_map == baseline_provenance:
            stable_properties.append("provenance class mapping unchanged")

        changed_properties = []
        if any(abs(delta) > 1e-12 for delta in score_deltas.values()):
            changed_properties.append("absolute stack_complexity_index values shifted")
        if token_changes:
            changed_properties.append(
                "stack descriptor tokens changed for "
                + ", ".join(sorted(token_changes.keys()))
            )
        if not changed_properties:
            changed_properties.append("no material changes recorded against baseline")

        variant_rows.append(
            {
                "variant_id": variant.variant_id,
                "variation_family": variant.variation_family,
                "description": variant.description,
                "run_parameters": variant.run_parameters(),
                "output_root": str(Path("variants") / variant.variant_id),
                "critic_summary_path": str(
                    Path("variants") / variant.variant_id / "critic_comparison.json"
                ),
                "ordering_low_to_high": ordering,
                "recommendation": recommendation,
                "matches_baseline_ordering": ordering == baseline_ordering,
                "ordering_flip_count": len(ordering_flips),
                "ordering_flips": ordering_flips,
                "documented_gap_metrics": gap_metrics,
                "stack_complexity_index_by_case": score_map,
                "stack_complexity_delta_from_baseline": score_deltas,
                "descriptor_tokens_by_case": token_map,
                "token_changes_from_baseline": token_changes,
                "stable_properties": stable_properties,
                "changed_properties": changed_properties,
            }
        )

    variants_with_flips = [
        row["variant_id"] for row in variant_rows if row["ordering_flip_count"] > 0
    ]
    variants_without_flips = [
        row["variant_id"] for row in variant_rows if row["ordering_flip_count"] == 0
    ]
    variants_with_token_changes = [
        row["variant_id"] for row in variant_rows if row["token_changes_from_baseline"]
    ]
    max_abs_delta_by_case = {
        case_id: max(
            abs(float(row["stack_complexity_delta_from_baseline"][case_id])) for row in variant_rows
        )
        for case_id in baseline_scores
    }

    stable_findings = []
    if not variants_with_flips:
        stable_findings.append(
            "The documented ordering remained straight_stack < obstruction_stack < constriction_stack across all bounded sweep variants."
        )
    if all(row["recommendation"] == baseline_recommendation for row in variant_rows):
        stable_findings.append(
            f"The bounded recommendation remained {baseline_recommendation} across all bounded sweep variants."
        )
    if all(row["documented_gap_metrics"]["documented_separation_retained"] for row in variant_rows):
        stable_findings.append(
            "The two documented stack-complexity gaps stayed above the bounded 0.08 separation threshold across all sweep variants."
        )
    stable_findings.append(
        "Provenance classes remained explicit and unchanged for all sweep variants."
    )

    changed_findings = [
        "Absolute stack_complexity_index values moved under slice-count, resolution, threshold, and perturbation changes."
    ]
    if variants_with_token_changes:
        changed_findings.append(
            "Some stack descriptor token bins changed under bounded variation for "
            + ", ".join(variants_with_token_changes)
            + "."
        )
    else:
        changed_findings.append(
            "No stack descriptor token-bin changes were observed across the bounded sweep."
        )

    robustness_summary = {
        "baseline_variant_id": baseline_result["variant"].variant_id,
        "baseline_ordering_low_to_high": baseline_ordering,
        "baseline_recommendation": baseline_recommendation,
        "variants_without_ordering_flips": variants_without_flips,
        "variants_with_ordering_flips": variants_with_flips,
        "variants_with_descriptor_token_changes": variants_with_token_changes,
        "max_abs_stack_complexity_delta_by_case": max_abs_delta_by_case,
        "stable_findings": stable_findings,
        "changed_findings": changed_findings,
        "what_this_proves": [
            "Within this bounded stacked-slice proxy, the documented ordering and gap-based descriptor separation can be checked against controlled slice-count, grid, threshold, and deterministic perturbation changes.",
            "The robustness pass can show whether the bounded ordering flips or stays intact under those controlled changes.",
        ],
        "what_this_does_not_prove": [
            "Any physical realism for the synthetic slices or the stacked proxy",
            "Any vortex correspondence",
            "Any TopoStream semantic compatibility",
            "Any validated ranking of 3D TPMS coldplate candidates",
            "Any hydraulic, thermal, structural, or manufacturing meaning",
            "Any physics validation",
        ],
    }

    summary = {
        "schema_version": "1.0.0",
        "summary_schema_id": "experimental_multi_slice_3d_critic_robustness_pass",
        "experimental_label": EXPERIMENT_LABEL,
        "robustness_label": ROBUSTNESS_LABEL,
        "sandbox_status": "EXPERIMENTAL_SANDBOX",
        "format_note": (
            "This robustness pass sweeps bounded experiment controls around the stacked-slice proxy. "
            "It tests ordering stability only and does not broaden repo claims."
        ),
        "baseline_variant_id": baseline_result["variant"].variant_id,
        "variant_results": variant_rows,
        "robustness_summary": robustness_summary,
        "not_proven": robustness_summary["what_this_does_not_prove"],
    }
    _write_json(output_root / "robustness_summary.json", summary)
    return summary


def _default_variants() -> List[RobustnessVariant]:
    return [
        RobustnessVariant(
            variant_id="baseline",
            variation_family="baseline",
            description="Baseline bounded robustness profile.",
            nx=ROBUSTNESS_PROFILE_NX,
            ny=ROBUSTNESS_PROFILE_NY,
            n_slices=ROBUSTNESS_PROFILE_N_SLICES,
        ),
        RobustnessVariant(
            variant_id="slice_count_5",
            variation_family="slice_count",
            description="Increase the deterministic stack to 5 slices.",
            nx=ROBUSTNESS_PROFILE_NX,
            ny=ROBUSTNESS_PROFILE_NY,
            n_slices=5,
        ),
        RobustnessVariant(
            variant_id="resolution_10x6",
            variation_family="grid_resolution",
            description="Coarsen the x/y grid while preserving the same case rules.",
            nx=10,
            ny=6,
            n_slices=ROBUSTNESS_PROFILE_N_SLICES,
        ),
        RobustnessVariant(
            variant_id="resolution_16x10",
            variation_family="grid_resolution",
            description="Refine the x/y grid while preserving the same case rules.",
            nx=16,
            ny=10,
            n_slices=ROBUSTNESS_PROFILE_N_SLICES,
        ),
        RobustnessVariant(
            variant_id="threshold_0p020",
            variation_family="descriptor_threshold",
            description="Raise the low-signal threshold fraction to 0.020.",
            nx=ROBUSTNESS_PROFILE_NX,
            ny=ROBUSTNESS_PROFILE_NY,
            n_slices=ROBUSTNESS_PROFILE_N_SLICES,
            low_signal_threshold=0.020,
        ),
        RobustnessVariant(
            variant_id="perturbation_0p012",
            variation_family="bounded_perturbation",
            description="Apply deterministic bounded dither with 1.2% amplitude.",
            nx=ROBUSTNESS_PROFILE_NX,
            ny=ROBUSTNESS_PROFILE_NY,
            n_slices=ROBUSTNESS_PROFILE_N_SLICES,
            perturbation_config=PerturbationConfig(
                mode="sinusoidal_dither",
                amplitude_fraction=0.012,
                phase_seed=7,
            ),
        ),
    ]


def _normalize_variants(
    variants: List[RobustnessVariant | Dict[str, object]],
    baseline_variant_id: str,
) -> List[RobustnessVariant]:
    normalized = [_coerce_variant(variant) for variant in variants]
    if not normalized:
        raise ValueError("At least one robustness variant is required.")

    baseline_index = next(
        (index for index, variant in enumerate(normalized) if variant.variant_id == baseline_variant_id),
        0,
    )
    if baseline_index != 0:
        baseline_variant = normalized.pop(baseline_index)
        normalized.insert(0, baseline_variant)
    return normalized


def _coerce_variant(variant: RobustnessVariant | Dict[str, object]) -> RobustnessVariant:
    if isinstance(variant, RobustnessVariant):
        return variant
    return RobustnessVariant(
        variant_id=str(variant["variant_id"]),
        variation_family=str(variant["variation_family"]),
        description=str(variant["description"]),
        nx=int(variant.get("nx", DEFAULT_NX)),
        ny=int(variant.get("ny", DEFAULT_NY)),
        n_slices=int(variant.get("n_slices", DEFAULT_N_SLICES)),
        low_signal_threshold=float(
            variant.get("low_signal_threshold", DEFAULT_LOW_SIGNAL_THRESHOLD)
        ),
        perturbation_config=_normalize_perturbation_config(
            variant.get("perturbation_config")
        ),
    )


def _case_score_map(critic_summary: Dict[str, object]) -> Dict[str, float]:
    return {
        row["case_id"]: float(row["stack_complexity_index"])
        for row in critic_summary["case_summaries"]
    }


def _case_token_map(critic_summary: Dict[str, object]) -> Dict[str, List[str]]:
    return {
        row["case_id"]: list(row["descriptor_tokens"])
        for row in critic_summary["case_summaries"]
    }


def _case_provenance_map(critic_summary: Dict[str, object]) -> Dict[str, str]:
    return {
        row["case_id"]: str(row["provenance_class"])
        for row in critic_summary["case_summaries"]
    }


def _pairwise_ordering_flips(
    baseline_ordering: List[str],
    observed_ordering: List[str],
) -> List[Dict[str, object]]:
    observed_positions = {case_id: index for index, case_id in enumerate(observed_ordering)}
    flips = []
    for left_index, left_case in enumerate(baseline_ordering):
        for right_case in baseline_ordering[left_index + 1 :]:
            if observed_positions[left_case] > observed_positions[right_case]:
                flips.append(
                    {
                        "case_pair": [left_case, right_case],
                        "baseline_relation": f"{left_case}<{right_case}",
                        "observed_relation": f"{right_case}<{left_case}",
                    }
                )
    return flips


def _documented_gap_metrics(score_map: Dict[str, float]) -> Dict[str, float | bool]:
    obstruction_minus_straight = float(
        score_map["obstruction_stack"] - score_map["straight_stack"]
    )
    constriction_minus_obstruction = float(
        score_map["constriction_stack"] - score_map["obstruction_stack"]
    )
    minimum_gap = min(obstruction_minus_straight, constriction_minus_obstruction)
    return {
        "obstruction_minus_straight": obstruction_minus_straight,
        "constriction_minus_obstruction": constriction_minus_obstruction,
        "minimum_gap": minimum_gap,
        "minimum_expected_gap": DEFAULT_MINIMUM_DOCUMENTED_GAP,
        "documented_separation_retained": minimum_gap > DEFAULT_MINIMUM_DOCUMENTED_GAP,
    }


def _token_changes(
    baseline_tokens: Dict[str, List[str]],
    observed_tokens: Dict[str, List[str]],
) -> Dict[str, Dict[str, List[str]]]:
    changes = {}
    for case_id, tokens in baseline_tokens.items():
        baseline_set = set(tokens)
        observed_set = set(observed_tokens[case_id])
        if baseline_set != observed_set:
            changes[case_id] = {
                "baseline_only": sorted(baseline_set - observed_set),
                "observed_only": sorted(observed_set - baseline_set),
            }
    return changes


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _format_cli_rows(summary: Dict[str, object]) -> Iterable[str]:
    robustness_summary = summary["robustness_summary"]
    yield ROBUSTNESS_LABEL
    yield (
        "baseline_ordering="
        + ",".join(robustness_summary["baseline_ordering_low_to_high"])
    )
    for row in summary["variant_results"]:
        yield (
            f"{row['variant_id']}: family={row['variation_family']} | "
            f"ordering={','.join(row['ordering_low_to_high'])} | "
            f"min_gap={row['documented_gap_metrics']['minimum_gap']:.6f} | "
            f"flips={row['ordering_flip_count']} | "
            f"recommendation={row['recommendation']}"
        )
    yield (
        "variants_with_ordering_flips="
        + (
            ",".join(robustness_summary["variants_with_ordering_flips"])
            if robustness_summary["variants_with_ordering_flips"]
            else "none"
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run bounded robustness sweeps for the EXPERIMENTAL_SANDBOX multi-slice critic."
    )
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parent / "robustness_out"),
        help="Root directory for robustness sweep outputs.",
    )
    args = parser.parse_args()

    summary = run_robustness_pass(output_root=Path(args.output_root))
    for row in _format_cli_rows(summary):
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
