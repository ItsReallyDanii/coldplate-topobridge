# coldplate-topobridge

**A bounded bridge from coldplate flow-field artifacts to topology-style descriptor artifacts.**

This repository exists to test a narrow question:

> Can coldplate field artifacts be converted into stable, reproducible, explicitly bounded descriptor summaries without pretending that this already proves vortex physics, TopoStream equivalence, or 3D ranking power?

That is the scope.

This repo is **not** a grand “physics solved” engine.  
It is a **bridge / methodology artifact** with an experimental sandbox.

---

## Status

**Current status:** active bridge repo with a completed bounded 2D analytical critic sandbox.

### What is implemented
- Read-only experimental handling of upstream coldplate-style field artifacts
- Bridge-local descriptor generation and packaging
- Deterministic sandbox field generation for simple 2D cases
- Explicit provenance labeling for generated cases:
  - `EXACT_ANALYTIC`
  - `QUASI_ANALYTICAL`
  - `SYNTHETIC`
- Tests for determinism, controls, and analytical 2D critic behavior
- Documentation that explicitly separates:
  - what is proven
  - what is not proven
  - what remains experimental

### What is **not** claimed
- No proof of physical realism for synthetic sandbox cases
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

The current implemented experimental lane is the **analytical 2D critic sandbox**, which creates three simple cases:

- `straight_channel`
- `single_obstruction`
- `constricted_channel`

These are intentionally narrow and bounded. They exist to test whether the descriptor layer can produce **stable, structured separation** across simple cases without overclaiming what that means.

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

> the descriptor layer appears stable and separable enough in this bounded 2D sandbox to justify a later, still-explicitly-experimental follow-up such as a multi-slice or simple 3D critic phase.

It does **not** mean the repo has validated real 3D ranking power.

---

## What this work proves

At the current stage, this repo supports the following claims:

- the sandbox is deterministic
- the three bounded 2D cases produce different structured descriptor summaries
- provenance separation is explicit and clean across:
  - `EXACT_ANALYTIC`
  - `QUASI_ANALYTICAL`
  - `SYNTHETIC`
- the bridge-style descriptor layer is stable enough in this bounded setting to justify a later, still-bounded follow-up experiment

---

## What this work does **not** prove

This repo does **not** prove any of the following:

- physical realism for the synthetic obstruction field
- vortex correspondence
- semantic compatibility with TopoStream
- validity for ranking 3D TPMS coldplate candidates
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
│  └─ EXPERIMENT_ANALYTICAL_2D_CRITIC.md
├─ experiments/
│  └─ analytical_2d_critic/
│     ├─ README.md
│     ├─ generate_fields.py
│     ├─ extract_descriptors.py
│     └─ run_demo.py
├─ tests/
│  ├─ test_analytical_2d_critic.py
│  ├─ test_controls.py
│  └─ test_determinism.py
└─ README.md
```

Depending on branch history and future updates, additional bridge code or schema files may exist, but the core current experimental lane is the bounded analytical 2D critic workflow above.

---

## Running the analytical 2D critic demo

Example:

```bash
python experiments/analytical_2d_critic/run_demo.py --output-root ./tmp/analytical_2d_critic_demo
```

Run the analytical critic test:

```bash
python -m pytest tests/test_analytical_2d_critic.py
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

> the descriptor layer appears workable in a narrow 2D sandbox and is worth a later bounded follow-up, but it has **not** yet earned stronger claims.

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

The current implementation proves that a bounded analytical 2D sandbox can deterministically generate structured bridge-style descriptor summaries across simple cases with explicit provenance separation (`EXACT_ANALYTIC`, `QUASI_ANALYTICAL`, `SYNTHETIC`). It does **not** prove physical realism for synthetic cases, does **not** prove vortex correspondence, does **not** prove TopoStream semantic compatibility, and does **not** validate ranking of 3D TPMS coldplate candidates.

---

## Related note

No validated Stage 4 files were changed as part of the analytical 2D critic addition. The sandbox is intentionally isolated so that bounded experimentation does not silently rewrite stronger evidence lanes.
```
