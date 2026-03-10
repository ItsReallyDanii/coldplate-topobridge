# AGENT_MISSION.md
# Bridge Agent Mission — coldplate-topobridge
# Stage: 1 (Read-only bridge layer)
# Date: 2026-03-10

## Purpose

Build the smallest credible, evidence-first thin bridge between:
- **coldplate-design-engine** (geometry + metric evaluation for cold-plate internal architectures)
- **topostream_stage0_specs** (XY/clock-model spin-topology stream for physical phase analysis)

This bridge is a **read-only ingestion layer** only. It does not modify either parent repo.
It does not claim integration. It does not claim topology-aware design is achieved.

## What This Bridge Does (Stage 1)

1. Reads a frozen 2D field artifact (u, v, optional scalar, solid_mask + provenance metadata)
   produced externally and conforming to `docs/FIELD_CONTRACT.md`.
2. Validates artifact provenance (hash, source, shape, dtype).
3. Encodes the field into a **bridge-local signature stream** (angle + low-signal mask + descriptors).
4. Emits a deterministic artifact bundle: `field_contract.json`, `signatures.jsonl`,
   `summary.json`, `manifest.json`.

## What This Bridge Does NOT Do

- Does NOT import or execute parent repo internals.
- Does NOT modify either parent repo.
- Does NOT produce TopoStream-schema-compatible tokens (that is a future stage decision).
- Does NOT claim spin defects == fluid vortices.
- Does NOT claim "topology-aware design stack" is achieved.
- Does NOT claim scientific validity for any mapping.

## Escalation Conditions

Stop and write a blocker report if:
1. No stable field artifact is available to ingest.
2. Proceeding requires importing parent repo internals at runtime.
3. Semantic meaning of the bridge signature stream requires a physics analogy not documented here.
4. Bridge-local schema is insufficient and TopoStream schema *changes* seem required.

## Repair Policy

- Max 2 repair loops per failure class.
- On 3rd failure in same class: stop and write `BLOCKER_REPORT.md`.
