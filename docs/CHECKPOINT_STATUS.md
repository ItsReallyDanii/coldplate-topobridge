# docs/CHECKPOINT_STATUS.md
# Bridge Checkpoint Status
# Date: 2026-03-11

## 1. Project Status Summary

The `coldplate-topobridge` is currently in a **VALIDATED** state only for the current Stage 4 software/control protocol covering real-artifact ingestion and 2D-slice encoding.

- **Bridge Scaffold**: Functional. Implements a deterministic pipeline from 2D velocity slices to signature streams.
- **Real Stage 4 Ingestion**: Verified. `Stage4SliceConfig` correctly loads `.npz` velocity fields from `coldplate-design-engine` and applies documented solid/low-signal thresholds.
- **Control Validation**: G5 (Negative Control) and G6 (Positive Control) pass. The bridge correctly identifies zero-transverse flow via `transverse_max_ratio` and distinguishes structured obstructions from uniform flow.
- **Usefulness Audit**: Complete. Quantitative analysis confirms that while metrics are deterministic, their inter-candidate signal for the tested TPMS variants is significantly smaller than intra-candidate slice sensitivity (SNR < 0.2).
- **Testing**: 61/61 tests pass (`pytest`), covering schema integrity, adapter logic, and gate requirements.
- **Current claim sources**: Use this file, `CLAIM_TIERS.md`, `docs/METRIC_USEFULNESS_REPORT.md`, and `docs/CLAIM_AUDIT_REPORT.md` for the current claim boundary. `docs/REAL_COMPARISON_REPORT.md` and `docs/CONTROL_GAP_PACKET.md` are historical snapshots and still contain pre-validation language.

---

## 2. Rerun Commands

### Real Stage 4 Bridge Run
To encode a specific candidate slice (e.g., candidate_01, z=25):
```powershell
python -m topobridge.cli stage4 `
    ..\coldplate-design-engine\results\stage4_sim_full\candidate_01_diamond_2d_s1127\velocity_field.npz `
    ..\coldplate-design-engine\results\stage4_sim_full\candidate_01_diamond_2d_s1127\provenance.json `
    --output artifacts/stg4_example `
    --slice-axis z --slice-index 25
```

### Control Validation (G5/G6 Gates)
To verify the bridge correctly handles controls:
```powershell
python -m pytest tests/test_real_comparison.py
```

### Slice Usefulness Audit
To reproduce the 7-slice sweep analysis for candidate_01 and candidate_02:
```powershell
python scripts/slice_sweep.py
```

---

## 3. Claims Governance

| Category | Allowed Claims | Forbidden Claims |
|---|---|---|
| **Software** | Bridge output is bitwise deterministic. | Bridge ranking is slice-invariant. |
| **Ingestion** | Bridge correctly slices 3D Darcy `.npz` fields. | Darcy velocity represents point-wise physical streamlines. |
| **Validation** | Bridge distinguishes obstructions from uniform flow. | `theta_std` rank correlates with hydraulic performance. |
| **Semantics** | Bridge descriptors describe a specific 2D slice. | Bridge signatures correlate with TopoStream tokens. |

---

## 4. Final Conclusion

`coldplate-topobridge` is **VALIDATED** only for the current Stage 4 software/control protocol: it deterministically ingests current Stage 4 velocity artifacts, slices them to 2D, emits schema-valid bridge-local outputs, and passes the present G5/G6 control gates. For the tested diamond TPMS pair, the current 2D slice metrics are not validated ranking proxies. No hydraulic, thermal, structural, holistic 3D, or TopoStream-semantic claim is supported.

---

## 5. TPMS Family SNR Pilot (2026-03-11)

Script: `scripts/run_tpms_family_snr_pilot.py`
Artifact: `artifacts/tpms_family_snr_pilot_v1_1/pilot_summary.json`

**Gate results (z=25 slice, `candidate_gyroid_3d_s0000`):**
- Porosity gate (0.414–0.453): PASS (gyroid solid_fraction = 0.434)
- Transverse gate (> 1e-4): PASS (gyroid transverse_max_ratio = 2.539)

**SNR metrics (ddof=0 over 2 diamond seeds):**
- SNR_theta_std = 215.15 (signal = 0.145 rad; diamond σ = 0.000676 rad)
- SNR_grad_mean = 119.83 (signal = 0.207 rad/px; diamond σ = 0.00173 rad/px)

**Outcome: AMBIGUOUS**

The large SNR values reflect a near-zero intra-diamond-seed variance in the denominator —
not a validated separability claim. The gyroid `theta_std` (1.663 rad) and `grad_mean`
(0.393 rad/px) are *lower* than the diamond reference means (1.809 rad, 0.601 rad/px
respectively). This unexpected direction is consistent with the prior finding in
`METRIC_USEFULNESS_REPORT.md` that 2D slice metrics are unreliable proxies for holistic
3D structural differences. No ranking claim is supported.

**Preserved caveats:**

1. **Untracked-origin caveat:** The script that generated the gyroid Stage 4 artifact
   (`emit_stage4_gyroid.py`) is not in this repository. The gyroid artifact's generation
   provenance exits the repo boundary into the sibling `coldplate-design-engine` directory.

2. **Machine-local paths:** Paths recorded in `pilot_summary.json`
   (`velocity_path`, `provenance_path`) are Windows absolute paths
   (`C:\Users\slyki\OneDrive\...`) that are unreproducible outside the origin machine.
   The artifact JSON is committed; the source data is not.

3. **Transverse-ratio discrepancy:** The gyroid transverse_max_ratio (2.539) is higher
   than the diamond values (~2.025–2.058). This reflects expected cross-sectional geometry
   differences between the 3D gyroid candidate (`candidate_gyroid_3d_s0000`) and the
   2D diamond candidates (`candidate_*_diamond_2d_*`) at z=25. It is not a metric anomaly.

4. **Branch divergence at execution time:** Local master was 2 commits behind remote
   origin at the time of pilot execution. The pilot was committed on top of the checkpoint
   branch without rebasing onto the latest remote tip.

**Claim tier:** IMPLEMENTED (pilot script runs without exception; gate checks are
deterministic). VALIDATED tier is not extended by this pilot. Gyroid ranking is explicitly
not supported.
