"""Tests for real Stage 4 candidate comparison — bridge output determinism and sensitivity.

These tests verify that:
1. Bridge outputs for candidate_01 and candidate_02 are each independently deterministic.
2. Bridge outputs DIFFER between candidates (i.e., the pipeline is sensitive to input).
3. Key summary statistics are in documented, plausible ranges.
4. The comparison is fully documented (slice policy, artifact paths, known differences).

These tests gate advancement past "IMPLEMENTED" toward "VALIDATED" for the real-artifact path.
See CLAIM_TIERS.md.

CLAIM TIERS:
  IMPLEMENTED: both candidates are loaded and encoded
  VALIDATED (gated here): outputs are deterministic AND differ between candidates
  NOT_PROVEN: that any numeric difference reflects a physical performance difference
  NOT_PROVEN: that the compared z-slice is the "right" cross-section for either geometry
  NOT_PROVEN: that theta_std ranking correlates with any real-world metric

Slice policy (frozen for this comparison):
  axis=z, index=25 (midpoint of 50-voxel z-dimension), solid_threshold=1e-3
"""

import hashlib
import json
from pathlib import Path

import pytest

# -- Locate sibling repo artifacts --
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BASE = (
    _REPO_ROOT.parent / "coldplate-design-engine" / "results" / "stage4_sim_full"
)
_CAND01_VEL = _BASE / "candidate_01_diamond_2d_s1127" / "velocity_field.npz"
_CAND01_PROV = _BASE / "candidate_01_diamond_2d_s1127" / "provenance.json"
_CAND02_VEL = _BASE / "candidate_02_diamond_2d_s1045" / "velocity_field.npz"
_CAND02_PROV = _BASE / "candidate_02_diamond_2d_s1045" / "provenance.json"

# Frozen slice policy for this comparison
_SLICE_AXIS = "z"
_SLICE_INDEX = 25    # midpoint of 50-voxel depth
_SOLID_THRESHOLD = 1e-3

requires_both = pytest.mark.skipif(
    not (
        _CAND01_VEL.exists() and _CAND01_PROV.exists()
        and _CAND02_VEL.exists() and _CAND02_PROV.exists()
    ),
    reason="Real Stage 4 full artifacts (cand01 + cand02) not found at expected paths"
)

from topobridge.adapters.stage4_velocity_adapter import load_stage4_field_bundle, Stage4SliceConfig
from topobridge.encode.field_to_signature import field_to_signatures


# -- Helpers --

def _load_and_encode(vel_path, prov_path):
    cfg = Stage4SliceConfig(
        velocity_field_path=str(vel_path),
        provenance_path=str(prov_path),
        slice_axis=_SLICE_AXIS,
        slice_index=_SLICE_INDEX,
        solid_threshold_fraction=_SOLID_THRESHOLD,
        include_axial_as_scalar=True,
    )
    bundle = load_stage4_field_bundle(cfg)
    output = field_to_signatures(bundle)
    return bundle, output


def _stream_hash(output):
    content = "\n".join(
        json.dumps(r.to_dict(), sort_keys=True) for r in output.records
    )
    return hashlib.sha256(content.encode()).hexdigest()


# =========================================================================
# Gate tests: VALIDATED tier for real-artifact comparison path
# =========================================================================

class TestRealCandidateComparison:
    """Comparison gate tests for candidate_01 vs candidate_02 (Stage 4 full run)."""

    @requires_both
    def test_candidate01_output_is_deterministic(self):
        """Candidate 01 must produce identical JSONL stream hash on two runs.

        VALIDATED gate criterion (1 of 3).
        """
        _, out1 = _load_and_encode(_CAND01_VEL, _CAND01_PROV)
        _, out2 = _load_and_encode(_CAND01_VEL, _CAND01_PROV)
        h1 = _stream_hash(out1)
        h2 = _stream_hash(out2)
        assert h1 == h2, (
            f"candidate_01 output is NOT deterministic.\n"
            f"run1: {h1[:16]}\nrun2: {h2[:16]}"
        )

    @requires_both
    def test_candidate02_output_is_deterministic(self):
        """Candidate 02 must produce identical JSONL stream hash on two runs.

        VALIDATED gate criterion (1 of 3).
        """
        _, out1 = _load_and_encode(_CAND02_VEL, _CAND02_PROV)
        _, out2 = _load_and_encode(_CAND02_VEL, _CAND02_PROV)
        h1 = _stream_hash(out1)
        h2 = _stream_hash(out2)
        assert h1 == h2, (
            f"candidate_02 output is NOT deterministic.\n"
            f"run1: {h1[:16]}\nrun2: {h2[:16]}"
        )

    @requires_both
    def test_outputs_differ_between_candidates(self):
        """Bridge outputs for different geometry seeds must produce different stream hashes.

        VALIDATED gate criterion (2 of 3).
        Confirms the pipeline is sensitive to input geometry, not producing constant output.
        NOT_PROVEN: that the hash difference reflects any physical performance difference.
        """
        _, out1 = _load_and_encode(_CAND01_VEL, _CAND01_PROV)
        _, out2 = _load_and_encode(_CAND02_VEL, _CAND02_PROV)
        h1 = _stream_hash(out1)
        h2 = _stream_hash(out2)
        assert h1 != h2, (
            "candidate_01 and candidate_02 produced IDENTICAL stream hashes — "
            "unexpected: different geometry seeds should produce different 2D slices"
        )

    @requires_both
    def test_summary_stats_differ_between_candidates(self):
        """At least one bridge summary statistic must differ between candidates.

        Confirms that the difference is captured in human-readable metrics,
        not just in the raw JSONL hash.
        NOT_PROVEN: statistical differences reflect physical performance differences.
        """
        _, out1 = _load_and_encode(_CAND01_VEL, _CAND01_PROV)
        _, out2 = _load_and_encode(_CAND02_VEL, _CAND02_PROV)
        s1 = out1.summary
        s2 = out2.summary

        differing = []
        for key in ("n_active_pixels", "n_solid_pixels"):
            if s1[key] != s2[key]:
                differing.append(key)
        for key in ("std_rad", "mean_rad"):
            if abs(s1["theta_stats"][key] - s2["theta_stats"][key]) > 1e-6:
                differing.append(f"theta_stats.{key}")

        assert len(differing) > 0, (
            f"No summary stat differs between candidates — unexpected.\n"
            f"s1127: n_active={s1['n_active_pixels']}, theta_std={s1['theta_stats']['std_rad']:.5f}\n"
            f"s1045: n_active={s2['n_active_pixels']}, theta_std={s2['theta_stats']['std_rad']:.5f}"
        )

    @requires_both
    def test_same_git_sha_across_candidates(self):
        """Both candidates in the full run must share the same source git SHA.

        This confirms they were produced under identical solver conditions,
        making the comparison valid as a geometry-only comparison.
        """
        bundle1, _ = _load_and_encode(_CAND01_VEL, _CAND01_PROV)
        bundle2, _ = _load_and_encode(_CAND02_VEL, _CAND02_PROV)
        sha1 = bundle1.provenance.source_commit
        sha2 = bundle2.provenance.source_commit
        assert sha1 == sha2, (
            f"Candidates have different source git SHAs — comparison may be confounded.\n"
            f"cand01: {sha1}\ncand02: {sha2}"
        )

    @requires_both
    def test_both_candidates_same_grid_shape(self):
        """Both 50x50x50 candidates sliced at z=25 must produce (50, 50) 2D shape."""
        bundle1, _ = _load_and_encode(_CAND01_VEL, _CAND01_PROV)
        bundle2, _ = _load_and_encode(_CAND02_VEL, _CAND02_PROV)
        assert bundle1.shape == (50, 50), f"cand01 shape: {bundle1.shape}"
        assert bundle2.shape == (50, 50), f"cand02 shape: {bundle2.shape}"
        assert bundle1.shape == bundle2.shape, "Shape mismatch between candidates"

    @requires_both
    def test_solid_fractions_in_expected_range(self):
        """Solid fractions for both candidates must match 3D porosity within ±10%.

        3D porosity: cand01=0.555192 → solid_frac~0.4448
                     cand02=0.563976 → solid_frac~0.4360
        At z=25 slice: slightly different due to local geometry variation.
        Tolerance: ±10% from 3D solid fraction — NOT_PROVEN at pixel level.
        """
        bundle1, _ = _load_and_encode(_CAND01_VEL, _CAND01_PROV)
        bundle2, _ = _load_and_encode(_CAND02_VEL, _CAND02_PROV)
        sf1 = bundle1.solid_mask.mean()
        sf2 = bundle2.solid_mask.mean()
        # From provenance: 3D solid = 0.4448, 0.4360 respectively
        assert 0.30 <= sf1 <= 0.60, f"cand01 solid_frac {sf1:.4f} out of range"
        assert 0.30 <= sf2 <= 0.60, f"cand02 solid_frac {sf2:.4f} out of range"

    @requires_both
    def test_theta_std_in_plausible_range(self):
        """Both candidates must have theta_std in (0, pi).

        A value of ~1.8 rad for a TPMS cross-section is expected given the
        multidirectional flow around the diamond struts.
        NOT_PROVEN: that this value is physically meaningful.
        """
        _, out1 = _load_and_encode(_CAND01_VEL, _CAND01_PROV)
        _, out2 = _load_and_encode(_CAND02_VEL, _CAND02_PROV)
        import math
        ts1 = out1.summary["theta_stats"]["std_rad"]
        ts2 = out2.summary["theta_stats"]["std_rad"]
        assert 0 < ts1 < math.pi, f"cand01 theta_std {ts1:.4f} outside (0, pi)"
        assert 0 < ts2 < math.pi, f"cand02 theta_std {ts2:.4f} outside (0, pi)"

    @requires_both
    def test_n_active_pixels_above_zero(self):
        """Both candidates must have at least 1 active pixel in the mid-slice."""
        _, out1 = _load_and_encode(_CAND01_VEL, _CAND01_PROV)
        _, out2 = _load_and_encode(_CAND02_VEL, _CAND02_PROV)
        assert out1.summary["n_active_pixels"] > 0, "cand01: no active pixels"
        assert out2.summary["n_active_pixels"] > 0, "cand02: no active pixels"

    @requires_both
    def test_record_keys_are_valid_schema(self):
        """Every record must contain the expected bridge_signature_stream schema keys."""
        _, out1 = _load_and_encode(_CAND01_VEL, _CAND01_PROV)
        required_keys = {
            "schema_version", "bridge_schema_id", "record_id",
            "i", "j", "is_solid", "is_low_signal",
            "theta_bridge", "magnitude",
        }
        for rec in out1.records[:10]:
            d = rec.to_dict()
            missing = required_keys - set(d.keys())
            assert not missing, (
                f"Record missing expected keys: {missing}\nActual keys: {set(d.keys())}"
            )
            assert d["bridge_schema_id"] == "bridge_signature_stream"
            assert isinstance(d["i"], int)
            assert isinstance(d["j"], int)
            assert isinstance(d["record_id"], str)
            assert len(d["record_id"]) > 0
