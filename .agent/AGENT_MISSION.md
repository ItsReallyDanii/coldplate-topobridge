# coldplate-topobridge — bounded audit pass

Audit the current `coldplate-topobridge` repository after the `analytical_2d_critic` addition.

## Goal
Verify that the repo is internally consistent and that all documentation preserves the exact experimental claim boundary.

## Files to inspect
- `README.md`
- `experiments/analytical_2d_critic/README.md`
- `docs/EXPERIMENT_ANALYTICAL_2D_CRITIC.md`
- `tests/test_analytical_2d_critic.py`

## Required checks

### 1) Claim boundary consistency
Confirm that all wording stays aligned with this exact boundary:

**What this work proves**
- deterministic bounded 2D descriptor separation across the defined sandbox cases
- explicit provenance separation across:
  - `EXACT_ANALYTIC`
  - `QUASI_ANALYTICAL`
  - `SYNTHETIC`

**What this work does NOT prove**
- physical realism for synthetic cases
- vortex correspondence
- TopoStream semantic compatibility
- validation of ranking for 3D TPMS coldplate candidates

### 2) Repo framing
Confirm the root `README.md` presents this repository as:
- a bridge / methodology artifact
- an experimental descriptor sandbox
- not a validated physics-ranking engine
- not a full 3D coldplate validation repo

### 3) Provenance terminology
Check that provenance labels are used consistently everywhere:
- `EXACT_ANALYTIC`
- `QUASI_ANALYTICAL`
- `SYNTHETIC`

Flag any drift, synonym use, capitalization mismatch, or ambiguous phrasing.

### 4) Experimental scope discipline
Check that no file accidentally overstates:
- “validation”
- “compatibility”
- “physical correspondence”
- “3D ranking power”
- “vortex truth”

If any wording implies stronger claims than the implemented sandbox supports, tighten it.

### 5) Test/document alignment
Confirm the tests and docs agree on:
- implemented cases
- expected bounded ordering
- deterministic behavior
- recommendation status meaning

## Constraints
- Do NOT expand scope.
- Do NOT add new experiments.
- Do NOT modify validated Stage 4 files.
- Do NOT introduce new scientific claims.
- If edits are needed, keep them minimal and limited to consistency/documentation corrections.

## Return format
Return exactly:

### Verdict
A short verdict on whether the repo is currently consistent and honest.

### Issues found
A concise bullet list of any inconsistencies, overclaims, stale wording, or naming drift.

### Files changed
List exact files changed, or say `none`.

### Wording tightened
Quote the exact wording that was corrected.

### Final claim boundary
Provide one clean paragraph stating the proof / non-proof boundary for this repo exactly as supported by the current implementation.