# docs/UNCERTAINTIES.md
# Open Uncertainties — coldplate-topobridge
# Version: 1.0.0
# Date: 2026-03-10

Every uncertainty listed here is tagged with its tier from `CLAIM_TIERS.md`.

---

## 1. Structural Uncertainties (about the bridge design)

### U-001: No native vector field in coldplate-design-engine Stage 1
**Tier:** NOT_PROVEN

**Description:** Stage 1 of coldplate-design-engine produces binary solid masks only.
It does not produce u/v velocity fields. The bridge Stage 1 therefore requires externally
provided vector fields (e.g., from CFD post-processing, or synthetic test fields).

**Impact:** The bridge cannot be run on coldplate-engine Stage 1 alone. It needs a CFD
step (Stage 4+) or synthetic fields.

**Resolution path:** Audit coldplate-design-engine Stage 4 output format; if stable .npy
files are produced, write a Stage 4 adapter.

**Escalation trigger:** If Stage 4 outputs require importing engine internals, escalate.

---

### U-002: Solid mask convention inversion
**Tier:** IMPLEMENTED

**Description:** coldplate-design-engine Stage 1 uses convention 1=fluid, 0=solid.
The bridge field contract uses 1=solid, 0=fluid. The inversion is explicit in the loader.

**Impact:** Any consumer of bridge-processed masks must be aware of this inversion.

**Resolution:** Documented in `docs/FIELD_CONTRACT.md` §2.2. Bridge loader applies inversion.
No action needed unless convention changes in either parent repo.

---

### U-003: Bridge angle field ≠ spin angle field
**Tier:** NOT_PROVEN

**Description:** `theta_bridge = atan2(v, u)` is computed identically to `theta = atan2(Sy, Sx)`
in topostream_stage0_specs. However, the semantic domains are entirely different:
- topostream θ: orientation of a magnetic/clock spin on a lattice, with periodic boundary conditions
- bridge θ: orientation of a 2D velocity or flow-proxy vector, with open (non-periodic) boundaries

**Impact:** Any attempt to run topostream vortex extraction on bridge angle fields would produce
numbers but those numbers would NOT be physical spin vortex charges.

**Resolution:** DO NOT apply topostream vortex extraction to bridge fields (Stage 1).
Any future bridge-to-topostream adapter MUST document the inversion/mapping with explicit
validation controls before any such output is labeled.

**Escalation trigger:** If any code path in the bridge imports topostream extraction code
and uses its output as a vortex charge, escalate immediately.

---

## 2. Numerical Uncertainties (about computed values)

### U-004: Low-signal mask threshold is arbitrary
**Tier:** HYPOTHESIS

**Description:** The bridge flags pixels where `|u|² + |v|² < threshold` as low-signal.
The current threshold (0.01 of max magnitude) is an engineering choice, not a
physically derived value.

**Impact:** The low-signal fraction reported in `summary.json` depends on threshold.
Comparisons between runs with different thresholds are not valid.

**Resolution path:** Threshold is recorded in every `field_contract.json` and `summary.json`.
If threshold sensitivity is needed, add a sweep mode in a future run.

---

### U-005: Bridge descriptors are not normalized across field scales
**Tier:** HYPOTHESIS

**Description:** The bridge signature descriptors (angle variance, gradient magnitude statistics)
depend on the magnitude of u and v. If two fields are produced from the same geometry
at different flow speeds, descriptors will differ even if the normalized flow pattern is identical.

**Impact:** Cross-field comparison requires normalization. Stage 1 does not normalize.

**Resolution:** Documented. Future work: add optional magnitude normalization flag.

---

## 3. Semantic Uncertainties (about meaning)

### U-006: Does bridge angle variance predict flow complexity?
**Tier:** HYPOTHESIS

**Description:** High spatial variance in `theta_bridge` might indicate geometrically complex
flow patterns (turns, recirculation zones) rather than uniform flow. This is a geometric intuition,
not a physically validated claim.

**Evidence basis:**
- In straight-channel geometry: flow direction is uniform → low theta variance (expected)
- In pin-fin geometry: flow is deflected around pins → higher theta variance (expected, NOT measured)

**What has NOT been done:**
- No CFD validation of this correspondence
- No comparison of bridge descriptors to any real flow measurement
- No comparison to coldplate metric outputs (e.g., tortuosity_proxy)

---

### U-007: Is there any useful correspondence between bridge signatures and TopoStream tokens?
**Tier:** NOT_PROVEN

**Description:** This is the central open question of the topobridge project.

**Current status:** No correspondence has been established, measured, or claimed.
TopoStream tokens carry spin-lattice physical meaning (temperature, periodic BCs).
Bridge signatures carry CFD-like geometric meaning (open BCs, real-space flow).

**What would be needed to investigate (NOT done in Stage 1):**
1. A field from a geometry that produces topological features at known positions
2. A method to map bridge signature peaks to candidate "event" locations
3. A way to compare event locations to any observable in coldplate behavior
4. Validation against experiment or high-fidelity simulation

**Escalation condition:** If anyone attempts to claim this correspondence is established,
that claim must be rejected and documented as NOT_PROVEN.

---

## 4. Infrastructure Uncertainties

### U-008: jsonschema validation is the only enforcement point
**Tier:** IMPLEMENTED

**Description:** Bridge output schemas are validated with jsonschema at runtime.
There is no compile-time type enforcement beyond Python type hints.

**Impact:** Schema drift between schema files and code is possible.

**Resolution:** Schema tests in `tests/test_field_contract.py` catch drift at test time.

---

## Summary Table

| ID | Title | Tier | Resolution Status |
|---|---|---|---|
| U-001 | No native vector field in Stage 1 | NOT_PROVEN | **Partially resolved** — Stage 4 wired |
| U-002 | Solid mask convention inversion | IMPLEMENTED | Resolved, documented |
| U-003 | Bridge angle ≠ spin angle | NOT_PROVEN | Guardrails enforced |
| U-004 | Low-signal threshold is arbitrary | HYPOTHESIS | Threshold recorded in output |
| U-005 | Descriptors not normalized | HYPOTHESIS | Documented |
| U-006 | Angle variance predicts flow complexity? | HYPOTHESIS | Not tested |
| U-007 | Bridge–TopoStream correspondence? | NOT_PROVEN | Explicitly not claimed |
| U-008 | jsonschema is only enforcement | IMPLEMENTED | Tests added |
| U-009 | 3D→2D slice choice is arbitrary | NOT_PROVEN | New — Stage 4 adapter |
| U-010 | Solid detection threshold calibration | NOT_PROVEN | New — Stage 4 adapter |
| U-011 | Darcy velocity semantics for bridge angle | NOT_PROVEN | New — Stage 4 adapter |
| U-012 | theta_std slice-sensitivity | NOT_PROVEN | New — Stage 2 comparison |
| U-013 | Missing upstream control artifacts | NOT_PROVEN | **Resolved** — artifacts emitted |
| U-014 | atan2(near-zero, near-zero) produces spurious theta_std | NOT_PROVEN | G5 criterion blocked — reformulation required |

---

## 5. Stage 4 Adapter Uncertainties (added 2026-03-10)

### U-009: 3D→2D slice choice is arbitrary
**Tier:** NOT_PROVEN

**Description:** Stage 4 velocity field is 3D (nx, ny, nz). The bridge requires 2D. The adapter
takes a cross-sectional slice at a specified z-index (default: midpoint nz//2). No physical or
mathematical argument is provided for why this slice is more representative than any other.

**Evidence:** z=10 vs z=30 slices of the full artifact produce different JSONL hashes and
theta_std values. These differences are NOT documented as physically meaningful.

**Impact:** Bridge signatures from different z-slices of the same geometry are NOT directly
comparable without explicit slice-index matching.

**Resolution path:** Document `slice_index` in provenance (done). For future work, test
slice sensitivity across all z-levels and document variance.

**NOT claimed:** That mid-slice is "the correct" physically representative cross-section.

---

### U-010: Solid detection from velocity threshold is not perfectly calibrated
**Tier:** NOT_PROVEN

**Description:** Stage 4 does not emit a solid mask array in its artifacts. Solid cells are
detected by thresholding velocity magnitude: `solid = (|v| < 1e-3 × max(|v|))`.

At 3D level: matches provenance porosity (55601/125000 = 0.4448 solid = 1 - 0.555192). ✓
For individual 2D z-slices: solid fraction varies ~1–2% by z-index.
Individual pixel assignments may be incorrect near geometry boundaries.

**Resolution path:** The ideal fix is for Stage 4 to emit `solid_mask.npz` separately.
This requires an upstream change — NOT done (no parent repo editing allowed).
Until then, threshold detection remains the only approach from emitted artifacts.

**NOT claimed:** That `solid_mask[i,j]` is accurate for every pixel in every 2D cross-section.

---

### U-011: Darcy velocity is not point-wise physical velocity
**Tier:** NOT_PROVEN

**Description:** Stage 4 uses Darcy's law: `v = -(k/μ) ∇p`. This is a simplified porous-medium
approximation, not a Navier-Stokes solver. Darcy velocity is a volume-averaged, smeared quantity.

**Impact:** `theta_bridge = atan2(vy, vx)` on Darcy velocity encodes the direction of local
Darcy flux. This is NOT equivalent to the streamline direction from resolved Navier-Stokes.
Transverse components (vx, vy) may be partially numerical artifacts of the Darcy model applied
to a 3D porous geometry.

**Escalation trigger:** If any claim is made that bridge signatures from Stage 4 Darcy velocity
correspond to physical flow streamlines or resolved CFD, escalate and reject.

---

### U-012: metric difference between candidates is smaller than slice-level noise
**Tier:** NOT_PROVEN
**Updated:** 2026-03-10 (Metric Usefulness Audit)

**Description:** In a quantitative slice-sweep audit across z={10,15,20,25,30,35,40}, the variance of metrics like `theta_std` within a single candidate (due to slice choice) was found to be ~20x larger than the mean difference between candidate_01 and candidate_02. The signal-to-noise ratio is < 0.2.

This demonstrates that for the tested TPMS manifolds, a single 2D slice is not a reliable structural proxy for holistic 3D differences. The metrics do not monotonically separate the candidates across slices.

**Impact:** The bridge's output signatures and summaries function correctly as software artifacts (they are deterministic per-slice), but they are strictly descriptor metadata for a *specific* cross-section.

**Resolution:** Documented in `METRIC_USEFULNESS_REPORT.md`. We continue using these metrics ONLY as programmatic descriptors (e.g. for downstream agents to verify determinism) but NOT as scientific 3D performance proxies.

**NOT claimed:** That bridge metrics can be used to rank 3D geometries.

---

### U-013: Missing upstream Stage 4 control artifacts
**Tier:** NOT_PROVEN
**Added:** 2026-03-10
**Updated:** 2026-03-10 — RESOLVED

**Description:** The bridge VALIDATED tier required G5 and G6 upstream control artifacts.

**Resolution:** Both artifacts were generated by `coldplate-design-engine/scripts/emit_stage4_controls.py` and committed (SHA `6588545`):
- `results/stage4_sim_full/baseline_uniform_channel_ctrl/` (G5 negative control)
- `results/stage4_sim_full/baseline_single_obstruction_ctrl/` (G6 positive control)

Both contain `velocity_field.npz` (keys: vx, vy, vz, shape (50,50,50), float64) and `provenance.json`. Bridge can ingest both without schema changes.

**Residual:** G5 criterion must be reformulated — see U-014.

---

### U-014: atan2(near-zero, near-zero) produces spurious theta_std in all-fluid domains
**Tier:** NOT_PROVEN
**Added:** 2026-03-10

**Description:** When a Darcy velocity field has zero transverse components (vx=vy≈0 at machine epsilon, ~1e-9 m/s) but non-zero axial component (vz~200 m/s), the bridge computes `theta_bridge = atan2(vy, vx)`. This produces arbitrary angles from floating-point sign-bit patterns on the near-zero values, resulting in `theta_std ≈ π/2` even though the true physics implies perfectly uniform flow.

**Observed:** uniform_channel_ctrl at z=25: vx_max=4.3e-9 m/s, vy_max=4.1e-9 m/s. Bridge reports `theta_std = 1.51 rad`. The current low_signal_threshold (0.01 × max(|vx|,|vy|)) does not catch this because max(|vx|,|vy|) is also ~4e-9, so threshold = ~4e-11, which near-zero pixels still exceed.

**Impact:** The G5 acceptance criterion `theta_std < 0.05` cannot be satisfied for the uniform channel Darcy artifact. G5 must be reformulated.

**Reformulated G5 criterion (correct):**
```
G5_pass: max(|vx|,|vy|) / mean(|vz|) < 1e-5   (transverse-to-axial ratio)
```
For the uniform channel: 4.3e-9 / 204.08 = 2.1e-11 → passes.

**Resolution path:** Add a `transverse_ratio` field to `summary.json`, or add a separate gate test that reads from `velocity_field.npz` directly. G5 does NOT need a theta_std threshold.

**NOT claimed:** That the atan2 ambiguity invalidates the bridge for real geometries with non-zero transverse flow.
