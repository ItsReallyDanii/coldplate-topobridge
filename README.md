# coldplate-topobridge

**A bounded bridge from coldplate flow-field artifacts to topology-style descriptor artifacts.**

This repository exists to test a narrow question:

> Can coldplate field artifacts be converted into stable, reproducible, explicitly bounded descriptor summaries without pretending that this already proves vortex physics, TopoStream equivalence, or 3D ranking power?

That is the scope.

This repo is **not** a grand “physics solved” engine.  
It is a **bridge / methodology artifact** with an experimental sandbox.

---

## Status

**Current status:** active bridge repo with a completed bounded 2D analytical critic sandbox and a bounded multi-slice / simple 3D proxy critic sandbox.

### What is implemented
- Read-only experimental handling of upstream coldplate-style field artifacts
- Bridge-local descriptor generation and packaging
- Deterministic sandbox field generation for simple 2D cases
- Deterministic stacked-slice sandbox generation for a simple 3D proxy
- Explicit provenance labeling for generated cases:
  - `EXACT_ANALYTIC`
  - `QUASI_ANALYTICAL`
  - `SYNTHETIC`
- Tests for determinism, controls, analytical 2D critic behavior, and multi-slice simple 3D proxy critic behavior
- Documentation that explicitly separates:
  - what is proven
  - what is not proven
  - what remains experimental

### What is **not** claimed
- No proof of physical realism for sandbox cases or stacked-slice proxies
- No proof of vortex correspondence
- No proof of TopoStream semantic compatibility
- No validation of ranking for 3D TPMS coldplate candidates
- No fabrication or hardware validation
- No broad CFD-equivalence claim

---

## Why this repo exists

The larger coldplate project needs a disciplined middle layer between:

1. **field-producing workflows**  
2. **descriptor / topology-style summaries**  
3. **later evaluation or critic experiments**

This repo is that middle layer.

Its job is to:
- take bounded field-like inputs,
- generate structured descriptor summaries,
- keep provenance explicit,
- keep outputs reproducible,
- and keep the claim boundary honest.

If the descriptors are stable and separable, the idea earns the right to continue.

If not, this repo should say so directly instead of dressing up weak signal with fancy words.

---

## What this repository currently does

At a high level, this repo supports a workflow like:

```text
bounded field input
    -> descriptor extraction
    -> structured bridge-style summary
    -> deterministic artifact bundle
    -> explicit proof / non-proof boundary
```

The implemented experimental lanes are:

- the **analytical 2D critic sandbox** with `straight_channel`, `single_obstruction`, and `constricted_channel`
- the **multi-slice / simple 3D proxy critic sandbox** with `straight_stack`, `obstruction_stack`, and `constriction_stack`

These lanes are intentionally narrow and bounded. They exist to test whether the descriptor layer can produce stable, structured separation across controlled cases without overclaiming what that means.

---

## Analytical 2D critic sandbox

The current sandbox includes three provenance classes:

| Case | Provenance class | Notes |
|---|---|---|
| `straight_channel` | `EXACT_ANALYTIC` | clean baseline |
| `single_obstruction` | `SYNTHETIC` | deliberately bounded synthetic disturbance |
| `constricted_channel` | `QUASI_ANALYTICAL` | simplified structured constriction case |

Example descriptor outputs include values such as:
- `theta_std_rad`
- `deflection_fraction`
- `acceleration_ratio`
- descriptor token summaries such as:
  - `AXIAL_VARIATION_LOW`
  - `DEFLECTION_LOCALIZED_MODERATE`
  - `ACCELERATION_BAND_HIGH`
  - `CRITIC_COMPLEXITY_HIGH`

The bounded ordering observed in the sandbox was:

```text
straight_channel < single_obstruction < constricted_channel
```

The current recommendation in the sandbox output is:

```text
continue
```

That means only this:

> the descriptor layer appears stable and separable enough in this bounded 2D sandbox to justify a later, still-explicitly-experimental follow-up such as a multi-slice or simple 3D proxy critic phase.

It does **not** mean the repo has validated real 3D ranking power.

---

## Multi-slice / simple 3D proxy critic sandbox

The bounded follow-up lane models a simple 3D proxy as deterministic stacks of
2D slices with controlled variation.

The sandbox includes three provenance classes:

| Case | Provenance class | Notes |
|---|---|---|
| `straight_stack` | `EXACT_ANALYTIC` | repeated analytic baseline slices |
| `obstruction_stack` | `SYNTHETIC` | deterministic obstruction stack with slice-to-slice variation |
| `constriction_stack` | `QUASI_ANALYTICAL` | deterministic constriction stack with smooth z-variation |

The bounded ordering observed in the default stack sandbox is:

```text
straight_stack < obstruction_stack < constriction_stack
```

The current recommendation in the stack sandbox output is:

```text
continue
```

That means only this:

> descriptor separation remains stable enough in a bounded stacked-slice proxy to justify later bounded follow-up work.

It does **not** mean the repo has validated physical realism, TopoStream compatibility, or 3D candidate ranking.

### Bounded robustness sweep

A bounded parameter sweep was run against the stacked-slice proxy across five variants:
`baseline`, `slice_count_5`, `resolution_16x10`, `threshold_0p020`, and `perturbation_0p012`.

The sweep was entirely within the EXPERIMENTAL_SANDBOX and tested only ordering stability
under controlled slice-count, grid-resolution, descriptor-threshold, and deterministic-dither changes.

**Stable across all variants:**
- Ordering stayed `straight_stack < obstruction_stack < constriction_stack` — no flips.
- Recommendation stayed `continue`.
- Every variant kept a documented minimum gap above the 0.08 bounded threshold.
- Provenance classes remained explicit and unchanged.

**Observed under bounded variation:**
- Absolute `stack_complexity_index` values shifted under slice-count, resolution, threshold,
  and perturbation changes. This is expected for sandbox-only ordering metrics.
- Ablation-level descriptor token-bin changes were observed for `slice_count_5`
  (`SLICE_VARIATION_TIGHT` → `SLICE_VARIATION_MODERATE` for `obstruction_stack`).
  This is reported honestly and is not treated as an ordering failure.

This robustness sweep does **not** validate physical realism, vortex correspondence,
TopoStream semantic compatibility, 3D TPMS candidate ranking, or any hydraulic, thermal,
structural, or manufacturing meaning.

---

## What this work proves

At the current stage, this repo supports the following claims:

- deterministic bounded 2D descriptor separation across the defined sandbox cases
- deterministic bounded multi-slice descriptor separation across the defined stacked-slice proxy cases
- ordering stability of the stacked-slice proxy under a bounded parameter sweep (slice-count,
  grid-resolution, descriptor-threshold, deterministic dither) — no ordering flips observed
- explicit provenance separation across:
  - `EXACT_ANALYTIC`
  - `QUASI_ANALYTICAL`
  - `SYNTHETIC`
- **Lane B (2026-03-13):** class-level CV_all(scalar) ordering `ctrl_uniform_channel < ctrl_single_obstruction < stage4_full_cand01/cand02` is stable across all five tested z-slices with no crossover; see `docs/LANE_B_CHECKPOINT.md`

---

## What this work does **not** prove

This repo does **not** prove any of the following:

- physical realism
- vortex correspondence
- TopoStream semantic compatibility
- validation of ranking for 3D TPMS coldplate candidates
- physics validation
- hydraulic, thermal, structural, or manufacturing meaning
- experimental performance claims
- hardware usefulness
- fabrication readiness

This distinction is not a disclaimer buried in the corner.  
It is the central governance rule of the repo.

---

## Repository philosophy

This repo is built around a few simple rules:

### 1) Evidence before vocabulary
A more dramatic name does not make a metric more real.

### 2) Provenance must stay visible
If a case is synthetic, it should be labeled synthetic.  
If a case is quasi-analytical, it should not be quietly treated like exact physics.

### 3) Experimental lanes must stay bounded
A sandbox is useful only if it stays honest about being a sandbox.

### 4) Docs must not outrun implementation
The README should describe what the code actually does today, not what would sound coolest in a pitch deck.

---

## Repository structure

```text
coldplate-topobridge/
├─ docs/
│  ├─ EXPERIMENT_ANALYTICAL_2D_CRITIC.md
│  └─ EXPERIMENT_MULTI_SLICE_3D_CRITIC.md
├─ experiments/
│  ├─ analytical_2d_critic/
│  │  ├─ README.md
│  │  ├─ generate_fields.py
│  │  ├─ extract_descriptors.py
│  │  └─ run_demo.py
│  └─ multi_slice_3d_critic/
│     ├─ README.md
│     ├─ generate_stack.py
│     ├─ extract_descriptors.py
│     └─ run_demo.py
├─ tests/
│  ├─ test_analytical_2d_critic.py
│  ├─ test_multi_slice_3d_critic.py
│  ├─ test_controls.py
│  └─ test_determinism.py
└─ README.md
```

Depending on branch history and future updates, additional bridge code or schema files may exist, but the core current experimental lanes are the bounded analytical 2D workflow and the bounded multi-slice simple-3D proxy workflow above.

---

## Running the experimental demos

Analytical 2D:

```bash
python experiments/analytical_2d_critic/run_demo.py --output-root ./tmp/analytical_2d_critic_demo
```

Multi-slice / simple 3D proxy:

```bash
python experiments/multi_slice_3d_critic/run_demo.py --output-root ./tmp/multi_slice_3d_critic_demo
```

Run the sandbox critic tests:

```bash
python -m pytest tests/test_analytical_2d_critic.py tests/test_multi_slice_3d_critic.py
```

Run supporting determinism and control tests:

```bash
python -m pytest tests/test_determinism.py tests/test_controls.py
```

On Windows, use backslashes if preferred.

---

## Expected outputs

A demo run is expected to produce structured artifacts such as:
- generated field data
- extracted descriptor summaries
- comparison or critic summary files
- provenance-tagged outputs
- a bounded recommendation such as `continue`

The important property is not flashy output volume.  
The important property is that the outputs are:

- reproducible
- interpretable
- provenance-aware
- claim-bounded

---

## Why the bounded result matters

A lot of technical projects die in a weird swamp where the code exists, the language gets dramatic, and nobody can say exactly what has been shown.

This repo is trying to avoid that swamp.

A narrow but real result is better than a grand but mushy one.

Right now, the honest result is:

> the descriptor layer appears workable in bounded 2D and stacked-slice proxy sandboxes, but it has **not** yet earned stronger claims.

That is a respectable state for a bridge repo.

---

## Non-goals

This repository is **not** currently trying to be:
- a full CFD solver
- a validated thermal performance engine
- a fabrication pipeline
- a production optimizer
- a replacement for real experimental validation
- a proof that topology language transfers cleanly from one scientific domain to another

---

## Current verdict

**This is a legitimate experimental bridge artifact.**

It is not a finished scientific result, and it does not pretend to be one.

That is exactly why it is useful.

---

## Proof / non-proof boundary

The current implementation proves deterministic bounded 2D descriptor separation across the defined sandbox cases and deterministic bounded multi-slice descriptor separation across the defined stacked-slice proxy cases, with explicit provenance separation (`EXACT_ANALYTIC`, `QUASI_ANALYTICAL`, `SYNTHETIC`). A bounded parameter sweep of the stacked-slice proxy confirmed the documented ordering (`straight_stack < obstruction_stack < constriction_stack`) was stable across all tested variants, with the documented minimum gap above 0.08 retained in every variant; ablation-level token-bin shifts were observed at `slice_count_5` and `resolution_10x6` and are reported honestly. It does **not** prove physical realism, does **not** prove vortex correspondence, does **not** prove TopoStream semantic compatibility, does **not** validate ranking of 3D TPMS coldplate candidates, does **not** imply hydraulic, thermal, structural, or manufacturing meaning, and does **not** validate physics.

---

## Related note

No validated Stage 4 files were changed as part of the analytical 2D critic addition or the multi-slice / simple 3D proxy critic addition. The sandboxes are intentionally isolated so that bounded experimentation does not silently rewrite stronger evidence lanes.

[![codecov](https://codecov.io/github/ItsReallyDanii/coldplate-topobridge/graph/badge.svg?token=M4AYW3VIV1)](https://codecov.io/github/ItsReallyDanii/coldplate-topobridge)
