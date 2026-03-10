"""Stage 4 simulation adapter — reads velocity_field.npz from coldplate-design-engine Stage 4 results.

This adapter is READ-ONLY. It does NOT import any coldplate-design-engine Python modules.
It reads emitted artifact files only.

Physical setting (from solver.py audit):
  Velocity is Darcy velocity: v = -(k/μ) ∇p  (m/s)
  Flow direction: z-axis (inlet at z=0, outlet at z=nz-1)
  vx and vy are cross-sectional components (transverse to main flow)
  vz is the axial (through-plane) component

Bridge contract mapping (non-negotiable, not a physics claim):
  u = vx[:, :, slice_z]   — cross-sectional x-velocity
  v = vy[:, :, slice_z]   — cross-sectional y-velocity
  solid_mask = (magnitude < solid_threshold) & fluid_void  [NOTE below]
  scalar = vz[:, :, slice_z]  (optional — axial velocity, passed through as scalar)

NOTE — solid detection:
  Stage 4 does NOT separately emit a solid mask array. The only reliable
  way to detect solid cells from emitted artifacts alone is near-zero
  velocity magnitude. This is confirmed by:
    solid count = 55601 of 125000 = 0.444808 fraction
    porosity = 0.555192, so fluid fraction = 0.555192 — matches 69399/125000
  solid_threshold is intentionally set conservatively at 1e-3 × max_mag.
  This is documented as NOT_PROVEN for absolute accuracy.

CLAIM TIERS for this adapter:
  IMPLEMENTED: reads real artifact files, extracts 2D slice, builds FieldBundle
  NOT_PROVEN: that vx/vy slice semantics correspond to bridge signature semantics
  NOT_PROVEN: solid detection from velocity threshold is perfectly accurate
  NOT_PROVEN: z=25 (mid-slice) is the physically representative cross-section
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import numpy as np

from topobridge.adapters.coldplate_field_loader import FieldBundle, FieldProvenance

# Sentinel for solid detection threshold fraction of max velocity magnitude
_SOLID_DETECTION_FRACTION = 1e-3


@dataclass
class Stage4SliceConfig:
    """Configuration for slicing a 3D Stage 4 field to 2D.

    Attributes:
        velocity_field_path: Path to velocity_field.npz
        provenance_path: Path to provenance.json sidecar
        slice_axis: Axis to slice along. 'z' = cross-section perpendicular to flow.
        slice_index: Index along slice_axis. None = mid-point.
        solid_threshold_fraction: Fraction of max magnitude below which pixels are solid.
        include_axial_as_scalar: If True, vz slice is passed as optional scalar.
    """
    velocity_field_path: str
    provenance_path: str
    slice_axis: str = "z"          # 'x', 'y', or 'z'
    slice_index: Optional[int] = None  # None = midpoint
    solid_threshold_fraction: float = _SOLID_DETECTION_FRACTION
    include_axial_as_scalar: bool = True


def load_stage4_field_bundle(config: Stage4SliceConfig) -> FieldBundle:
    """Load a 2D bridge FieldBundle from a Stage 4 velocity_field.npz artifact.

    This function:
    1. Reads velocity_field.npz (keys: vx, vy, vz) — read-only
    2. Slices the 3D array at the requested z (or x/y) index
    3. Detects solid cells via near-zero magnitude threshold
    4. Reads provenance.json to build FieldProvenance
    5. Returns a FieldBundle compatible with field_to_signatures()

    Args:
        config: Stage4SliceConfig with paths and slice parameters.

    Returns:
        FieldBundle ready for bridge encoding.

    Raises:
        FileNotFoundError: If velocity_field.npz or provenance.json not found.
        ValueError: On format mismatch or invalid slice index.
    """
    vel_path = Path(config.velocity_field_path).resolve()
    prov_path = Path(config.provenance_path).resolve()

    if not vel_path.exists():
        raise FileNotFoundError(f"velocity_field.npz not found: {vel_path}")
    if not prov_path.exists():
        raise FileNotFoundError(f"provenance.json not found: {prov_path}")

    # --- Hash the raw file ---
    input_sha256 = _sha256_file(vel_path)

    # --- Load arrays (read-only, no parent-repo import) ---
    data = np.load(str(vel_path), allow_pickle=False)
    required_keys = ("vx", "vy", "vz")
    for k in required_keys:
        if k not in data:
            raise ValueError(
                f"velocity_field.npz missing key '{k}'. Available: {list(data.keys())}"
            )

    vx_3d = data["vx"].astype(np.float64)
    vy_3d = data["vy"].astype(np.float64)
    vz_3d = data["vz"].astype(np.float64)

    if vx_3d.ndim != 3:
        raise ValueError(f"Expected 3D arrays in velocity_field.npz, got shape {vx_3d.shape}")
    if vy_3d.shape != vx_3d.shape or vz_3d.shape != vx_3d.shape:
        raise ValueError("vx, vy, vz must all have the same shape")

    nx, ny, nz = vx_3d.shape  # Note: Stage 4 stores as (nx, ny, nz)

    # --- Determine slice ---
    ax = config.slice_axis.lower()
    if ax not in ("x", "y", "z"):
        raise ValueError(f"slice_axis must be 'x', 'y', or 'z', got '{ax}'")

    if ax == "z":
        dim_size = nz
        mid = nz // 2
        sidx = config.slice_index if config.slice_index is not None else mid
        _check_slice_index(sidx, dim_size, "z")
        # Slice: take vx[:, :, sidx] → shape (nx, ny) — treat as (ny, nx) for bridge
        u_2d = vx_3d[:, :, sidx].T   # (ny, nx)  [transpose so rows=y, cols=x]
        v_2d = vy_3d[:, :, sidx].T
        scalar_2d = vz_3d[:, :, sidx].T if config.include_axial_as_scalar else None
        grid_ny, grid_nx = u_2d.shape
    elif ax == "y":
        dim_size = ny
        mid = ny // 2
        sidx = config.slice_index if config.slice_index is not None else mid
        _check_slice_index(sidx, dim_size, "y")
        u_2d = vx_3d[:, sidx, :].T   # (nz, nx)
        v_2d = vz_3d[:, sidx, :].T   # use vz as v in xz-plane
        scalar_2d = vy_3d[:, sidx, :].T if config.include_axial_as_scalar else None
        grid_ny, grid_nx = u_2d.shape
    elif ax == "x":
        dim_size = nx
        mid = nx // 2
        sidx = config.slice_index if config.slice_index is not None else mid
        _check_slice_index(sidx, dim_size, "x")
        u_2d = vy_3d[sidx, :, :].T   # (nz, ny)
        v_2d = vz_3d[sidx, :, :].T
        scalar_2d = vx_3d[sidx, :, :].T if config.include_axial_as_scalar else None
        grid_ny, grid_nx = u_2d.shape

    # --- Solid detection from velocity threshold ---
    mag_2d = np.sqrt(u_2d**2 + v_2d**2 + (scalar_2d**2 if scalar_2d is not None else 0))
    max_mag = mag_2d.max()
    threshold = config.solid_threshold_fraction * max_mag if max_mag > 0 else 0.0
    solid_mask = (mag_2d < threshold).astype(np.uint8)

    # --- Sort out NaN from solid region (Stage 4 uses 0-velocity not NaN) ---
    # u/v should have no NaN; any NaN means data corruption
    if np.isnan(u_2d).any() or np.isnan(v_2d).any():
        raise ValueError(
            "NaN found in sliced velocity field. Data may be corrupted. "
            "Stage 4 should use zero-velocity for solid cells, not NaN."
        )

    # --- Build provenance from stage4 provenance.json ---
    provenance = _parse_stage4_provenance(prov_path, grid_nx, grid_ny, ax, sidx)

    return FieldBundle(
        u=u_2d,
        v=v_2d,
        solid_mask=solid_mask,
        scalar=scalar_2d,
        provenance=provenance,
        input_path=str(vel_path),
        input_sha256=input_sha256,
    )


def _parse_stage4_provenance(
    prov_path: Path,
    grid_nx: int,
    grid_ny: int,
    slice_axis: str,
    slice_index: int,
) -> FieldProvenance:
    """Parse coldplate-design-engine Stage 4 provenance.json into a FieldProvenance.

    Maps stage4 fields to bridge field contract provenance schema.
    All field name mappings are explicit — no assumptions about semantics.
    """
    with open(prov_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    git_sha = raw.get("git_sha")
    timestamp = raw.get("timestamp")
    candidate_id = raw.get("candidate_id", "unknown")
    stage = raw.get("stage", "stage4_sim")

    # Extract voxel_size_mm from simulation grid if present
    sim = raw.get("simulation", {})
    grid_info = sim.get("grid", {})
    voxel_size_mm = grid_info.get("voxel_size_mm")

    # Provenance preprocessing steps for the slicing operation
    preprocessing = [
        f"stage4_velocity_field_slice:axis={slice_axis},index={slice_index}",
        "solid_detection:method=velocity_magnitude_threshold",
        "axes_transpose:stage4_nx_ny_nz_to_bridge_ny_nx",
    ]

    return FieldProvenance(
        schema_version="1.0.0",
        source_repo="coldplate-design-engine",
        source_stage=stage,
        source_artifact=f"{candidate_id}/velocity_field.npz",
        source_commit=git_sha,
        preprocessing=preprocessing,
        grid_nx=grid_nx,
        grid_ny=grid_ny,
        grid_dx=voxel_size_mm,
        grid_dy=voxel_size_mm,
        field_frozen_at=timestamp,
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_slice_index(sidx: int, dim_size: int, axis: str) -> None:
    if not (0 <= sidx < dim_size):
        raise ValueError(
            f"slice_index={sidx} out of range for axis '{axis}' with size {dim_size}. "
            f"Valid range: [0, {dim_size - 1}]"
        )
