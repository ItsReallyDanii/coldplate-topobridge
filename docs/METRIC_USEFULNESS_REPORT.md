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

### Key Finding: Noise Dominates Signal

For the two diamond TPMS geometry seeds:
- The variation of `theta_std` depending on *which slice you pick* (±0.049 rad) is roughly **20 times larger** than the difference between the two different geometries (~0.002 rad).
- The metrics do not monotonically separate the candidates. For example, `theta_std` is higher for cand01 at z=20, but higher for cand02 at z=25.
- Therefore, a single 2D slice comparison is structurally incapable of robustly ranking 3D TPMS variants. The choice of `z` index determines the winner.

---

## 3. Metric Classification Table

Based on the audit, the current bridge-local summary metrics are classified as follows:

| Metric | Classification | Justification |
|---|---|---|
| **`transverse_max_ratio`** | **KEEP** | Robust numerical validity check for undefined/zero transverse flow (G5 pass). Not a ranking metric, but a necessary diagnostic boolean. |
| **`n_solid`, `n_active`** | **KEEP** | Structural metadata that correctly scales with porosity. Essential for data sanity, even if slice-variable. |
| **`theta_std`** | **WEAK** | Successfully separates strong controls (uniform=0.0 vs obstruction=1.79). Fails to stably separate similar TPMS geometries across slices (SNR < 0.2). Useful as a macro-feature, useless for micro-optimization of TPMS. |
| **`theta_mean`** | **UNSTABLE** | Meaningless for 3D TPMS manifolds where flow symmetrically splits in both directions. Arbitrarily fluctuates near 0 based on slice phase. |
| **`grad_mean`** | **WEAK** | Originally intended as a structural complexity proxy. Also dominated by slice noise (span 0.050 vs mean diff 0.005). Fails to separate candidates. |
| **`low_signal_fraction`**| **NOT_USEFUL_YET** | Almost always 0.0 for actual Darcy results because the absolute floor (1e-6) clears machine-noise. The relative threshold (1%) almost never triggers in high-pressure-drop manifolds. |

---

## 4. Conclusions

1. **Continue current metric family, but with strict disclaimer:** The existing metrics (`theta_std`, `grad_mean`) are successfully deterministic, pass schemas, and detect macro-level flow changes (G5/G6 controls pass easily). We should KEEP them as they fulfill the bridge's software requirements.
2. **2D slice approach is physically weak for 3D TPMS:** The assumption that a single 2D cross-section can represent the flow complexity of a 3D repeating lattice is proven false by the SNR < 1 finding. Slice-phase noise dominates geometry variation.
3. **No performance claims:** This audit confirms that using `coldplate-topobridge` outputs to "rank" or "score" geometries is scientifically invalid under the current 2D-slice constraint. Any downstream agent must be instructed that bridge signatures describe a *specific* cross-section, not the holistic performance of the coldplate.

**Final Action:** The current metric pipeline remains intact as a software adapter, but explicitly moves from "seeking a topological signal" to "providing a deterministic structural descriptor." We will NOT invent new 3D metrics here, as that violates the hard constraint against rewriting bridge semantics.
