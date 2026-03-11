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

What it does not do:
- prove physical realism
- prove vortex correspondence
- prove TopoStream semantic compatibility
- validate ranking for 3D TPMS coldplate candidates
- imply hydraulic, thermal, structural, or manufacturing meaning
- validate physics

Run:

```powershell
python experiments\multi_slice_3d_critic\run_demo.py --output-root C:\tmp\multi_slice_3d_critic_demo
```

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
