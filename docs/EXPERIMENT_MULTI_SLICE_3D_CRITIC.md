# EXPERIMENT_MULTI_SLICE_3D_CRITIC.md

## Status

This is an `EXPERIMENTAL_SANDBOX` prototype inside `coldplate-topobridge`.

It is intentionally separate from the validated Stage 4 bridge/control pipeline.
It does not modify Stage 4 semantics and it does not broaden current repo claims.

---

## Goal

Test whether descriptor separation remains deterministic and bounded when the
critic is moved from single 2D cases to a simple multi-slice proxy.

The proxy is a stack of deterministic 2D slices with controlled variation.
This is a bounded bridge experiment, not a validation study.

---

## Geometry Cases

1. `straight_stack`
   - Type: stacked straight channel
   - Provenance class: `EXACT_ANALYTIC`
   - Construction: identical plane-Poiseuille slices repeated across z

2. `obstruction_stack`
   - Type: straight channel with one obstruction varying deterministically across slices
   - Provenance class: `SYNTHETIC`
   - Construction: deterministic blend of a Poiseuille envelope, obstruction-induced
     deflection, wake attenuation, and gap boost with z-dependent parameters
   - Claim boundary: this is not CFD and is not claimed as physically realistic

3. `constriction_stack`
   - Type: smooth constriction stack with deterministic z-variation
   - Provenance class: `QUASI_ANALYTICAL`
   - Construction: imposed streamfunction with throat depth, width, and center
     varying across slices
   - Claim boundary: exact for the constructed streamfunction per slice, not claimed
     as an exact Navier-Stokes solution or validated coldplate physics model

---

## Structured Outputs

Per slice, the sandbox emits:
- `field_contract.json`
- `signatures.jsonl`
- `summary.json`
- `descriptor_summary.json`

Per case, the sandbox emits:
- `case_summary.json`
- `stack_manifest.json`

Across the run, the sandbox emits:
- `critic_comparison.json`

These files deliberately resemble bridge-local artifacts so the critic can be
tested without changing the validated mainline path.

---

## What This Proves

- The sandbox produces deterministic slice generation and deterministic
  descriptor extraction for the defined multi-slice cases.
- Explicit provenance labeling separates `EXACT_ANALYTIC`,
  `QUASI_ANALYTICAL`, and `SYNTHETIC` stacks without hiding approximation status.
- In this bounded stack setup, descriptor separation remains observable after
  aggregating controlled slice variation with sandbox-only metrics.

---

## What This Does NOT Prove

- It does not prove physical realism.
- It does not prove vortex correspondence.
- It does not prove TopoStream semantic compatibility.
- It does not validate ranking of 3D TPMS coldplate candidates.
- It does not validate physics.
- It does not show that stack-level descriptor ordering predicts hydraulic,
  thermal, structural, or manufacturing performance.

---

## Why This Remains Only a Bounded Bridge Experiment

- The stack is synthetic or quasi-analytical by construction and is not a
  validated 3D solver output.
- The aggregation metrics are sandbox-only ordering aids, not validated scores.
- The bridge encoder still operates on 2D slices; the stack is only a simple
  proxy for controlled cross-slice variation.
- No real-candidate or Stage 4 ranking claim is earned from this experiment.

---

## Current Default Outcome

With the default grid and thresholds, the bounded critic summary orders the
cases from lower to higher stack complexity as:

1. `straight_stack`
2. `obstruction_stack`
3. `constriction_stack`

This ordering is local to this sandbox setup only.

---

## Bounded Robustness Sweep Result

A bounded parameter sweep was run across five variants (`baseline`, `slice_count_5`,
`resolution_16x10`, `threshold_0p020`, `perturbation_0p012`) to test whether the
documented ordering was stable under controlled changes to slice count, grid resolution,
descriptor threshold, and deterministic sinusoidal dither.

**Stable findings:**
- The documented ordering `straight_stack < obstruction_stack < constriction_stack`
  held across all five variants — zero ordering flips observed.
- The bounded recommendation (`continue`) held across all five variants.
- Every variant kept the documented minimum gap above the 0.08 bounded threshold.
- Provenance classes remained explicit and unchanged for all variants.

**Observed under bounded variation (reported honestly, not overstated):**
- Absolute `stack_complexity_index` values shifted under slice-count, resolution, threshold,
  and perturbation changes. This is expected behavior for sandbox-only ordering metrics.
- Ablation-level token-bin changes were observed for `slice_count_5`
  (`SLICE_VARIATION_TIGHT` → `SLICE_VARIATION_MODERATE` for `obstruction_stack`).
  The ordering and gap were unaffected. This is not treated as an ordering failure.

**This sweep does NOT prove:**
- Physical realism
- Vortex correspondence
- TopoStream semantic compatibility
- Validated ranking of 3D TPMS coldplate candidates
- Hydraulic, thermal, structural, or manufacturing meaning
- Physics validation

---

## Recommendation

Recommendation: `continue`

Reason:
- generation is deterministic
- per-slice and stack-level descriptors are deterministic
- the cases remain separable under controlled slice variation
- provenance classes remain explicit

Continue means only that a later bounded follow-up may be worth testing.
It does not authorize stronger claims.
