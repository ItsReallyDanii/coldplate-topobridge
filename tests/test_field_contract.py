"""Tests for bridge field contract — schema validation and loader behavior.

Tests:
- Schema validation for field_contract.json
- Schema validation for signature stream records
- Provenance sidecar loading
- Shape mismatch detection
- NaN rejection
- Invalid solid_mask values
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

# We need jsonschema available for schema tests
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


from topobridge.adapters.coldplate_field_loader import load_field_bundle, FieldBundle
from topobridge.encode.field_to_signature import field_to_signatures
from topobridge.io.schema_validate import validate_field_frame, validate_signature_record


# --- Fixtures ---

def _write_npz_and_meta(tmp_path: Path, u, v, solid_mask, scalar=None, meta_overrides=None):
    """Helper: write .npz + .meta.json to tmp_path, return (npz_path, meta_path)."""
    npz_path = tmp_path / "test_field.npz"
    if scalar is not None:
        np.savez(str(npz_path), u=u, v=v, solid_mask=solid_mask, scalar=scalar)
    else:
        np.savez(str(npz_path), u=u, v=v, solid_mask=solid_mask)

    ny, nx = u.shape
    meta = {
        "schema_version": "1.0.0",
        "source_repo": "test_repo",
        "source_stage": "test_stage",
        "source_artifact": "test/artifact.npy",
        "source_commit": None,
        "preprocessing": [],
        "grid_nx": nx,
        "grid_ny": ny,
        "grid_dx": None,
        "grid_dy": None,
        "field_frozen_at": "2026-03-10T17:00:00Z",
    }
    if meta_overrides:
        meta.update(meta_overrides)

    meta_path = tmp_path / "test_field.meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    return npz_path, meta_path


def _make_uniform_field(ny=8, nx=8):
    """Uniform rightward flow, no solid region."""
    u = np.ones((ny, nx), dtype=np.float64)
    v = np.zeros((ny, nx), dtype=np.float64)
    solid_mask = np.zeros((ny, nx), dtype=np.uint8)
    return u, v, solid_mask


def _make_swirl_field(ny=16, nx=16):
    """Synthetic swirl (circular) flow field, no solid region."""
    y_idx, x_idx = np.mgrid[:ny, :nx]
    cy, cx = ny / 2, nx / 2
    dy = y_idx - cy
    dx = x_idx - cx
    # Counterclockwise rotation: u = -dy, v = dx (normalized)
    mag = np.sqrt(dx**2 + dy**2) + 1e-10
    u = (-dy / mag).astype(np.float64)
    v = (dx / mag).astype(np.float64)
    solid_mask = np.zeros((ny, nx), dtype=np.uint8)
    return u, v, solid_mask


# --- Schema validation tests ---

@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
class TestFieldFrameSchemaValidation:
    def test_valid_record_passes(self, tmp_path):
        ny, nx = 8, 8
        u, v, solid_mask = _make_uniform_field(ny, nx)
        npz_path, meta_path = _write_npz_and_meta(tmp_path, u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)

        record = {
            "schema_version": "1.0.0",
            "bridge_schema_id": "bridge_field_frame",
            "input_file": str(npz_path),
            "input_sha256": bundle.input_sha256,
            "provenance": bundle.provenance.to_dict(),
            "field_shape": [ny, nx],
            "field_dtype": "float64",
            "has_scalar": False,
            "solid_mask_fraction": 0.0,
            "low_signal_fraction": 0.0,
            "low_signal_threshold": output.low_signal_threshold,
            "magnitude_stats": {"mean": 1.0, "std": 0.0, "min": 1.0, "max": 1.0},
        }
        # Should not raise
        validate_field_frame(record)

    def test_missing_required_key_fails(self, tmp_path):
        record = {
            "schema_version": "1.0.0",
            "bridge_schema_id": "bridge_field_frame",
            # missing input_file, input_sha256, etc.
        }
        with pytest.raises(Exception):  # jsonschema.ValidationError
            validate_field_frame(record)

    def test_wrong_sha256_format_fails(self):
        record = {
            "schema_version": "1.0.0",
            "bridge_schema_id": "bridge_field_frame",
            "input_file": "foo.npz",
            "input_sha256": "not-a-valid-sha256",  # wrong format
            "provenance": {
                "schema_version": "1.0.0",
                "source_repo": "r",
                "source_stage": "s",
                "source_artifact": "a",
                "preprocessing": [],
                "grid_nx": 8,
                "grid_ny": 8,
                "field_frozen_at": "2026-03-10T17:00:00Z",
            },
            "field_shape": [8, 8],
            "field_dtype": "float64",
            "has_scalar": False,
            "solid_mask_fraction": 0.0,
            "low_signal_fraction": 0.0,
            "low_signal_threshold": 0.01,
            "magnitude_stats": {"mean": 1.0, "std": 0.0, "min": 1.0, "max": 1.0},
        }
        with pytest.raises(Exception):
            validate_field_frame(record)

    def test_valid_signature_record_passes(self, tmp_path):
        ny, nx = 4, 4
        u, v, solid_mask = _make_uniform_field(ny, nx)
        npz_path, _ = _write_npz_and_meta(tmp_path, u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        output = field_to_signatures(bundle)
        # Check first record
        record = output.records[0].to_dict()
        validate_signature_record(record)

    def test_signature_record_with_null_theta_passes(self):
        """Solid pixel record with null theta should pass schema."""
        record = {
            "schema_version": "1.0.0",
            "bridge_schema_id": "bridge_signature_stream",
            "record_id": "abcdef012345678",
            "i": 0,
            "j": 0,
            "is_solid": True,
            "is_low_signal": False,
            "theta_bridge": None,
            "magnitude": 0.0,
            "scalar": None,
        }
        validate_signature_record(record)


# --- Loader validation tests ---

class TestLoaderValidation:
    def test_shape_mismatch_raises(self, tmp_path):
        ny, nx = 8, 8
        u = np.ones((ny, nx), dtype=np.float64)
        v = np.ones((ny, nx + 1), dtype=np.float64)  # wrong shape
        solid_mask = np.zeros((ny, nx), dtype=np.uint8)
        npz_path = tmp_path / "bad.npz"
        np.savez(str(npz_path), u=u, v=v, solid_mask=solid_mask)
        meta_path = tmp_path / "bad.meta.json"
        meta = {
            "schema_version": "1.0.0",
            "source_repo": "r", "source_stage": "s",
            "source_artifact": "a", "preprocessing": [],
            "grid_nx": nx, "grid_ny": ny,
            "field_frozen_at": "2026-03-10T17:00:00Z",
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f)
        with pytest.raises(ValueError, match="shape"):
            load_field_bundle(str(npz_path))

    def test_nan_in_u_raises(self, tmp_path):
        ny, nx = 8, 8
        u = np.ones((ny, nx), dtype=np.float64)
        u[0, 0] = np.nan
        v = np.zeros((ny, nx), dtype=np.float64)
        solid_mask = np.zeros((ny, nx), dtype=np.uint8)
        npz_path, _ = _write_npz_and_meta(tmp_path, u, v, solid_mask)
        with pytest.raises(ValueError, match="NaN"):
            load_field_bundle(str(npz_path))

    def test_invalid_solid_mask_raises(self, tmp_path):
        ny, nx = 8, 8
        u = np.ones((ny, nx), dtype=np.float64)
        v = np.zeros((ny, nx), dtype=np.float64)
        solid_mask = np.full((ny, nx), 2, dtype=np.uint8)  # invalid value 2
        npz_path, _ = _write_npz_and_meta(tmp_path, u, v, solid_mask)
        with pytest.raises(ValueError, match="solid_mask"):
            load_field_bundle(str(npz_path))

    def test_missing_provenance_raises(self, tmp_path):
        ny, nx = 8, 8
        u, v, solid_mask = _make_uniform_field(ny, nx)
        npz_path = tmp_path / "noprov.npz"
        np.savez(str(npz_path), u=u, v=v, solid_mask=solid_mask)
        # No sidecar written
        with pytest.raises(ValueError, match="Provenance"):
            load_field_bundle(str(npz_path))

    def test_missing_required_key_raises(self, tmp_path):
        ny, nx = 8, 8
        npz_path = tmp_path / "nokeys.npz"
        np.savez(str(npz_path), u=np.ones((ny, nx)))  # missing v, solid_mask
        meta_path = tmp_path / "nokeys.meta.json"
        with open(meta_path, "w") as f:
            json.dump({
                "schema_version": "1.0.0", "source_repo": "r",
                "source_stage": "s", "source_artifact": "a",
                "preprocessing": [], "grid_nx": nx, "grid_ny": ny,
                "field_frozen_at": "2026-03-10T17:00:00Z",
            }, f)
        with pytest.raises(ValueError, match="'v'"):
            load_field_bundle(str(npz_path))

    def test_sha256_is_recorded(self, tmp_path):
        ny, nx = 8, 8
        u, v, solid_mask = _make_uniform_field(ny, nx)
        npz_path, _ = _write_npz_and_meta(tmp_path, u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        assert len(bundle.input_sha256) == 64
        assert all(c in "0123456789abcdef" for c in bundle.input_sha256)

    def test_scalar_loaded_when_present(self, tmp_path):
        ny, nx = 8, 8
        u, v, solid_mask = _make_uniform_field(ny, nx)
        scalar = np.random.rand(ny, nx).astype(np.float64)
        npz_path, _ = _write_npz_and_meta(tmp_path, u, v, solid_mask, scalar=scalar)
        bundle = load_field_bundle(str(npz_path))
        assert bundle.scalar is not None
        assert bundle.scalar.shape == (ny, nx)

    def test_scalar_absent_when_not_provided(self, tmp_path):
        ny, nx = 8, 8
        u, v, solid_mask = _make_uniform_field(ny, nx)
        npz_path, _ = _write_npz_and_meta(tmp_path, u, v, solid_mask)
        bundle = load_field_bundle(str(npz_path))
        assert bundle.scalar is None
