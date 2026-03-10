"""Bridge field loader — reads frozen 2D field artifacts and validates provenance.

IMPLEMENTED: reads .npz artifacts, computes hashes, records provenance.
NOT_PROVEN: any physical interpretation of loaded fields.

This module does NOT import coldplate-design-engine internals at runtime.
All coldplate-engine artifact schemas are reproduced locally via docs/FIELD_CONTRACT.md.
"""

import hashlib
import json
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import numpy as np


# --- Data structures ---

@dataclass
class FieldProvenance:
    """Provenance metadata for a frozen field bundle.

    All fields here correspond to docs/FIELD_CONTRACT.md §3.1.
    """
    schema_version: str
    source_repo: str
    source_stage: str
    source_artifact: str
    preprocessing: list
    grid_nx: int
    grid_ny: int
    source_commit: Optional[str] = None
    grid_dx: Optional[float] = None
    grid_dy: Optional[float] = None
    field_frozen_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FieldBundle:
    """Validated 2D field bundle ready for bridge encoding.

    Attributes:
        u: x-component of vector field (ny, nx), float64
        v: y-component of vector field (ny, nx), float64
        solid_mask: 1=solid, 0=fluid (ny, nx), uint8
        scalar: optional scalar field (ny, nx) or None
        provenance: metadata from sidecar
        input_path: path to source .npz file
        input_sha256: SHA-256 of source file bytes
    """
    u: np.ndarray
    v: np.ndarray
    solid_mask: np.ndarray
    provenance: FieldProvenance
    input_path: str
    input_sha256: str
    scalar: Optional[np.ndarray] = None

    @property
    def shape(self) -> Tuple[int, int]:
        return self.u.shape  # (ny, nx)


# --- Public API ---

def load_field_bundle(
    artifact_path: str,
    sidecar_path: Optional[str] = None,
    low_signal_threshold_fraction: float = 0.01,
) -> FieldBundle:
    """Load and validate a frozen 2D field bundle from .npz file.

    Args:
        artifact_path: Path to .npz file containing u, v, solid_mask, optional scalar.
        sidecar_path: Path to .meta.json sidecar. If None, looks for
            {artifact_stem}.meta.json alongside the artifact.
        low_signal_threshold_fraction: Not used in loading (for encoder). Reserved.

    Returns:
        Validated FieldBundle.

    Raises:
        ValueError: If any required field is missing, shapes mismatch, or
            provenance metadata is absent.
        FileNotFoundError: If artifact or sidecar not found.
    """
    artifact_path = Path(artifact_path).resolve()
    if not artifact_path.exists():
        raise FileNotFoundError(f"Artifact not found: {artifact_path}")

    # Compute file hash BEFORE loading (hash raw bytes)
    sha256 = _sha256_file(artifact_path)

    # Load arrays
    data = np.load(str(artifact_path), allow_pickle=False)

    # Validate required keys
    for required_key in ("u", "v", "solid_mask"):
        if required_key not in data:
            raise ValueError(
                f"Required key '{required_key}' missing from {artifact_path}. "
                f"Available keys: {list(data.keys())}"
            )

    u = _coerce_float64(data["u"], "u")
    v = _coerce_float64(data["v"], "v")
    solid_mask = _coerce_uint8(data["solid_mask"], "solid_mask")
    scalar = _coerce_float64(data["scalar"], "scalar") if "scalar" in data else None

    # Shape validation
    if u.ndim != 2:
        raise ValueError(f"'u' must be 2D, got shape {u.shape}")
    if v.shape != u.shape:
        raise ValueError(
            f"'v' shape {v.shape} does not match 'u' shape {u.shape}"
        )
    if solid_mask.shape != u.shape:
        raise ValueError(
            f"'solid_mask' shape {solid_mask.shape} does not match 'u' shape {u.shape}"
        )
    if scalar is not None and scalar.shape != u.shape:
        raise ValueError(
            f"'scalar' shape {scalar.shape} does not match 'u' shape {u.shape}"
        )

    # NaN check
    if np.isnan(u).any():
        raise ValueError("'u' contains NaN. Use solid_mask to exclude solid regions.")
    if np.isnan(v).any():
        raise ValueError("'v' contains NaN. Use solid_mask to exclude solid regions.")

    # solid_mask value check
    unique_vals = np.unique(solid_mask)
    if not set(unique_vals.tolist()).issubset({0, 1}):
        raise ValueError(
            f"'solid_mask' must contain only 0 and 1. Got: {unique_vals}"
        )

    # Load provenance sidecar
    provenance = _load_provenance(artifact_path, sidecar_path, u.shape)

    return FieldBundle(
        u=u,
        v=v,
        solid_mask=solid_mask,
        scalar=scalar,
        provenance=provenance,
        input_path=str(artifact_path),
        input_sha256=sha256,
    )


# --- Internal helpers ---

def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _coerce_float64(arr: np.ndarray, name: str) -> np.ndarray:
    if arr.dtype in (np.float32, np.float64):
        return arr.astype(np.float64)
    raise ValueError(
        f"'{name}' must be float32 or float64, got {arr.dtype}"
    )


def _coerce_uint8(arr: np.ndarray, name: str) -> np.ndarray:
    if arr.dtype in (np.uint8, np.int32, np.int64, np.bool_):
        return arr.astype(np.uint8)
    raise ValueError(
        f"'{name}' must be uint8, int, or bool, got {arr.dtype}"
    )


def _load_provenance(
    artifact_path: Path,
    sidecar_path: Optional[str],
    array_shape: Tuple[int, int],
) -> FieldProvenance:
    """Load and validate provenance from sidecar JSON."""

    # Locate sidecar
    if sidecar_path is not None:
        sidecar = Path(sidecar_path)
    else:
        sidecar = artifact_path.with_suffix("").with_suffix(".meta.json")
        if not sidecar.exists():
            # Also try replacing .npz directly
            sidecar = artifact_path.with_suffix(".meta.json")

    if not sidecar.exists():
        raise ValueError(
            f"Provenance sidecar not found. Expected: {sidecar}\n"
            f"Create a .meta.json following docs/FIELD_CONTRACT.md §3.1"
        )

    with open(sidecar, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Validate required fields
    required = [
        "schema_version", "source_repo", "source_stage",
        "source_artifact", "preprocessing", "grid_nx", "grid_ny",
        "field_frozen_at",
    ]
    missing = [k for k in required if k not in meta]
    if missing:
        raise ValueError(
            f"Provenance sidecar missing required fields: {missing}"
        )

    # Cross-check grid shape
    ny, nx = array_shape
    if meta["grid_nx"] != nx or meta["grid_ny"] != ny:
        raise ValueError(
            f"Provenance grid ({meta['grid_ny']}, {meta['grid_nx']}) "
            f"does not match array shape ({ny}, {nx})"
        )

    return FieldProvenance(
        schema_version=meta["schema_version"],
        source_repo=meta["source_repo"],
        source_stage=meta["source_stage"],
        source_artifact=meta["source_artifact"],
        source_commit=meta.get("source_commit"),
        preprocessing=meta.get("preprocessing", []),
        grid_nx=meta["grid_nx"],
        grid_ny=meta["grid_ny"],
        grid_dx=meta.get("grid_dx"),
        grid_dy=meta.get("grid_dy"),
        field_frozen_at=meta.get("field_frozen_at"),
    )


def get_bridge_git_sha() -> Optional[str]:
    """Get current git SHA of the bridge repo (not parent repos)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(Path(__file__).parent.parent.parent.parent),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None
