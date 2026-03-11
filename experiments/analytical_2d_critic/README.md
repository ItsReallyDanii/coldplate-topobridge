# EXPERIMENTAL_SANDBOX Analytical 2D Critic

This folder contains a separate prototype for a bounded 2D design-critic demo.

Scope:
- EXPERIMENTAL_SANDBOX only
- no changes to the validated Stage 4 bridge/control path
- no TopoStream semantic integration
- no TPMS ranking claim

Cases:
- `straight_channel`: `EXACT_ANALYTIC`
- `single_obstruction`: `SYNTHETIC`
- `constricted_channel`: `QUASI_ANALYTICAL`

What the prototype does:
- generates deterministic 2D channel fields
- reuses the repo's existing bridge-local encoder to emit `signatures.jsonl`
- writes a sandbox `descriptor_summary.json` per case
- writes `critic_comparison.json` for a bounded three-case comparison

What it does not do:
- prove physical realism for the synthetic obstruction field
- prove vortex correspondence
- prove TopoStream semantic compatibility
- validate ranking for 3D TPMS coldplate candidates

Run:

```powershell
python experiments\analytical_2d_critic\run_demo.py --output-root C:\tmp\analytical_2d_critic_demo
```

Outputs:
- `fields/*.npz` and `fields/*.meta.json`
- `results/<case>/field_contract.json`
- `results/<case>/signatures.jsonl`
- `results/<case>/summary.json`
- `results/<case>/descriptor_summary.json`
- `critic_comparison.json`

Format note:
- the record/summary format intentionally resembles existing bridge artifacts
- that resemblance is format-only and does not imply TopoStream compatibility
