"""Sandbox-only tests for the experimental analytical 2D critic demo."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = REPO_ROOT / "experiments" / "analytical_2d_critic"
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from run_demo import run_demo


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_analytical_2d_critic_demo_is_deterministic_and_distinct(tmp_path):
    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"

    critic_a = run_demo(out_a)
    critic_b = run_demo(out_b)

    assert critic_a == critic_b
    assert critic_a["bounded_critic_summary"]["ordering_low_to_high"] == [
        "straight_channel",
        "single_obstruction",
        "constricted_channel",
    ]
    assert critic_a["bounded_critic_summary"]["recommendation"] == "continue"

    expected_classes = {
        "straight_channel": "EXACT_ANALYTIC",
        "single_obstruction": "SYNTHETIC",
        "constricted_channel": "QUASI_ANALYTICAL",
    }

    theta_std = {}
    deflection = {}

    for case_id, provenance_class in expected_classes.items():
        npz_a = out_a / "fields" / f"{case_id}.npz"
        npz_b = out_b / "fields" / f"{case_id}.npz"
        assert _sha256(npz_a) == _sha256(npz_b)

        summary_a = _load_json(out_a / "results" / case_id / "summary.json")
        summary_b = _load_json(out_b / "results" / case_id / "summary.json")
        descriptor_a = _load_json(out_a / "results" / case_id / "descriptor_summary.json")
        descriptor_b = _load_json(out_b / "results" / case_id / "descriptor_summary.json")
        field_contract_a = _load_json(out_a / "results" / case_id / "field_contract.json")
        field_contract_b = _load_json(out_b / "results" / case_id / "field_contract.json")

        assert summary_a == summary_b
        assert descriptor_a == descriptor_b
        assert field_contract_a["input_sha256"] == field_contract_b["input_sha256"]
        assert descriptor_a["provenance_class"] == provenance_class

        theta_std[case_id] = descriptor_a["descriptor_stats"]["theta_std_rad"]
        deflection[case_id] = descriptor_a["descriptor_stats"]["deflection_fraction"]

        sig_a = out_a / "results" / case_id / "signatures.jsonl"
        sig_b = out_b / "results" / case_id / "signatures.jsonl"
        assert _sha256(sig_a) == _sha256(sig_b)

    assert theta_std["straight_channel"] < theta_std["single_obstruction"] < theta_std["constricted_channel"]
    assert deflection["straight_channel"] < deflection["single_obstruction"] < deflection["constricted_channel"]
