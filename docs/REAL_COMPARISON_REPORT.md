# docs/REAL_COMPARISON_REPORT.md
# Real Artifact Comparison Report — coldplate-topobridge Stage 2 Validation
# Date: 2026-03-10T18:36 EST
# Status: COMPARISON COMPLETE — see "What This Proves" section below

---

## Comparison Summary

| Property | Value |
|---|---|
| Comparison type | Two real Stage 4 coldplate geometry candidates |
| Outcome | Differences detected, deterministic, documented |
| Claim tier advance | NOT advanced — see gate status table |
| Parent repo edits | None |

---

## Artifacts Compared

### Candidate 01 — diamond_2d seed 1127

```
../coldplate-design-engine/results/stage4_sim_full/candidate_01_diamond_2d_s1127/velocity_field.npz
../coldplate-design-engine/results/stage4_sim_full/candidate_01_diamond_2d_s1127/provenance.json
```

- Input SHA-256: `d3ea45f4601e…` (first 12 chars)
- 3D shape: (50, 50, 50) float64
- Family: `diamond_2d`, seed: 1127
- 3D porosity: 0.555192 → 3D solid fraction: 0.4448
- Source git SHA: `617eb6ab0619…`
- Solver: pressure-Poisson + Darcy's law, converged=True

### Candidate 02 — diamond_2d seed 1045

```
../coldplate-design-engine/results/stage4_sim_full/candidate_02_diamond_2d_s1045/velocity_field.npz
../coldplate-design-engine/results/stage4_sim_full/candidate_02_diamond_2d_s1045/provenance.json
```

- Input SHA-256: `77780539b9c2…`
- 3D shape: (50, 50, 50) float64
- Family: `diamond_2d`, seed: 1045
- 3D porosity: 0.563976 → 3D solid fraction: 0.4360
- Source git SHA: `617eb6ab0619…` (same as candidate 01)
- Solver: same conditions, same boundary pressure drop (1000 Pa, z-flow)

---

## Slice Policy (frozen for this comparison)

```
axis = z
index = 25   (midpoint of nz=50)
solid_threshold_fraction = 1e-3  (of max velocity magnitude)
include_axial_scalar = True
low_signal_threshold = 0.01
```

This is documented explicitly in `tests/test_real_comparison.py`. Any future comparison using
a different slice policy must be separately documented and is NOT directly comparable.

---

## Bridge Output Comparison

All values computed at z=25 mid-slice.

| Metric | cand_01 (s1127) | cand_02 (s1045) | Δ (s1045 − s1127) | % change |
|---|---|---|---|---|
| `n_total` | 2500 | 2500 | 0 | 0% |
| `n_solid` | 1094 | 1074 | **−20** | 1.8% |
| `solid_frac` | 0.4376 | 0.4296 | **−0.0080** | 1.8% |
| `n_low_signal` | 0 | 0 | 0 | — |
| `n_active` | 1406 | 1426 | **+20** | 1.4% |
| `theta_mean` (rad) | −0.12624 | −0.09583 | +0.030 | — |
| `theta_std` (rad) | 1.80808 | 1.80943 | **+0.00135** | 0.07% |
| `theta_abs_mean` (rad) | 1.58615 | 1.58509 | −0.001 | — |
| `mag_mean` (m/s) | 83.71 | 83.54 | −0.17 | 0.2% |
| `mag_std` (m/s) | 36.49 | 36.34 | −0.15 | 0.4% |
| `mag_max` (m/s) | 158.19 | 164.77 | **+6.58** | 4.2% |
| `grad_mean` | 0.94852 | 0.94278 | −0.006 | 0.6% |
| `grad_max` | 5.78218 | 5.70578 | −0.076 | 1.3% |
| stream hash | `27f8a06f90ee…` | `ca91de9aacd0…` | DIFFER | — |
| input sha256 | different | different | DIFFER | — |

### Key observation

- `theta_std` difference is **0.07%** — very small, indicating both geometries at this
  slice index produce nearly identical angular spread distributions.
- `n_solid` difference is **20 pixels** (1.8%) — consistent with the difference in
  3D porosity between the two seeds (0.555192 vs 0.563976).
- `mag_max` difference is **4.2%** — the seed-1045 geometry allows a slightly higher
  peak velocity at this cross-section.
- Stream hashes DIFFER — the full pixel-level records are distinct.

---

## Determinism Verification

| Run | Hash 1 | Hash 2 | Match? |
|---|---|---|---|
| cand_01 run A vs run B | `27f8a06f90ee6…` | `27f8a06f90ee6…` | ✅ SAME |
| cand_02 run A vs run B | `ca91de9aacd04…` | `ca91de9aacd04…` | ✅ SAME |
| cand_01 vs cand_02 | `27f8a06f90ee6…` | `ca91de9aacd04…` | ✅ DIFFER |

All three determinism gate criteria confirmed.

---

## Commands Run

```bash
# 1. Emit candidate_01 artifact bundle
python -m topobridge.cli stage4 \
    ../coldplate-design-engine/results/stage4_sim_full/candidate_01_diamond_2d_s1127/velocity_field.npz \
    ../coldplate-design-engine/results/stage4_sim_full/candidate_01_diamond_2d_s1127/provenance.json \
    --output artifacts/stage4_full_cand01_z25 \
    --slice-axis z --slice-index 25

# 2. Emit candidate_02 artifact bundle
python -m topobridge.cli stage4 \
    ../coldplate-design-engine/results/stage4_sim_full/candidate_02_diamond_2d_s1045/velocity_field.npz \
    ../coldplate-design-engine/results/stage4_sim_full/candidate_02_diamond_2d_s1045/provenance.json \
    --output artifacts/stage4_full_cand02_z25 \
    --slice-axis z --slice-index 25

# 3. Validate both bundles
python -m topobridge.cli validate artifacts/stage4_full_cand01_z25  → PASS
python -m topobridge.cli validate artifacts/stage4_full_cand02_z25  → PASS

# 4. Run full test suite
python -m pytest tests/ -v --tb=short  → 51 passed in 1.70s
```

---

## Artifact Trees Produced

```
artifacts/stage4_full_cand01_z25/
  field_contract.json  ← sha256=d3ea45f4601e..., shape=[50,50], solid_frac=0.438
  signatures.jsonl     ← 2500 records, n_active=1406
  summary.json         ← theta_std=1.80808, n_solid=1094
  manifest.json        ← run_sha256=2e4d0d7d044a...

artifacts/stage4_full_cand02_z25/
  field_contract.json  ← sha256=77780539b9c2..., shape=[50,50], solid_frac=0.430
  signatures.jsonl     ← 2500 records, n_active=1426
  summary.json         ← theta_std=1.80943, n_solid=1074
  manifest.json        ← run_sha256=ce7b4a39bd02...

artifacts/real_comparison_metrics.json  ← full comparison table with all stats
```

---

## Test Results

```
51 passed, 0 failed, 0 skipped in 1.70s

  test_real_comparison.py::TestRealCandidateComparison:
    test_candidate01_output_is_deterministic               PASSED
    test_candidate02_output_is_deterministic               PASSED
    test_outputs_differ_between_candidates                 PASSED
    test_summary_stats_differ_between_candidates           PASSED
    test_same_git_sha_across_candidates                    PASSED
    test_both_candidates_same_grid_shape                   PASSED
    test_solid_fractions_in_expected_range                 PASSED
    test_theta_std_in_plausible_range                      PASSED
    test_n_active_pixels_above_zero                        PASSED
    test_record_keys_are_valid_schema                      PASSED
```

---

## VALIDATED Tier Gate Status

The bridge has three tiers: IMPLEMENTED → VALIDATED → (future higher tiers).  
For the VALIDATED tier on the real-artifact path, the following gates are defined in `CLAIM_TIERS.md`:

| Gate | Condition | Status |
|---|---|---|
| G1 | Real artifact loads without error | ✅ PASS |
| G2 | Output is deterministic (same hash on two runs) | ✅ PASS (both candidates) |
| G3 | Bundle validates against JSON schema | ✅ PASS |
| G4 | Outputs differ between different inputs | ✅ PASS |
| G5 | Negative control: known-uniform geometry produces low theta_std | ❌ NOT YET DONE |
| G6 | Positive control: known-varied geometry produces high theta_std | ❌ NOT YET DONE |

**Current claim tier for real-artifact path: IMPLEMENTED** (G5 and G6 not yet done).

G5 and G6 require a uniform-channel Stage 4 artifact in
`../coldplate-design-engine/results/` — none currently exists. This is an upstream gap.

---

## Open Uncertainties

See `docs/UNCERTAINTIES.md`. New observations from this comparison:

| ID | Observation |
|---|---|
| U-009 | z=25 mid-slice produces theta_std ≈ 1.808 for both candidates — nearly identical despite different seeds. Slice choice may dominate the signal over geometry variation. |
| U-010 | Solid pixel count differs by 20 at z=25 — consistent with 3D porosity difference (Δ=0.0088). Some of this may be threshold detection noise rather than true geometry. |
| U-012 | **NEW**: theta_std difference between candidates is only 0.07% — smaller than expected for seed-level geometry variation. It is NOT_PROVEN whether a larger z-sensitivity study would reveal more separation. |

---

## What This Proves

> **Claim tier: IMPLEMENTED** (unchanged)

1. **Two real Stage 4 coldplate artifacts were ingested**, encoded, and validated independently.
2. **Both runs are deterministic**: identical JSONL stream hash on independent re-runs.
3. **Outputs differ between candidates**: different stream hashes, 20-pixel n_solid difference, 4.2% mag_max difference.
4. **Differences are documented**: exact metrics table above, frozen slice policy, git SHA confirmed consistent across both candidates.
5. **No parent repo was modified**: zero edits to `coldplate-design-engine` or `topostream_stage0_specs`.
6. **51/51 tests pass**, including 10 new real-comparison tests.
7. **Comparison metrics are saved** in `artifacts/real_comparison_metrics.json` for reproducibility.

---

## What This Does NOT Prove

> **None of the following are claimed.**

1. **That theta_std differences between candidates reflect physical performance differences.**  
   A 0.07% difference in theta_std is noted. It is NOT_PROVEN that this small difference
   correlates with any thermal, hydraulic, or geometric performance gap.

2. **That seed 1045 is "better" or "worse" than seed 1127 by any bridge metric.**  
   The bridge produces descriptive signatures only. It does not rank geometries.

3. **That the z=25 mid-slice captures the most informative cross-section.**  
   Slice index 25 is a convention. Other z-levels may produce different relative rankings.

4. **That the 0.07% theta_std difference is statistically significant.**  
   No uncertainty quantification for bridge summary statistics exists. Slice index variation
   alone can change theta_std by more than this (Z=10 vs Z=30 produces measurably different
   values per test `test_different_z_slices_produce_different_hashes`).

5. **That Darcy velocity cross-sections are physically meaningful for any purpose.**  
   See U-011. Darcy velocity is a volume-averaged approximation.

6. **That VALIDATED tier is reached.**  
   G5 (uniform geometry negative control) and G6 (varied geometry positive control)
   are not completed. The claim tier remains IMPLEMENTED.

7. **Any correspondence with TopoStream token semantics.** Still NOT_PROVEN.

---

## STOP
