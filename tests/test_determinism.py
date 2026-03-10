"""Tests for deterministic rerun behavior.

Validates: given identical inputs, all output hashes are identical across runs.

This is a GATE CRITERION for VALIDATED tier in CLAIM_TIERS.md:
> "Deterministic rerun test passes (identical hash on second run with same input)"
"""

import hashlib
import json
import tempfile
from pathlib import Path
from typing import List

import numpy as np
import pytest

from topobridge.adapters.coldplate_field_loader import load_field_bundle
from topobridge.encode.field_to_signature import field_to_signatures


def _write_test_field(tmp_path: Path, seed: int = 42) -> Path:
    """Write a reproducible test field with sidecar."""
    rng = np.random.RandomState(seed)
    ny, nx = 16, 16
    u = rng.randn(ny, nx).astype(np.float64)
    v = rng.randn(ny, nx).astype(np.float64)
    # Some solid pixels
    solid_mask = np.zeros((ny, nx), dtype=np.uint8)
    solid_mask[0:2, :] = 1  # top 2 rows solid
    solid_mask[14:, :] = 1  # bottom 2 rows solid

    npz_path = tmp_path / "det_field.npz"
    np.savez(str(npz_path), u=u, v=v, solid_mask=solid_mask)

    meta_path = tmp_path / "det_field.meta.json"
    with open(meta_path, "w") as f:
        json.dump({
            "schema_version": "1.0.0",
            "source_repo": "test_determinism",
            "source_stage": "test",
            "source_artifact": "det_field.npz",
            "source_commit": "deadbeef",
            "preprocessing": [],
            "grid_nx": nx,
            "grid_ny": ny,
            "grid_dx": None,
            "grid_dy": None,
            "field_frozen_at": "2026-03-10T17:00:00Z",
        }, f)

    return npz_path


def _run_and_collect_hashes(npz_path: Path) -> dict:
    """Run encoding pipeline and collect deterministic outputs."""
    bundle = load_field_bundle(str(npz_path))
    output = field_to_signatures(bundle)

    # Collect: input hash, all record IDs, all theta values, summary stats
    record_ids = [r.record_id for r in output.records]
    theta_values = [r.theta_bridge for r in output.records]
    magnitude_values = [r.magnitude for r in output.records]
    is_solid_values = [r.is_solid for r in output.records]
    is_low_signal_values = [r.is_low_signal for r in output.records]

    # Hash of the JSONL stream (deterministic ordering)
    jsonl_content = "\n".join(
        json.dumps(r.to_dict(), sort_keys=True) for r in output.records
    )
    jsonl_hash = hashlib.sha256(jsonl_content.encode("utf-8")).hexdigest()

    # Hash of summary (sort_keys for determinism)
    summary_str = json.dumps(output.summary, sort_keys=True)
    summary_hash = hashlib.sha256(summary_str.encode("utf-8")).hexdigest()

    return {
        "input_sha256": bundle.input_sha256,
        "n_records": len(output.records),
        "record_ids": record_ids,
        "theta_values": theta_values,
        "magnitude_values": magnitude_values,
        "is_solid": is_solid_values,
        "is_low_signal": is_low_signal_values,
        "jsonl_hash": jsonl_hash,
        "summary_hash": summary_hash,
        "low_signal_threshold": output.low_signal_threshold,
    }


class TestDeterminism:

    def test_same_input_same_output_twice(self, tmp_path):
        """Running the pipeline twice on the same file produces identical outputs."""
        npz_path = _write_test_field(tmp_path)

        run1 = _run_and_collect_hashes(npz_path)
        run2 = _run_and_collect_hashes(npz_path)

        assert run1["input_sha256"] == run2["input_sha256"], (
            "Input hash changed between runs — filesystem issue"
        )
        assert run1["n_records"] == run2["n_records"]
        assert run1["record_ids"] == run2["record_ids"], (
            "Record IDs are not deterministic"
        )
        assert run1["theta_values"] == run2["theta_values"], (
            "Theta values changed between runs"
        )
        assert run1["magnitude_values"] == run2["magnitude_values"]
        assert run1["is_solid"] == run2["is_solid"]
        assert run1["is_low_signal"] == run2["is_low_signal"]
        assert run1["jsonl_hash"] == run2["jsonl_hash"], (
            "JSONL stream hash changed — output is NOT deterministic"
        )
        assert run1["summary_hash"] == run2["summary_hash"], (
            "Summary hash changed — output is NOT deterministic"
        )
        assert run1["low_signal_threshold"] == run2["low_signal_threshold"]

    def test_different_inputs_produce_different_hashes(self, tmp_path):
        """Different input fields produce different output hashes — sanity check."""
        with tempfile.TemporaryDirectory() as tmp1:
            with tempfile.TemporaryDirectory() as tmp2:
                npz1 = _write_test_field(Path(tmp1), seed=42)
                npz2 = _write_test_field(Path(tmp2), seed=99)

                run1 = _run_and_collect_hashes(npz1)
                run2 = _run_and_collect_hashes(npz2)

                assert run1["input_sha256"] != run2["input_sha256"]
                assert run1["jsonl_hash"] != run2["jsonl_hash"]

    def test_record_id_is_deterministic_formula(self, tmp_path):
        """Record IDs follow the documented formula: sha256(input_sha256:i:j)[:16]."""
        import hashlib
        npz_path = _write_test_field(tmp_path)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)

        # Verify first few records
        input_sha = bundle.input_sha256
        for rec in output.records[:10]:
            expected_id = hashlib.sha256(
                f"{input_sha}:{rec.i}:{rec.j}".encode("utf-8")
            ).hexdigest()[:16]
            assert rec.record_id == expected_id, (
                f"Record ID mismatch at ({rec.i},{rec.j}): "
                f"got {rec.record_id}, expected {expected_id}"
            )

    def test_record_ordering_matches_raster_scan(self, tmp_path):
        """Records are emitted in row-major (raster) order: (0,0), (0,1), ..., (ny-1, nx-1)."""
        npz_path = _write_test_field(tmp_path)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)
        ny, nx = bundle.shape

        for idx, rec in enumerate(output.records):
            expected_i = idx // nx
            expected_j = idx % nx
            assert rec.i == expected_i
            assert rec.j == expected_j

    def test_theta_is_nan_for_solid_pixels(self, tmp_path):
        """theta_bridge must be None for solid pixels (guardrail: no angle in solid)."""
        npz_path = _write_test_field(tmp_path)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)

        for rec in output.records:
            if rec.is_solid:
                assert rec.theta_bridge is None, (
                    f"Solid pixel at ({rec.i},{rec.j}) has non-null theta_bridge"
                )
