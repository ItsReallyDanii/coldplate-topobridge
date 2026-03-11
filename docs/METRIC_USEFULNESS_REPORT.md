# docs/METRIC_USEFULNESS_REPORT.md
# Real Input VALIDATED Tier — Metric Usefulness Audit
# Date: 2026-03-10

This document audits the usefulness and robustness of the bridge's Stage 4 real-artifact descriptor metrics. While the bridge correctly executes and distinguishes inputs deterministically, a software descriptor is only useful if its inter-candidate separation is larger than its intra-candidate noise.

---

## 1. Audit Methodology

- **Artifacts used:**
  - `candidate_01_diamond_2d_s1127` (overall rank 1)
  - `candidate_02_diamond_2d_s1045` (overall rank 2)
  - `baseline_uniform_channel_ctrl` (G5 negative control)
  - `baseline_single_obstruction_ctrl` (G6 positive control)
- **Sweep policy:** `z`-axis (transverse flow cross-section) at indices `10, 15, 20, 25, 30, 35, 40` out of 50.
- **Constraints:** Metrics derived ONLY from Bridge Stage 4 fields (vx, vy, vz). No upstream edits.

---

## 2. Summary of Slice Variation

The following statistics measure metric variance *within* a single candidate (across 7 slices) vs. difference *between* candidates (averaged across slices).

| Metric | Cand01 Range (span) | Cand02 Range (span) | Slice StdDev | Mean Diff btwn Cands | Signal-to-Noise |
|---|---|---|---|---|---|
| `solid_fraction` | 0.428 – 0.457 (0.029) | 0.418 – 0.448 (0.030) | ~0.009 | **0.008** | **< 1** |
| `theta_std` (rad) | 1.766 – 1.815 (0.049) | 1.762 – 1.819 (0.056) | ~0.017 | **0.002** | **< 0.2** |
| `grad_mean` (rad/px) | 0.918 – 0.968 (0.050) | 0.900 – 0.965 (0.065) | ~0.017 | **0.005** | **< 0.3** |

### Key Finding: Slice-Sensitivity Dominates Inter-Candidate Separation

For the two tested diamond TPMS geometry seeds:
- The variation of `theta_std` depending on *which slice is selected* (±0.049 rad span) is roughly **20 times larger** than the mean difference between the two configurations (~0.002 rad).
- The metrics do not monotonically separate the candidates across the tested z-range. For example, `theta_std` is higher for cand01 at z=20, but higher for cand02 at z=25.
- Therefore, for these specific TPMS candidates, a single 2D slice is not a reliable structural proxy for holistic 3D manifold differences. The choice of `z` index determines the relative ranking.

---

## 3. Metric Classification Table

Based on the audit of these candidates, the current bridge-local summary metrics are classified as follows:

| Metric | Classification | Justification |
|---|---|---|
| **`transverse_max_ratio`** | **KEEP** | Robust numerical validity check for undefined/zero transverse flow (G5 pass). |
| **`n_solid`, `n_active`** | **KEEP** | Structural metadata that correctly scales with porosity. Essential for data sanity. |
| **`theta_std`** | **WEAK** | Successfully separates strong controls (uniform=0.0 vs obstruction=1.79). Fails to stably separate the two TPMS variants across the slice set (SNR < 0.2). |
| **`theta_mean`** | **UNSTABLE** | Fluctuates near 0 based on slice phase relative to symmetrical flow splitting. |
| **`grad_mean`** | **WEAK** | Dominated by slice noise for these candidates (span 0.050 vs mean diff 0.005). |
| **`low_signal_fraction`**| **NOT_USEFUL_YET** | Floor threshold (1e-6) subsumes relative threshold (1%) for current artifacts. |

---

## 4. Conclusions

1. **Continue current metric family as software descriptors:** The metrics (`theta_std`, `grad_mean`, etc.) are implementation-complete, deterministic, and pass all gate tests (G1–G6). They should remain as the bridge's signature descriptors.
2. **Relative ranking is slice-dependent for TPMS:** For the tested TPMS pair, inter-candidate signal is significantly smaller than intra-candidate slice sensitivity. One cannot conclude which geometry is "more complex" from a single 2D slice.
3. **No holistic performance claims:** This audit confirms that bridge outputs describe a *specific* cross-section. They should not be used as proxies for holistic 3D coldplate performance without a stabilized, multi-slice averaging policy (outside current scope).

**Final Action:** The bridge pipeline is frozen as a stable structural descriptor for 2D slices. We will NOT promote these metrics as 3D rankings or invent new 3D metrics, as the current 2D-slice contract is fulfilled.
