"""Control tests — negative and positive controls for bridge signature behavior.

These tests are GATE CRITERIA for VALIDATED tier in CLAIM_TIERS.md:
> "Negative control: uniform flow yields no strong signature"
> "Positive control: synthetic swirl yields nontrivial signature"

IMPORTANT EPISTEMIC CONSTRAINTS:
- These tests use synthetic fields only. No real CFD data is used.
- "Strong signature" is operationally defined as theta_std > threshold.
  This threshold is arbitrary. See docs/UNCERTAINTIES.md U-006.
- Passing these tests does NOT prove that bridge signatures correspond to
  any physical quantity. It only shows the encoder behaves as expected
  on the two extreme cases.
"""

import json
import math
from pathlib import Path

import numpy as np
import pytest

from topobridge.adapters.coldplate_field_loader import load_field_bundle
from topobridge.encode.field_to_signature import field_to_signatures


def _write_field(tmp_path: Path, name: str, u, v, solid_mask, scalar=None):
    """Write .npz + .meta.json and return npz path."""
    ny, nx = u.shape
    npz_path = tmp_path / f"{name}.npz"
    if scalar is not None:
        np.savez(str(npz_path), u=u, v=v, solid_mask=solid_mask, scalar=scalar)
    else:
        np.savez(str(npz_path), u=u, v=v, solid_mask=solid_mask)

    meta_path = tmp_path / f"{name}.meta.json"
    with open(meta_path, "w") as f:
        json.dump({
            "schema_version": "1.0.0",
            "source_repo": "test_controls",
            "source_stage": "synthetic",
            "source_artifact": f"{name}.npz",
            "source_commit": None,
            "preprocessing": ["synthetic_generated"],
            "grid_nx": nx,
            "grid_ny": ny,
            "grid_dx": None,
            "grid_dy": None,
            "field_frozen_at": "2026-03-10T17:00:00Z",
        }, f)

    return npz_path


def _make_uniform_field(ny=32, nx=32, angle_deg=0.0):
    """Uniform flow in a fixed direction. theta_bridge = constant everywhere."""
    angle_rad = math.radians(angle_deg)
    u = np.full((ny, nx), math.cos(angle_rad), dtype=np.float64)
    v = np.full((ny, nx), math.sin(angle_rad), dtype=np.float64)
    solid_mask = np.zeros((ny, nx), dtype=np.uint8)
    return u, v, solid_mask


def _make_swirl_field(ny=32, nx=32, center=None):
    """Counterclockwise circular flow. theta_bridge varies from -pi to pi."""
    if center is None:
        center = (ny / 2, nx / 2)
    cy, cx = center
    y_idx, x_idx = np.mgrid[:ny, :nx]
    dy = (y_idx - cy).astype(np.float64)
    dx = (x_idx - cx).astype(np.float64)
    mag = np.sqrt(dx**2 + dy**2) + 1e-10
    u = (-dy / mag)
    v = (dx / mag)
    solid_mask = np.zeros((ny, nx), dtype=np.uint8)
    return u, v, solid_mask


def _make_partial_solid_field(ny=16, nx=16):
    """Flow with a solid obstacle in the center."""
    u = np.ones((ny, nx), dtype=np.float64)
    v = np.zeros((ny, nx), dtype=np.float64)
    solid_mask = np.zeros((ny, nx), dtype=np.uint8)
    # Central 4x4 block is solid
    cy, cx = ny // 2, nx // 2
    r = 2
    solid_mask[cy-r:cy+r, cx-r:cx+r] = 1
    return u, v, solid_mask


class TestNegativeControl:
    """Uniform flow should yield near-zero theta variance (no strong signature).

    Operational definition:
      theta_std < 1e-10 (rad) for a perfectly uniform field with no solid/low-signal pixels.

    Claim tier: IMPLEMENTED.
    NOT_PROVEN: That this means "no topological features". It means no angle variation.
    """

    def test_uniform_rightward_flow_has_zero_theta_std(self, tmp_path):
        """Uniform →→→ flow: all active theta = atan2(0, 1) = 0. Std should be ~0."""
        u, v, solid_mask = _make_uniform_field(angle_deg=0.0)
        npz_path = _write_field(tmp_path, "uniform_right", u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)

        summary = output.summary
        theta_std = summary["theta_stats"]["std_rad"]

        assert theta_std < 1e-10, (
            f"Uniform rightward flow should have theta_std ≈ 0, got {theta_std:.6e}"
        )

    def test_uniform_flow_at_45deg_has_zero_theta_std(self, tmp_path):
        """Uniform flow at any fixed angle: theta should be constant."""
        u, v, solid_mask = _make_uniform_field(angle_deg=45.0)
        npz_path = _write_field(tmp_path, "uniform_45", u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)

        theta_std = output.summary["theta_stats"]["std_rad"]
        assert theta_std < 1e-10, (
            f"Uniform 45° flow should have theta_std ≈ 0, got {theta_std:.6e}"
        )

    def test_uniform_flow_all_pixels_active(self, tmp_path):
        """Uniform flow: no solid, no low-signal pixels (all pixels should be active)."""
        ny, nx = 16, 16
        u, v, solid_mask = _make_uniform_field(ny=ny, nx=nx, angle_deg=0.0)
        npz_path = _write_field(tmp_path, "uniform_fullgrid", u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)

        summary = output.summary
        assert summary["n_solid_pixels"] == 0
        assert summary["n_low_signal_pixels"] == 0
        assert summary["n_active_pixels"] == ny * nx

    def test_no_signature_records_have_null_theta_for_uniform_full_grid(self, tmp_path):
        """Uniform flow on full grid: every record should have non-null theta."""
        u, v, solid_mask = _make_uniform_field(angle_deg=30.0)
        npz_path = _write_field(tmp_path, "uniform_30", u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)

        null_theta_records = [r for r in output.records if r.theta_bridge is None]
        assert len(null_theta_records) == 0, (
            f"Expected 0 records with null theta, got {len(null_theta_records)}"
        )


class TestPositiveControl:
    """Synthetic swirl flow should yield high theta variance (nontrivial signature).

    Operational definition:
      theta_std > pi/4 (0.785 rad) for a circular flow covering the full domain.
      (A full circle spans [-pi, pi], so std >> 0 for any full circular sweep.)

    Claim tier: IMPLEMENTED.
    NOT_PROVEN: That this "signature" corresponds to a vortex, defect, or topological event.
    """

    def test_swirl_field_has_high_theta_std(self, tmp_path):
        """Circular flow: theta rotates 2π around center → high theta_std."""
        u, v, solid_mask = _make_swirl_field(ny=32, nx=32)
        npz_path = _write_field(tmp_path, "swirl", u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)

        theta_std = output.summary["theta_stats"]["std_rad"]
        # A full circular sweep: std should be large (>> pi/4)
        assert theta_std > math.pi / 4.0, (
            f"Swirl field should have theta_std > pi/4 = {math.pi/4:.4f}, "
            f"got {theta_std:.4f}"
        )

    def test_swirl_has_more_theta_variance_than_uniform(self, tmp_path):
        """Swirl should have strictly higher theta variance than uniform flow."""
        u_swirl, v_swirl, mask_swirl = _make_swirl_field(ny=32, nx=32)
        u_uni, v_uni, mask_uni = _make_uniform_field(ny=32, nx=32, angle_deg=0.0)

        npz_sw = _write_field(tmp_path, "swirl32", u_swirl, v_swirl, mask_swirl)
        npz_un = _write_field(tmp_path, "uniform32", u_uni, v_uni, mask_uni)

        bundle_sw = load_field_bundle(str(npz_sw))
        bundle_un = load_field_bundle(str(npz_un))

        out_sw = field_to_signatures(bundle_sw)
        out_un = field_to_signatures(bundle_un)

        std_swirl = out_sw.summary["theta_stats"]["std_rad"]
        std_uniform = out_un.summary["theta_stats"]["std_rad"]

        assert std_swirl > std_uniform, (
            f"Swirl std ({std_swirl:.4f}) should exceed uniform std ({std_uniform:.4f})"
        )

    def test_swirl_gradient_mean_exceeds_uniform(self, tmp_path):
        """Swirl should have higher mean spatial gradient of theta than uniform flow."""
        u_swirl, v_swirl, mask_swirl = _make_swirl_field(ny=32, nx=32)
        u_uni, v_uni, mask_uni = _make_uniform_field(ny=32, nx=32, angle_deg=0.0)

        npz_sw = _write_field(tmp_path, "swirlg", u_swirl, v_swirl, mask_swirl)
        npz_un = _write_field(tmp_path, "uniformg", u_uni, v_uni, mask_uni)

        bundle_sw = load_field_bundle(str(npz_sw))
        bundle_un = load_field_bundle(str(npz_un))

        out_sw = field_to_signatures(bundle_sw)
        out_un = field_to_signatures(bundle_un)

        grad_swirl = out_sw.summary["gradient_stats"]["mean_grad_mag"]
        grad_uniform = out_un.summary["gradient_stats"]["mean_grad_mag"]

        assert grad_swirl > grad_uniform, (
            f"Swirl gradient ({grad_swirl:.4f}) should exceed uniform gradient ({grad_uniform:.4f})"
        )

    def test_swirl_records_have_nontrivial_theta_spread(self, tmp_path):
        """Active pixels in swirl should span a wide range of theta values."""
        u, v, solid_mask = _make_swirl_field(ny=32, nx=32)
        npz_path = _write_field(tmp_path, "swirl_spread", u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)

        active_thetas = [r.theta_bridge for r in output.records if r.theta_bridge is not None]
        assert len(active_thetas) > 0

        theta_range = max(active_thetas) - min(active_thetas)
        # A circular flow spans nearly 2π
        assert theta_range > math.pi, (
            f"Swirl theta range ({theta_range:.4f}) should exceed pi={math.pi:.4f}"
        )


class TestMixedControl:
    """Tests with partial solid mask."""

    def test_solid_pixels_excluded_from_active_count(self, tmp_path):
        """Solid region pixels must not be counted as active."""
        ny, nx = 16, 16
        u, v, solid_mask = _make_partial_solid_field(ny, nx)
        npz_path = _write_field(tmp_path, "partial_solid", u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)

        summary = output.summary
        expected_solid = int(solid_mask.sum())
        assert summary["n_solid_pixels"] == expected_solid
        assert summary["n_active_pixels"] == ny * nx - expected_solid - summary["n_low_signal_pixels"]

    def test_solid_pixels_have_null_theta_in_records(self, tmp_path):
        """Every record flagged is_solid=True must have theta_bridge=None."""
        ny, nx = 16, 16
        u, v, solid_mask = _make_partial_solid_field(ny, nx)
        npz_path = _write_field(tmp_path, "ps_nulltheta", u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)

        for rec in output.records:
            if rec.is_solid:
                assert rec.theta_bridge is None, (
                    f"Solid pixel ({rec.i},{rec.j}) must have theta_bridge=None"
                )
