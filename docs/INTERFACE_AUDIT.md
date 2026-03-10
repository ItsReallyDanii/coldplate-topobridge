# docs/INTERFACE_AUDIT.md
# Interface Audit — coldplate-topobridge
# Status: IMPLEMENTED (audit complete, bridge layer created)
# Date: 2026-03-10

---

## 1. Audit Scope

Read-only audit of both parent repositories.
No files were modified in either parent repo.

---

## 2. coldplate-design-engine — Audit Summary

### 2.1 Repository Layout

```
coldplate-design-engine/
  src/
    stage1_2d/          ← geometry generators, metrics, masks, IO, provenance
    stage2_inverse/     ← inverse design optimizer
    stage3_geometry/    ← 3D geometry promotion
    stage4_sim/         ← flow simulation (CFD-like)
    stage5_thermal/     ← thermal analysis
    stage6_structural/  ← structural screening
  data/                 ← .gitkeep only (no field artifacts persisted in repo)
  results/              ← run outputs (not in repo)
  baselines/            ← geometry families reference
```

### 2.2 Primary Outputs (Stage 1)

| Output | Format | Contents | Status |
|---|---|---|---|
| Binary masks | `.npy` uint8 | 2D arrays: 1=fluid, 0=solid | IMPLEMENTED in engine |
| Metric results | `.json` | 12+ proxy metrics per mask | IMPLEMENTED in engine |
| Sweep manifest | `.json` | Run provenance, git SHA | IMPLEMENTED in engine |

### 2.3 Key Finding: No Native Vector Field Output

**FINDING:** `coldplate-design-engine` Stage 1 produces **binary solid masks only**.
It does NOT produce u/v velocity fields, pressure fields, or scalar temperature fields
as stable file artifacts at Stage 1.

- Stage 4 (`stage4_sim`) performs flow simulation, but output format and stability
  were not audited in this run (data/ is empty in the read copy).
- Stage 5 produces thermal outputs but again: no confirmed stable artifact in `data/`.

**Implication for bridge:** The bridge field contract (`docs/FIELD_CONTRACT.md`) defines
a vector-field bundle as the canonical input. In Stage 1, this bundle MUST be provided
externally (e.g., from a CFD post-processing step, or synthetically generated for testing).
The bridge does NOT infer flow fields from masks alone.

**Claim tier:** IMPLEMENTED (bridge reads externally-provided fields).
**Claim tier:** NOT_PROVEN (any correspondence between mask geometry and field structure).

### 2.4 Stable Interface Points

| Interface | Module | Description |
|---|---|---|
| `BaselineFamily` enum | `stage1_2d/schemas.py` | 6 geometry families |
| `GridConfig` dataclass | `stage1_2d/schemas.py` | Grid shape (nx, ny, dx, dy) |
| `generate_baseline_mask()` | `stage1_2d/generators.py` | Returns (mask, metadata) |
| `get_git_sha()` | `stage1_2d/provenance.py` | Git provenance capture |
| `save_mask()` / `load_mask()` | `stage1_2d/io.py` | `.npy` round-trip |

### 2.5 What Bridge May Reference (No Import Required)

The bridge may reference:
- Provenance metadata written by the engine (git SHA, family, seed, shape)
- The `.npy` mask file format for the `solid_mask` component of the field bundle
- The `GridConfig` convention (nx, ny, dx, dy)

The bridge MUST NOT:
- Import `stage1_2d` at runtime
- Depend on engine internal module structure

---

## 3. topostream_stage0_specs — Audit Summary

### 3.1 Repository Layout

```
topostream_stage0_specs/
  src/topostream/
    simulate/     ← XY/clock MC simulation
    extract/      ← vortex extraction
    aggregate/    ← pairing, metrics
    analysis/     ← UQ, sweep analysis
    map/          ← map-mode adapters (Stage 3)
    io/           ← schema validation
    cli.py        ← CLI entrypoint
  schemas/
    topology_event_stream.schema.json  ← v1.1.0, vortex/pair/sweep_delta tokens
  docs/
    SPEC_INPUTS.md     ← angle field and map mode
    SPEC_ALGORITHMS.md ← vortex extraction, pairing, MC
    SPEC_UQ.md         ← uncertainty quantification
    SPEC_FORMULAE.md   ← formulae
    SPEC_METRICS.md    ← metric definitions
    SPEC_VALIDATION.md ← validation protocol
```

### 3.2 Token Schema (v1.1.0)

```json
{
  "schema_version": "string",
  "token_type": "vortex" | "pair" | "sweep_delta",
  "provenance": { "model": "XY"|"clock6"|"map_mode", "L", "T", "seed", "sweep_index", ... },
  "vortex": { "id", "x", "y", "charge": -1|1, "strength", "confidence" },
  ...
}
```

**Key token semantics (DO NOT apply to bridge outputs):**
- `charge` ∈ {-1, +1}: sign of winding number on a plaquette
- `strength` = |W_raw| ≈ 1 for well-resolved spin vortex
- `confidence` = 1 − σ/μ across MC seeds
- `L` = lattice size; periodic boundary conditions REQUIRED

### 3.3 What Bridge May Reference

The bridge may treat TopoStream as a **reference architecture** for:
- Provenance field structure (model, seed, schema_version)
- Determinism requirements (identical seed → identical output)
- Plaquette-based angle computation concept (as computational pattern, NOT semantic)

The bridge MUST NOT:
- Produce `charge ∈ {-1, +1}` labels on coldplate-derived fields
- Use `model: "XY"` or `model: "clock6"` in bridge provenance
- Claim `map_mode` adapter compatibility without explicit mapping validation

### 3.4 Semantic Boundary

| TopoStream concept | Bridge-local concept | Relationship |
|---|---|---|
| Spin angle `θ(x,y)` ∈ [−π, π) | Bridge angle `θ_bridge(x,y) = atan2(v, u)` | Computational analogy; NO physical equivalence |
| Winding number ∈ {-1,0,+1} | Bridge signature descriptor (float, unlabeled) | Different domain; not directly comparable |
| XY model temperature T | Not present in bridge | No mapping defined |
| Vortex charge | Not in bridge (FORBIDDEN by guardrails) | DO NOT map |

---

## 4. Summary: What Bridge Stage 1 Achieves

| Capability | Status | Tier |
|---|---|---|
| Read coldplate binary mask (solid_mask) | IMPLEMENTED | IMPLEMENTED |
| Read externally-provided u/v vector field | IMPLEMENTED | IMPLEMENTED |
| Compute bridge angle field θ = atan2(v, u) | IMPLEMENTED | IMPLEMENTED |
| Compute low-signal mask (|u|² + |v|² < threshold) | IMPLEMENTED | IMPLEMENTED |
| Compute bridge-local descriptors | IMPLEMENTED | IMPLEMENTED |
| Validate provenance hash | IMPLEMENTED | IMPLEMENTED |
| Emit deterministic artifact bundle | IMPLEMENTED (pending test run) | IMPLEMENTED |
| Produce TopoStream-compatible tokens | NOT IMPLEMENTED (not a Stage 1 goal) | NOT_PROVEN |
| Claim physics equivalence between domains | EXPLICITLY FORBIDDEN | NOT_PROVEN |

---

## 5. Open Escalation Questions

None escalated at this stage. The only structural gap (no native vector field in engine Stage 1)
is handled by specifying the field contract as externally-provided.
If Stage 4/5 outputs become stable, a future audit pass should confirm their artifact schema
before any automatic ingestion.
