# docs/FIELD_CONTRACT.md
# Field Contract — coldplate-topobridge
# Version: 1.0.0
# Date: 2026-03-10

---

## 1. Purpose

This document defines the bridge input contract for a **frozen 2D field bundle**.
Any artifact submitted to the bridge MUST conform to this contract.

This is a bridge-LOCAL contract. It does NOT depend on topostream_stage0_specs schemas.
It does NOT depend on coldplate-design-engine internals.

---

## 2. Required Array Contents

### 2.1 Primary Vector Field

| Key | Shape | Dtype | Units | Required | Notes |
|---|---|---|---|---|---|
| `u` | `(ny, nx)` | float64 | dimensionless | YES | x-component of 2D vector field |
| `v` | `(ny, nx)` | float64 | dimensionless | YES | y-component of 2D vector field |

**Conventions:**
- x-axis: j (column index), increasing left-to-right
- y-axis: i (row index), increasing top-to-bottom
- Both arrays must have the same shape (ny, nx)
- NaN is NOT permitted in `u` or `v` (use `solid_mask` to exclude solid regions)

**Important (IMPLEMENTED, NOT interpreted physically):**
The bridge computes `theta_bridge = atan2(v, u)` purely as a geometric transform.
This is NOT a spin angle field. DO NOT interpret as XY model spin orientation.

### 2.2 Solid Mask

| Key | Shape | Dtype | Values | Required | Notes |
|---|---|---|---|---|---|
| `solid_mask` | `(ny, nx)` | uint8 | 0=fluid, 1=solid | YES | Must match shape of u and v |

**Convention note:** This is the INVERSE of `coldplate-design-engine` Stage 1 convention,
which uses 1=fluid, 0=solid. The bridge uses 1=solid, 0=fluid to match physical intuition.
When loading Stage 1 masks: `solid_mask = 1 - stage1_mask`.

### 2.3 Optional Scalar Field

| Key | Shape | Dtype | Units | Required | Notes |
|---|---|---|---|---|---|
| `scalar` | `(ny, nx)` | float64 | domain-specific | NO | Pressure, temperature, or other scalar |

If provided, the scalar field is recorded in provenance but NOT used in bridge signature computation (Stage 1).

---

## 3. Required Sidecar Metadata (provenance)

Every field bundle MUST have a provenance sidecar, either:
- As a `.meta.json` file alongside the `.npz`, OR
- As an embedded `provenance` key in the `.npz` (via `np.savez`)

### 3.1 Required Provenance Fields

```json
{
  "schema_version": "1.0.0",
  "source_repo": "coldplate-design-engine",
  "source_stage": "stage1_2d",
  "source_artifact": "masks/run_001/candidate_01_diamond_2d.npy",
  "source_commit": "abc123def456",
  "preprocessing": ["mask_to_field_not_implemented"],
  "grid_nx": 64,
  "grid_ny": 64,
  "grid_dx": 0.001,
  "grid_dy": 0.001,
  "field_frozen_at": "2026-03-10T17:00:00Z"
}
```

### 3.2 Provenance Field Definitions

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | YES | Always "1.0.0" for Stage 1 |
| `source_repo` | string | YES | Name of originating repository |
| `source_stage` | string | YES | Pipeline stage that produced the field |
| `source_artifact` | string | YES | Relative path to original artifact within source repo |
| `source_commit` | string | NO | Git SHA if available; null if unknown |
| `preprocessing` | array[string] | YES | List of transformations applied before bridge ingestion |
| `grid_nx` | int | YES | Number of columns |
| `grid_ny` | int | YES | Number of rows |
| `grid_dx` | float | NO | Physical cell width (meters); null if unknown |
| `grid_dy` | float | NO | Physical cell height (meters); null if unknown |
| `field_frozen_at` | string | YES | ISO 8601 timestamp when artifact was frozen |

---

## 4. File Format

Preferred: NumPy `.npz` archive containing all required arrays.
Alternative: separate `.npy` per array + `.meta.json` sidecar.

**Naming:** No constraint on input file name. Output naming follows `ARTIFACT_RULES.md`.

---

## 5. Validation Rules

The bridge loader (`src/topobridge/adapters/coldplate_field_loader.py`) enforces:

1. **Shape consistency:** `u.shape == v.shape == solid_mask.shape`
2. **Dtype:** u and v must be float64 (or float32, which is auto-promoted)
3. **No NaN in u, v:** NaN is rejected; raise `ValueError`
4. **solid_mask values:** Must be 0 or 1 only; raise `ValueError` otherwise
5. **Provenance required:** Missing provenance metadata raises `ValueError`
6. **SHA-256 hash:** Computed from raw bytes of input file; recorded in output

---

## 6. Known Gaps (HYPOTHESIS / NOT_PROVEN)

- HYPOTHESIS: Stage 4 flow-simulation outputs from coldplate-design-engine may be
  convertible to bridge field bundles. This requires a future audit of Stage 4 output format.
- NOT_PROVEN: The bridge angle field `theta_bridge = atan2(v, u)` has any correspondence
  with topological features in the downstream domain (topostream_stage0_specs).
- NOT_PROVEN: Any metric derived from the bridge signature stream predicts real fluid behavior.

---

## 7. Contract Version

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-03-10 | Initial contract — u, v, solid_mask, optional scalar |
