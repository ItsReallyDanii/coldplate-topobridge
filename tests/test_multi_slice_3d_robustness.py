"""Bounded robustness tests for the experimental multi-slice/simple-3D critic."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
_EXPERIMENT_ROOT = REPO_ROOT / "experiments" / "multi_slice_3d_critic"

# Flush any stale sys.modules entries for bare experiment-local names.
# This prevents a previously imported analytical_2d_critic version of
# extract_descriptors from shadowing this experiment's version, and prevents
# a stale run_demo from another experiment from being resolved by run_robustness.
_EXPERIMENT_LOCAL_NAMES = [
    "run_demo", "run_robustness", "generate_stack", "extract_descriptors",
]
for _name in _EXPERIMENT_LOCAL_NAMES:
    sys.modules.pop(_name, None)

# Ensure this experiment's directory is at sys.path[0] so bare-name imports
# within the experiment scripts resolve to the correct co-located files.
_exp_str = str(_EXPERIMENT_ROOT)
if _exp_str in sys.path:
    sys.path.remove(_exp_str)
sys.path.insert(0, _exp_str)

from generate_stack import PerturbationConfig  # noqa: E402 — must follow path fixup
from run_robustness import RobustnessVariant, run_robustness_pass  # noqa: E402


TEST_VARIANTS = [
    RobustnessVariant(
        variant_id="baseline",
        variation_family="baseline",
        description="Test baseline.",
        nx=12,
        ny=8,
        n_slices=3,
    ),
    RobustnessVariant(
        variant_id="slice_count_5",
        variation_family="slice_count",
        description="Higher slice count.",
        nx=12,
        ny=8,
        n_slices=5,
    ),
    RobustnessVariant(
        variant_id="resolution_16x10",
        variation_family="grid_resolution",
        description="Slightly finer grid.",
        nx=16,
        ny=10,
        n_slices=3,
    ),
    RobustnessVariant(
        variant_id="threshold_0p020",
        variation_family="descriptor_threshold",
        description="Higher low-signal threshold.",
        nx=12,
        ny=8,
        n_slices=3,
        low_signal_threshold=0.02,
    ),
    RobustnessVariant(
        variant_id="perturbation_0p012",
        variation_family="bounded_perturbation",
        description="Deterministic mild perturbation.",
        nx=12,
        ny=8,
        n_slices=3,
        perturbation_config=PerturbationConfig(
            mode="sinusoidal_dither",
            amplitude_fraction=0.012,
            phase_seed=7,
        ),
    ),
]


def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_multi_slice_robustness_pass_is_deterministic_and_stable(tmp_path):
    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"

    summary_a = run_robustness_pass(out_a, variants=TEST_VARIANTS)
    summary_b = run_robustness_pass(out_b, variants=TEST_VARIANTS)

    assert summary_a == summary_b
    assert _load_json(out_a / "robustness_summary.json") == _load_json(
        out_b / "robustness_summary.json"
    )

    robustness = summary_a["robustness_summary"]
    assert robustness["baseline_ordering_low_to_high"] == [
        "straight_stack",
        "obstruction_stack",
        "constriction_stack",
    ]
    assert robustness["variants_with_ordering_flips"] == []

    for row in summary_a["variant_results"]:
        assert row["matches_baseline_ordering"] is True
        assert row["ordering_flip_count"] == 0
        assert row["ordering_flips"] == []
        assert row["recommendation"] == "continue"
        assert row["documented_gap_metrics"]["documented_separation_retained"] is True


def test_multi_slice_robustness_pass_records_variant_outputs_and_flip_status(tmp_path):
    summary = run_robustness_pass(tmp_path / "run", variants=TEST_VARIANTS)

    observed_families = {row["variation_family"] for row in summary["variant_results"]}
    assert observed_families == {
        "baseline",
        "slice_count",
        "grid_resolution",
        "descriptor_threshold",
        "bounded_perturbation",
    }

    for row in summary["variant_results"]:
        critic_summary_path = tmp_path / "run" / Path(row["critic_summary_path"])
        assert critic_summary_path.exists()
        assert row["ordering_flip_count"] == len(row["ordering_flips"])
        assert row["output_root"] == str(Path("variants") / row["variant_id"])

    robustness = summary["robustness_summary"]
    assert robustness["variants_without_ordering_flips"] == [
        row["variant_id"] for row in summary["variant_results"]
    ]
    assert robustness["variants_with_ordering_flips"] == []
    assert robustness["changed_findings"][0].startswith(
        "Absolute stack_complexity_index values moved"
    )
