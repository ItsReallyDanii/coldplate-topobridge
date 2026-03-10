# Real Input Blockers — coldplate-topobridge Stage 2 Entry Audit

**Date:** 2026-03-10  
**Status:** OUTCOME A — Viable real input found and wired.  
**This document records the audit findings and any partial blockers for the record.**

---

## Audit Summary

### What was audited (read-only)

```
../coldplate-design-engine/results/
  stage2_inverse/           → csv/jsonl optimizer results only — NO field data
  stage2_inverse_smoke/     → csv/jsonl optimizer results only — NO field data
  stage4_sim_full/
    candidate_01_diamond_2d_s1127/
      velocity_field.npz    ← VIABLE (vx, vy, vz, shape 50×50×50)
      pressure_field.npy    ← scalar field, shape 50×50×50
      provenance.json       ← rich provenance (git SHA, solver params, geometry lineage)
      metrics.json          ← summary statistics only
      solver_info.json      ← convergence info
  stage4_sim_smoke/
    candidate_01_diamond_2d_s1127/
      velocity_field.npz    ← VIABLE (vx, vy, vz, shape 20×20×20)  ← USED FOR TESTS
      ...
  stage5_thermal_smoke/     → temperature_field.npy only, no velocity
  stage6_structural_smoke/  → structural analysis only
  stage7_benchtop/          → README + calibration/test_data subdirs, no emitted fields
../coldplate-design-engine/
  baselines/channels/       → no files (only directory structure)
  baselines/tpms/           → no files
  configs/                  → yaml only
  data/                     → .gitkeep only
```

### Candidate found: Stage 4 velocity_field.npz

| Property | Value |
|---|---|
| File | `results/stage4_sim_{full,smoke}/candidate_*/velocity_field.npz` |
| Keys | `vx`, `vy`, `vz` (all `float64`) |
| Shape (full) | `(50, 50, 50)` |
| Shape (smoke) | `(20, 20, 20)` |
| Solver | Pressure-Poisson + Darcy's law: `v = -(k/μ) ∇p` |
| Flow direction | `z`-axis (inlet at `z=0`, outlet at `z=nz-1`) |
| Solid encoding | Zero-velocity (NOT NaN; NaN count = 0) |
| Provenance | Rich `provenance.json` with git SHA, timestamps, geometry lineage |
| Real data | Yes — full run took 132s solve time; confirmed with `converged=True` |

### Solid mask extraction

Stage 4 does **not** emit a separate solid mask array. The only reliable approach from emitted artifacts is threshold detection on velocity magnitude:

```
solid_mask = (|v| < threshold_fraction × max(|v|)).astype(uint8)
threshold_fraction = 1e-3  (default)
```

Validation: at z=25 mid-slice, detected solid fraction ≈ 0.438, consistent with 3D porosity=0.555192.

### Stage 2 (inverse optimizer): NOT VIABLE

Stage 2 emits only:
- `best_candidates.csv` — score/parameter tables
- `genetic_algorithm_results.jsonl` — per-generation summaries
- `random_search_results.jsonl` — random search results
- `run_manifest.json`

**No field data** (u/v/mask). Stage 2 is a design optimizer, not a field simulator. Blocker for Stage 2: no field artifact exists.

### Stage 5 thermal: NOT VIABLE for bridge

Stage 5 emits `temperature_field.npy` (scalar, no velocity). The bridge contract requires u/v. Stage 5 temperature could be used as an optional `scalar` field alongside Stage 4 velocity — but this is out of scope for this run.

---

## Partial Blocker: 3D → 2D slice is a choice, not a ground truth

The bridge field contract requires a 2D (ny, nx) array. Stage 4 produces 3D (nx, ny, nz). The adapter performs a slice at a specified z-index (default: midpoint). This introduces:

- **Choice sensitivity**: different z-slices produce different signatures
- **Representativeness**: NOT_PROVEN that any single slice is "representative"
- **Solid detection accuracy**: NOT_PROVEN at 1e-3 threshold accuracy

These are documented in docs/UNCERTAINTIES.md as U-009, U-010, U-011.

---

## Conclusion

No blocker report required. A viable, read-only ingestion path was identified and wired. All existing tests still pass. New Stage 4-specific tests pass on real artifacts.

The pipeline **does NOT** require importing any coldplate-design-engine Python module. It reads emitted `.npz` and `.json` files only.
