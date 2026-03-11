# Claim Audit Report
# Stronger-Claim Audit
# Date: 2026-03-11

## 1. Scope

This memo is an evidence-first review of what `coldplate-topobridge` can honestly claim from the current repo state.

- Scope is limited to existing repo artifacts, tests, and documentation.
- No new experiments were run.
- No parent repo files were edited.
- Goal: identify the strongest earned claim and the exact point where stronger claims stop being defensible.

## 2. Bottom Line

No stronger claim beyond the current protocol-scoped `VALIDATED` statement is honestly supportable from the existing repo evidence.

The strongest earned claim is:

> `coldplate-topobridge` is `VALIDATED` only for the current Stage 4 software/control protocol: on the current emitted Stage 4 velocity artifacts and current G5/G6 controls, it deterministically ingests a 3D Darcy velocity artifact, slices it to 2D, emits schema-valid bridge-local outputs, and distinguishes the tested inputs at the software-descriptor level. This does not establish 3D ranking, physical performance meaning, or TopoStream semantics.

## 3. Evidence Base Used

- `tests/test_real_comparison.py`
  - Real-artifact determinism, different-input sensitivity, and current G5/G6 control gates.
- `tests/test_stage4_adapter.py`
  - Read-only Stage 4 artifact ingestion, 3D-to-2D slicing, provenance capture, and validation on real artifacts.
- `tests/test_determinism.py`
  - Deterministic record IDs, record ordering, JSONL hash, and summary hash behavior.
- `artifacts/ctrl_uniform_channel_z25/summary.json`
  - `n_solid_pixels = 0`
  - `n_low_signal_pixels = 2500`
  - `n_active_pixels = 0`
  - `transverse_max_ratio = 2.284245727065394e-11`
- `artifacts/ctrl_single_obstruction_z25/summary.json`
  - `n_solid_pixels = 100`
  - `n_active_pixels = 2400`
  - `theta_stats.std_rad = 1.7948136777698005`
  - `transverse_max_ratio = 0.000751089026912623`
- `artifacts/real_comparison_metrics.json`
  - Fixed-policy z=25 candidate comparison
  - same `source_commit = 617eb6ab0619`
  - different `stream_hash_full`
  - different `n_solid`, `n_active`, and summary values
- `artifacts/slice_sweep_metrics.json`
  - Current 2D slice metrics vary materially with slice index for the tested TPMS pair.
- `docs/METRIC_USEFULNESS_REPORT.md`
  - Documents that current 2D slice metrics are not validated ranking proxies for the tested diamond TPMS pair.
- `docs/UNCERTAINTIES.md`
  - Explicit `NOT_PROVEN` limits on TopoStream correspondence, Darcy semantics, slice representativeness, and ranking use.

## 4. Claim Buckets

### SUPPORTED

| Claim | Exact evidence used | Audit result |
|---|---|---|
| The repo is `VALIDATED` only for the current Stage 4 software/control protocol. | `tests/test_real_comparison.py` current G5/G6 gate coverage; `tests/test_stage4_adapter.py`; `tests/test_determinism.py`; control summaries in `artifacts/ctrl_uniform_channel_z25/summary.json` and `artifacts/ctrl_single_obstruction_z25/summary.json`. | Supported. This is the strongest earned claim. |
| The bridge is deterministic for repeated runs on the same input. | `tests/test_determinism.py`; deterministic rerun tests in `tests/test_real_comparison.py`; identical hash checks in control tests. | Supported. This is software behavior only. |
| The current protocol can distinguish the tested null control, obstruction control, and real candidate inputs at the bridge-output level. | `artifacts/ctrl_uniform_channel_z25/summary.json`; `artifacts/ctrl_single_obstruction_z25/summary.json`; `artifacts/real_comparison_metrics.json`; gate tests in `tests/test_real_comparison.py`. | Supported. This establishes sensitivity to tested inputs, not scientific meaning. |
| The Stage 4 adapter can read current emitted `velocity_field.npz` and `provenance.json` artifacts and produce a 2D bridge bundle without importing parent-repo internals. | `tests/test_stage4_adapter.py`; current artifact bundles under `artifacts/`. | Supported. This is an ingestion-contract claim only. |

### SUPPORTED BUT NARROW

| Claim | Exact evidence used | Boundary |
|---|---|---|
| Candidate 01 and Candidate 02 produce different bridge outputs under the frozen comparison policy `axis=z`, `index=25`, `solid_threshold=1e-3`. | `artifacts/real_comparison_metrics.json`; `tests/test_real_comparison.py`. | Narrow to those two artifacts and that exact slice policy. It is not a ranking claim. |
| Current summary metrics are usable as bridge-local descriptors of a specific 2D slice. | Determinism and schema-validation tests; current summary artifacts; `docs/METRIC_USEFULNESS_REPORT.md`. | Narrow to per-slice software descriptors. No holistic 3D or physical interpretation is earned. |
| For the tested diamond TPMS pair, current 2D slice metrics are not validated ranking proxies. | `artifacts/slice_sweep_metrics.json`; `docs/METRIC_USEFULNESS_REPORT.md`; `docs/UNCERTAINTIES.md` U-012. | Narrow to the tested pair and current metric family. It does not prove that any future metric family will work. |
| `transverse_max_ratio` is a valid current numerical gate for the all-fluid control. | `artifacts/ctrl_uniform_channel_z25/summary.json`; G5 test coverage in `tests/test_real_comparison.py`; `docs/UNCERTAINTIES.md` U-014. | Narrow to the current encoder and current control protocol. It is a numerical sanity check, not a physics result. |

### UNSUPPORTED

| Claim | Why it fails | Evidence against / missing |
|---|---|---|
| Any bridge metric currently ranks 3D geometries or is slice-invariant. | Current slice sensitivity is larger than inter-candidate separation for the tested TPMS pair. | `artifacts/slice_sweep_metrics.json`; `docs/METRIC_USEFULNESS_REPORT.md`; `docs/UNCERTAINTIES.md` U-009 and U-012. |
| `theta_std`, `grad_mean`, or related metrics proxy hydraulic, thermal, structural, or overall coldplate performance. | No such validation exists in this repo. | `docs/METRIC_USEFULNESS_REPORT.md`; `docs/UNCERTAINTIES.md`; explicit `NOT_PROVEN` text in tests and summaries. |
| Bridge outputs describe the full 3D manifold rather than the selected 2D slice. | The adapter explicitly slices a 3D field to 2D, and slice choice changes the result. | `tests/test_stage4_adapter.py`; `tests/test_real_comparison.py`; `artifacts/slice_sweep_metrics.json`; `docs/UNCERTAINTIES.md` U-009. |
| Darcy `theta_bridge` is a resolved streamline or point-wise physical flow direction. | Stage 4 uses Darcy flux, not resolved Navier-Stokes velocity. | `docs/UNCERTAINTIES.md` U-011; adapter docstring and tests. |
| Bridge outputs have TopoStream semantic correspondence or compatibility. | No semantic mapping or validation exists. | `CLAIM_TIERS.md`; `docs/UNCERTAINTIES.md` U-003 and U-007; schema and encoder guardrails. |
| The current `VALIDATED` status can be extended to any broader protocol, other metrics, other slice policies, or any performance/ranking interpretation. | Current validation gates cover only the present software/control protocol. | `CLAIM_TIERS.md`; `docs/CHECKPOINT_STATUS.md`; current tests and artifacts. |

### SPECULATIVE

| Claim | Current evidence status | Source of the suggestion |
|---|---|---|
| Bridge angle variance may correlate with geometry-level flow complexity. | Plausible intuition only. Not validated here. | `docs/UNCERTAINTIES.md` U-006. |
| Threshold tuning or magnitude normalization may improve cross-field comparison. | Engineering hypothesis only. Not established here. | `docs/UNCERTAINTIES.md` U-004 and U-005. |
| A future multi-slice policy might stabilize candidate comparison. | Not tested here. Current evidence only shows that the present single-slice contract is insufficient for ranking. | Implicit in `docs/METRIC_USEFULNESS_REPORT.md`; contradicted for current single-slice use by `artifacts/slice_sweep_metrics.json`. |

## 5. Stronger-Claim Boundary

The evidence supports claims only up to this boundary:

- deterministic ingestion of current Stage 4 artifacts
- deterministic 3D-to-2D slice encoding under the current contract
- schema-valid bridge-local outputs
- current G5/G6 control success
- tested-input differentiation at the software-descriptor level

Claims become non-defensible as soon as they require any of the following:

- generalizing from a tested 2D slice to a full 3D geometry
- turning descriptor differences into ranking statements
- assigning hydraulic, thermal, structural, or manufacturing meaning to the metrics
- treating Darcy flux angles as resolved physical streamline angles
- asserting TopoStream semantic equivalence or compatibility

## 6. Conflicting Historical Documents

Two repo documents still preserve earlier snapshots and should not be used as current status authorities:

- `docs/REAL_COMPARISON_REPORT.md`
  - Still states that the real-artifact path remains `IMPLEMENTED` because G5/G6 were not yet done.
- `docs/CONTROL_GAP_PACKET.md`
  - Still describes the pre-floor, pre-current-gate state where `VALIDATED` was blocked.

These files are useful as historical records of earlier checkpoints, but not as the current claim boundary.

## 7. Locked Status Paragraph

`coldplate-topobridge` is `VALIDATED` only for the current Stage 4 software/control protocol: it deterministically ingests current Stage 4 velocity artifacts, slices them to 2D, emits schema-valid bridge-local outputs, and passes the present G5/G6 control gates. For the tested diamond TPMS pair, the current 2D slice metrics are not validated ranking proxies. No hydraulic, thermal, structural, holistic 3D, or TopoStream-semantic claim is supported.

## 8. STOP
