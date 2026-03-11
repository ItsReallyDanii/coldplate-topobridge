# EXPERIMENT_ANALYTICAL_2D_CRITIC.md

## Status

This is an `EXPERIMENTAL_SANDBOX` prototype inside `coldplate-topobridge`.

It is intentionally separate from the validated Stage 4 bridge/control pipeline.
It does not modify Stage 4 semantics and it does not broaden current repo claims.

---

## Goal

Test whether three simple 2D channel geometries can produce deterministic,
structured bridge-style descriptor outputs that are different enough to support
a later critic-style loop.

This is a bounded descriptor-stability experiment, not a validation study.

---

## Geometry Cases

1. `straight_channel`
   - Type: uniform straight channel
   - Provenance class: `EXACT_ANALYTIC`
   - Construction: plane-Poiseuille profile in a fixed-width slit

2. `single_obstruction`
   - Type: straight channel with one circular obstruction
   - Provenance class: `SYNTHETIC`
   - Construction: deterministic blend of a Poiseuille envelope, cylinder-like deflection,
     and downstream wake attenuation
   - Claim boundary: this is not CFD and is not claimed as physically realistic

3. `constricted_channel`
   - Type: smooth constricted channel
   - Provenance class: `QUASI_ANALYTICAL`
   - Construction: imposed streamfunction with x-varying gap height
   - Claim boundary: exact for the constructed streamfunction, not claimed as an exact
     Navier-Stokes solution for a real constricted channel

---

## Structured Outputs

Per case, the sandbox emits:
- `field_contract.json`
- `signatures.jsonl`
- `summary.json`
- `descriptor_summary.json`

The first three deliberately resemble existing bridge-local artifacts so the
critic can be tested without changing the validated mainline path.

`descriptor_summary.json` adds sandbox-only fields such as:
- `provenance_class`
- `descriptor_tokens`
- `bounded_complexity_index`

`critic_comparison.json` compares the three cases using the sandbox descriptor
summaries only.

---

## What This Proves

- The sandbox produces deterministic bounded 2D descriptor separation across the
  defined cases.
- Explicit provenance labeling separates `EXACT_ANALYTIC`,
  `QUASI_ANALYTICAL`, and `SYNTHETIC` cases without hiding approximation status.

---

## What This Does NOT Prove

- It does not prove physical realism for the obstruction field.
- It does not prove that descriptor complexity predicts hydraulic, thermal,
  or manufacturing performance.
- It does not prove that any descriptor corresponds to a real fluid vortex.
- It does not prove TopoStream semantic compatibility.
- It does not validate ranking of 3D TPMS coldplate candidates.
- It does not validate a production design loop.

---

## Current Default Outcome

With the default grid and thresholds, the bounded critic summary orders the
cases from lower to higher descriptor complexity as:

1. `straight_channel`
2. `single_obstruction`
3. `constricted_channel`

This ordering is local to this sandbox setup only.

---

## Recommendation

Recommendation: `continue`

Reason:
- the descriptors are deterministic
- the cases are clearly separable
- the provenance classes remain explicit

Continue means only that a later multi-slice or simple 3D critic phase appears
worth testing. It does not authorize broader claims.
