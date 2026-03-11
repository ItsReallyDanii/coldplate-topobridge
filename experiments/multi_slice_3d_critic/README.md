# EXPERIMENTAL_SANDBOX Multi-Slice / Simple 3D Proxy Critic

This folder contains a separate prototype for a bounded multi-slice / simple 3D proxy critic demo.

Scope:
- EXPERIMENTAL_SANDBOX only
- no changes to the validated Stage 4 bridge/control path
- no physical realism claim
- no vortex correspondence claim
- no TopoStream semantic compatibility claim
- no validated ranking of 3D TPMS coldplate candidates
- no physics validation claim

Cases:
- `straight_stack`: `EXACT_ANALYTIC`
- `obstruction_stack`: `SYNTHETIC`
- `constriction_stack`: `QUASI_ANALYTICAL`

What the prototype does:
- generates deterministic stacks of 2D slices with controlled variation
- reuses the repo's existing bridge-local encoder on each slice
- writes per-slice `field_contract.json`, `signatures.jsonl`, `summary.json`, and `descriptor_summary.json`
- writes a per-case `case_summary.json`
- writes `critic_comparison.json` for a bounded stack-level comparison
- supports a bounded robustness sweep via `run_robustness.py`

What it does not do:
- prove physical realism
- prove vortex correspondence
- prove TopoStream semantic compatibility
- validate ranking for 3D TPMS coldplate candidates
- imply hydraulic, thermal, structural, or manufacturing meaning
- validate physics

Run (demo):

```powershell
python experiments\multi_slice_3d_critic\run_demo.py --output-root C:\tmp\multi_slice_3d_critic_demo
```

Run (bounded robustness sweep):

```powershell
python experiments\multi_slice_3d_critic\run_robustness.py --output-root C:\tmp\multi_slice_3d_critic_robustness
```

Robustness sweep result (bounded):
- Ordering `straight_stack < obstruction_stack < constriction_stack` was stable across all
  tested variants (baseline, slice_count_5, resolution_16x10, threshold_0p020,
  perturbation_0p012) — zero ordering flips.
- Recommendation stayed `continue` across all variants.
- Every variant kept the minimum documented gap above the 0.08 bounded threshold.
- Ablation-level token-bin changes were observed for `slice_count_5` only
  (`SLICE_VARIATION_TIGHT` → `SLICE_VARIATION_MODERATE` for `obstruction_stack`).
  Ordering and gap were unaffected.
- The sweep does NOT prove physical realism, vortex correspondence, TopoStream
  compatibility, 3D ranking, or any hydraulic, thermal, structural, or
  manufacturing meaning.

Outputs:
- `fields/<case>/stack_manifest.json`
- `fields/<case>/<slice>.npz` and `.meta.json`
- `results/<case>/slices/<slice>/field_contract.json`
- `results/<case>/slices/<slice>/signatures.jsonl`
- `results/<case>/slices/<slice>/summary.json`
- `results/<case>/slices/<slice>/descriptor_summary.json`
- `results/<case>/case_summary.json`
- `critic_comparison.json`

Format note:
- the record and summary format intentionally resembles existing bridge artifacts
- that resemblance is format-only and does not imply TopoStream compatibility
- the stack is a bounded simple-3D proxy built from deterministic slice rules
