"""Sandbox-only tests for the experimental multi-slice/simple-3D critic demo."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
_EXPERIMENT_ROOT = REPO_ROOT / "experiments" / "multi_slice_3d_critic"

# Flush any stale sys.modules entries for bare experiment-local names.
# This prevents a previously imported analytical_2d_critic version of
# run_demo / extract_descriptors from shadowing this experiment's version.
_EXPERIMENT_LOCAL_NAMES = [
    "run_demo", "generate_stack", "extract_descriptors",
]
for _name in _EXPERIMENT_LOCAL_NAMES:
    sys.modules.pop(_name, None)

# Ensure this experiment's directory is at sys.path[0] so bare-name imports
# within the experiment scripts resolve to the correct co-located files.
_exp_str = str(_EXPERIMENT_ROOT)
if _exp_str in sys.path:
    sys.path.remove(_exp_str)
sys.path.insert(0, _exp_str)

from run_demo import run_demo  # noqa: E402 — must follow path fixup
from topobridge.adapters import stage4_velocity_adapter  # noqa: E402


# Reduced runtime grid; ordering and recommendation must still match the documented lane.
TEST_NX = 24
TEST_NY = 16
TEST_N_SLICES = 3


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_multi_slice_3d_critic_demo_is_deterministic_and_separable(tmp_path):
    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"

    critic_a = run_demo(out_a, nx=TEST_NX, ny=TEST_NY, n_slices=TEST_N_SLICES)
    critic_b = run_demo(out_b, nx=TEST_NX, ny=TEST_NY, n_slices=TEST_N_SLICES)

    assert critic_a == critic_b
    assert critic_a["bounded_critic_summary"]["ordering_low_to_high"] == [
        "straight_stack",
        "obstruction_stack",
        "constriction_stack",
    ]
    assert critic_a["bounded_critic_summary"]["recommendation"] == "continue"

    stack_scores = {
        row["case_id"]: row["stack_complexity_index"]
        for row in critic_a["case_summaries"]
    }
    assert stack_scores["obstruction_stack"] - stack_scores["straight_stack"] > 0.08
    assert stack_scores["constriction_stack"] - stack_scores["obstruction_stack"] > 0.08

    expected_classes = {
        "straight_stack": "EXACT_ANALYTIC",
        "obstruction_stack": "SYNTHETIC",
        "constriction_stack": "QUASI_ANALYTICAL",
    }

    for case_id, provenance_class in expected_classes.items():
        manifest_a = _load_json(out_a / "fields" / case_id / "stack_manifest.json")
        manifest_b = _load_json(out_b / "fields" / case_id / "stack_manifest.json")
        assert manifest_a == manifest_b
        assert manifest_a["provenance_class"] == provenance_class
        assert manifest_a["source_stage"] == "experimental_multi_slice_3d_critic"

        case_summary_a = _load_json(out_a / "results" / case_id / "case_summary.json")
        case_summary_b = _load_json(out_b / "results" / case_id / "case_summary.json")
        assert case_summary_a == case_summary_b
        assert case_summary_a["provenance_class"] == provenance_class
        assert case_summary_a["slice_count"] == TEST_N_SLICES

        for slice_row in case_summary_a["slice_overview"]:
            slice_id = slice_row["slice_id"]
            npz_a = out_a / "fields" / case_id / f"{slice_id}.npz"
            npz_b = out_b / "fields" / case_id / f"{slice_id}.npz"
            assert _sha256(npz_a) == _sha256(npz_b)

            summary_a = _load_json(out_a / "results" / case_id / "slices" / slice_id / "summary.json")
            summary_b = _load_json(out_b / "results" / case_id / "slices" / slice_id / "summary.json")
            descriptor_a = _load_json(
                out_a / "results" / case_id / "slices" / slice_id / "descriptor_summary.json"
            )
            descriptor_b = _load_json(
                out_b / "results" / case_id / "slices" / slice_id / "descriptor_summary.json"
            )
            field_contract_a = _load_json(
                out_a / "results" / case_id / "slices" / slice_id / "field_contract.json"
            )
            field_contract_b = _load_json(
                out_b / "results" / case_id / "slices" / slice_id / "field_contract.json"
            )

            assert summary_a == summary_b
            assert descriptor_a == descriptor_b
            assert field_contract_a["input_sha256"] == field_contract_b["input_sha256"]
            assert descriptor_a["provenance_class"] == provenance_class

            sig_a = out_a / "results" / case_id / "slices" / slice_id / "signatures.jsonl"
            sig_b = out_b / "results" / case_id / "slices" / slice_id / "signatures.jsonl"
            assert _sha256(sig_a) == _sha256(sig_b)


def test_multi_slice_3d_critic_demo_does_not_depend_on_stage4_files(tmp_path, monkeypatch):
    def _unexpected_stage4_call(*args, **kwargs):
        raise AssertionError("Stage 4 adapter should not be used by the multi-slice sandbox.")

    monkeypatch.setattr(
        stage4_velocity_adapter,
        "load_stage4_field_bundle",
        _unexpected_stage4_call,
    )

    critic = run_demo(tmp_path / "run", nx=TEST_NX, ny=TEST_NY, n_slices=TEST_N_SLICES)

    assert critic["sandbox_status"] == "EXPERIMENTAL_SANDBOX"
    assert critic["what_this_is"].startswith("A stack of 2D slices")
    for row in critic["case_summaries"]:
        assert row["provenance_class"] in {"EXACT_ANALYTIC", "SYNTHETIC", "QUASI_ANALYTICAL"}

    for case_id in ("straight_stack", "obstruction_stack", "constriction_stack"):
        manifest = _load_json(tmp_path / "run" / "fields" / case_id / "stack_manifest.json")
        assert manifest["source_stage"] == "experimental_multi_slice_3d_critic"
        assert "stage4" not in json.dumps(manifest).lower()
