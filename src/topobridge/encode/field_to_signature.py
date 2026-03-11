"""Bridge-local encoder: field bundle → signature stream.

IMPLEMENTED: theta = atan2(v, u), low-signal mask, bridge-local descriptors.
NOT_PROVEN: any physical or topological interpretation of outputs.

DO NOT label outputs with TopoStream token_type fields.
DO NOT compute winding numbers or vortex charges.
See GUARDRAILS.md and docs/UNCERTAINTIES.md for what is and is not claimed.
"""

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any

import numpy as np

from topobridge.adapters.coldplate_field_loader import FieldBundle


# Default low-signal threshold as fraction of max magnitude
_DEFAULT_LOW_SIGNAL_FRACTION = 0.01

# Absolute floor: if max transverse magnitude is below this value, the
# angle field is undefined because atan2(~0, ~0) produces arbitrary
# sign-bit angles at floating-point machine epsilon.
# For Darcy solvers this is ~1e-9 m/s vs axial ~200 m/s — undeniably
# noise, not signal. Threshold is 1e-6 m/s (7 decades above typical
# Darcy noise, still 8 decades below any meaningful transverse flow).
_TRANSVERSE_ABSOLUTE_FLOOR = 1e-6  # m/s (or dimensionless — same field units)


@dataclass
class SignatureRecord:
    """One spatial cell in the bridge signature stream.

    Fields correspond exactly to bridge_signature_stream.schema.json.
    """
    schema_version: str
    bridge_schema_id: str
    record_id: str
    i: int
    j: int
    is_solid: bool
    is_low_signal: bool
    theta_bridge: Optional[float]  # None if solid or low-signal
    magnitude: float
    scalar: Optional[float]  # None if no scalar provided

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EncoderOutput:
    """Complete output from field_to_signatures()."""
    records: List[SignatureRecord]
    theta_field: np.ndarray         # (ny, nx), nan where solid or low-signal
    low_signal_mask: np.ndarray     # (ny, nx) bool
    magnitude_field: np.ndarray     # (ny, nx) float64
    low_signal_threshold: float
    summary: Dict[str, Any]


def field_to_signatures(
    bundle: FieldBundle,
    low_signal_threshold_fraction: float = _DEFAULT_LOW_SIGNAL_FRACTION,
) -> EncoderOutput:
    """Encode a validated FieldBundle into a bridge-local signature stream.

    Steps:
    1. Compute vector magnitude at every pixel
    2. Determine low-signal mask: fluid pixels where magnitude < threshold
    3. Compute theta_bridge = atan2(v, u) for non-solid, non-low-signal pixels
    4. Generate deterministic per-pixel records
    5. Compute summary statistics

    Args:
        bundle: Validated FieldBundle from load_field_bundle().
        low_signal_threshold_fraction: Pixels with magnitude < this fraction of
            max magnitude are flagged as low-signal. Default 0.01 (1%).

    Returns:
        EncoderOutput with records, fields, and summary.

    Notes (GUARDRAILS):
    - theta_bridge is a geometric angle. It is NOT a spin orientation.
    - Records do NOT contain 'charge' or 'token_type' fields.
    - low_signal_mask has no physical interpretation beyond "small vector".
    """
    ny, nx = bundle.shape
    u = bundle.u
    v = bundle.v
    solid_mask = bundle.solid_mask.astype(bool)  # True = solid
    scalar = bundle.scalar

    # Step 1: Magnitude
    magnitude_field = np.sqrt(u**2 + v**2)

    # Step 2: Low-signal threshold
    # Primary: relative threshold = fraction of max transverse magnitude.
    # Secondary: absolute floor — if max transverse magnitude is below the
    #   absolute floor, atan2(v, u) is undefined (arbitrary sign-bit angles
    #   at machine epsilon). In that case ALL fluid pixels are low-signal.
    #   This correctly handles all-fluid Darcy fields where vx≈vy≈0.
    max_mag = magnitude_field.max()
    if max_mag == 0.0 or max_mag < _TRANSVERSE_ABSOLUTE_FLOOR:
        # Entire transverse field is at or below machine-epsilon noise.
        # Mark all non-solid pixels as low-signal.
        threshold = max_mag  # record the actual max for provenance
        low_signal_mask = (~solid_mask)  # all fluid pixels
    else:
        threshold = low_signal_threshold_fraction * max_mag
        # Low-signal: fluid pixels only (solid already excluded from analysis)
        low_signal_mask = (~solid_mask) & (magnitude_field < threshold)

    # Step 3: Theta field
    # Only compute for fluid, valid-signal pixels
    active_mask = (~solid_mask) & (~low_signal_mask)
    theta_field = np.full((ny, nx), np.nan, dtype=np.float64)
    theta_field[active_mask] = np.arctan2(v[active_mask], u[active_mask])

    # Step 4: Generate records
    # Use deterministic record IDs: sha256(input_hash + ":" + i + ":" + j)[:16]
    input_sha = bundle.input_sha256
    records: List[SignatureRecord] = []

    for i in range(ny):
        for j in range(nx):
            rec_id = _deterministic_record_id(input_sha, i, j)
            is_solid = bool(solid_mask[i, j])
            is_low_sig = bool(low_signal_mask[i, j])
            mag = float(magnitude_field[i, j])

            if is_solid or is_low_sig:
                theta_val = None
            else:
                theta_val = float(theta_field[i, j])

            sc_val = float(scalar[i, j]) if scalar is not None else None

            records.append(SignatureRecord(
                schema_version="1.0.0",
                bridge_schema_id="bridge_signature_stream",
                record_id=rec_id,
                i=i,
                j=j,
                is_solid=is_solid,
                is_low_signal=is_low_sig,
                theta_bridge=theta_val,
                magnitude=mag,
                scalar=sc_val,
            ))

    # Step 5: Summary statistics
    # Only computed over active (non-solid, non-low-signal) pixels
    active_indices = np.argwhere(active_mask)
    n_active = int(active_mask.sum())
    n_solid = int(solid_mask.sum())
    n_low_signal = int(low_signal_mask.sum())
    n_total = ny * nx

    if n_active > 0:
        active_thetas = theta_field[active_mask]
        theta_mean = float(np.mean(active_thetas))
        theta_std = float(np.std(active_thetas))
        theta_abs_mean = float(np.mean(np.abs(active_thetas)))

        active_mags = magnitude_field[active_mask]
        mag_mean = float(np.mean(active_mags))
        mag_std = float(np.std(active_mags))

        # Gradient of theta field (only over active region, central differences)
        # Signals spatial variability of flow direction. NOT a winding number.
        grad_i, grad_j = np.gradient(theta_field)
        # Use non-nan gradients only
        grad_mag = np.sqrt(grad_i**2 + grad_j**2)
        valid_grad = np.isfinite(grad_mag) & active_mask
        gradient_mean = float(np.mean(grad_mag[valid_grad])) if valid_grad.any() else 0.0
        gradient_max = float(np.max(grad_mag[valid_grad])) if valid_grad.any() else 0.0
    else:
        theta_mean = 0.0
        theta_std = 0.0
        theta_abs_mean = 0.0
        mag_mean = 0.0
        mag_std = 0.0
        gradient_mean = 0.0
        gradient_max = 0.0

    summary = {
        "schema_version": "1.0.0",
        "bridge_schema_id": "bridge_summary",
        "input_sha256": bundle.input_sha256,
        "source_repo": bundle.provenance.source_repo,
        "source_stage": bundle.provenance.source_stage,
        "grid_shape": [ny, nx],
        "n_total_pixels": n_total,
        "n_solid_pixels": n_solid,
        "n_low_signal_pixels": n_low_signal,
        "n_active_pixels": n_active,
        "solid_fraction": n_solid / n_total,
        "low_signal_fraction": n_low_signal / (n_total - n_solid) if (n_total - n_solid) > 0 else 0.0,
        "active_fraction": n_active / n_total,
        "low_signal_threshold": float(threshold),
        "theta_stats": {
            "mean_rad": theta_mean,
            "std_rad": theta_std,
            "abs_mean_rad": theta_abs_mean,
        },
        "magnitude_stats": {
            "mean": mag_mean,
            "std": mag_std,
            "global_max": float(max_mag),
        },
        "gradient_stats": {
            "mean_grad_mag": gradient_mean,
            "max_grad_mag": gradient_max,
            "NOTE": (
                "Gradient of theta_bridge over active pixels only. "
                "NOT a winding number or vortex charge."
            ),
        },
        "has_scalar": bundle.scalar is not None,
        "claim_tier": "IMPLEMENTED",
        "NOT_PROVEN": [
            "Any physical interpretation of bridge signatures",
            "Correspondence between gradient_stats and flow topology",
            "Equivalence with TopoStream token semantics",
        ],
        # Transverse-to-axial ratio: present only when scalar (axial) field is available.
        # This is the correct G5 gate criterion for Darcy fields with zero transverse flow.
        # Value < 1e-5 indicates the transverse field is at machine-epsilon noise level.
        # NOT a physical claim — a numerical validity check for atan2 inputs.
        "transverse_max_ratio": (
            float(max_mag / float(np.nanmean(np.abs(scalar)))) 
            if (bundle.scalar is not None and float(np.nanmean(np.abs(bundle.scalar))) > 0)
            else None
        ),
    }

    return EncoderOutput(
        records=records,
        theta_field=theta_field,
        low_signal_mask=low_signal_mask,
        magnitude_field=magnitude_field,
        low_signal_threshold=float(threshold),
        summary=summary,
    )


def _deterministic_record_id(input_sha256: str, i: int, j: int) -> str:
    """Compute deterministic 16-char hex ID for a spatial record."""
    h = hashlib.sha256(f"{input_sha256}:{i}:{j}".encode("utf-8"))
    return h.hexdigest()[:16]
