# CLAIM_TIERS.md
# Claim Tiers — coldplate-topobridge
# Version: 1.0.0
# Date: 2026-03-10

Every claim in this repository MUST carry one of the four tier labels below.
Promotion between tiers requires explicit gate criteria to be met.

---

## Tier 0 — IMPLEMENTED

**Definition:** Code exists and executes without error on at least one test input.

**Does NOT imply:**
- Correct output
- Validated behavior
- Physical meaning

**Gate criteria:**
- [ ] Code runs without exception
- [ ] Basic smoke test passes

**Known examples in this repo (Stage 1):**
- IMPLEMENTED: Field loader reads `.npz` and computes SHA-256 hash
- IMPLEMENTED: Bridge encoder computes `theta = atan2(v, u)` from input field
- IMPLEMENTED: Artifact bundle is written to output directory

---

## Tier 1 — VALIDATED

**Definition:** Output is deterministic across reruns AND both control tests pass.

**Does NOT imply:**
- Physical correctness
- Statistical significance
- TopoStream compatibility

**Gate criteria (ALL must pass):**
- [x] Deterministic rerun test passes (identical hash on second run with same input)
- [x] Negative control (G5): uniform channel yields machine-epsilon transverse flow (transverse_max_ratio < 1e-5)
- [x] Positive control (G6): single-obstruction flow yields non-zero theta_std (> 0.1 rad above baseline)
- [x] Schema validation passes on all outputs

**Current Status (2026-03-10):** Stage 4 real-artifact ingestion is **VALIDATED** per `docs/CHECKPOINT_STATUS.md`.

---

## Tier 2 — HYPOTHESIS

**Definition:** A claim that is plausible given current evidence but not yet tested.

**Examples:**
- HYPOTHESIS: Bridge-local angle signatures may correlate with geometry-level flow complexity
- HYPOTHESIS: High-angle-variance regions in the signature stream correspond to high-resistance
  zones in coldplate geometry

**Does NOT imply:**
- Causation
- Physical mechanism
- Validated correspondence

**Requirement:** Every HYPOTHESIS must cite the evidence it is based on.

---

## Tier 3 — NOT_PROVEN

**Definition:** A claim that would be scientifically interesting but has NOT been established
by any evidence in this repo or its parent repos.

**Examples:**
- NOT_PROVEN: Bridge signatures predict real thermal performance
- NOT_PROVEN: TopoStream vortex tokens and bridge angle signatures measure the same phenomenon
- NOT_PROVEN: Any topological quantity from bridge outputs correlates with manufacturing outcomes

**Policy:** NOT_PROVEN claims may be listed in `docs/UNCERTAINTIES.md` as open questions only.
They MUST NOT appear as factual assertions in code comments, docstrings, or README files.

---

## Tier Promotion Policy

```
IMPLEMENTED → VALIDATED: requires deterministic rerun + both controls passing
VALIDATED → HYPOTHESIS: requires a specific, testable mechanism statement + supporting evidence
HYPOTHESIS → PROVEN: OUTSIDE SCOPE of this repo (requires peer review / CFD / bench data)
```

**STOP condition:** No claim in this repo will be labeled PROVEN. This repo is a bridge layer,
not a validation study.
