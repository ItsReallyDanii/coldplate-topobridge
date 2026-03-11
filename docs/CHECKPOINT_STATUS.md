# docs/CHECKPOINT_STATUS.md
# Bridge Checkpoint Status
# Date: 2026-03-10

## 1. Project Status Summary

The `coldplate-topobridge` is currently in a **VALIDATED** state for its Stage 4 real-artifact ingestion and 2D-slice encoding pipeline.

- **Bridge Scaffold**: Functional. Implements a deterministic pipeline from 2D velocity slices to signature streams.
- **Real Stage 4 Ingestion**: Verified. `Stage4SliceConfig` correctly loads `.npz` velocity fields from `coldplate-design-engine` and applies documented solid/low-signal thresholds.
- **Control Validation**: G5 (Negative Control) and G6 (Positive Control) pass. The bridge correctly identifies zero-transverse flow via `transverse_max_ratio` and distinguishes structured obstructions from uniform flow.
- **Usefulness Audit**: Complete. Quantitative analysis confirms that while metrics are deterministic, their inter-candidate signal for the tested TPMS variants is significantly smaller than intra-candidate slice sensitivity (SNR < 0.2).
- **Testing**: 61/61 tests pass (`pytest`), covering schema integrity, adapter logic, and gate requirements.

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

The bridge is a stable, deterministic software adapter for 2D velocity slices. It successfully bridges the gap from raw CFD-proxy artifacts to bridge-local signature streams with high numerical integrity. It should be used as a structural descriptor of specific cross-sections, and not as a holistic performance ranking tool for the 3D TPMS manifolds tested.
