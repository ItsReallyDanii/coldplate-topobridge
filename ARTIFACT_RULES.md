# ARTIFACT_RULES.md
# Artifact Rules — coldplate-topobridge
# Version: 1.0.0
# Date: 2026-03-10

---

## 1. Artifact Directory

All bridge output artifacts are written to `artifacts/`. The directory is tracked with
a `.gitkeep` placeholder only. Actual run outputs are gitignored.

Add to `.gitignore`:
```
artifacts/run_*/
artifacts/*.npz
artifacts/*.npy
```

---

## 2. Required Files Per Run

Every successful bridge run MUST produce exactly these files in the output directory:

| File | Schema | Description |
|---|---|---|
| `field_contract.json` | `bridge_field_frame.schema.json` | Validated provenance + field metadata |
| `signatures.jsonl` | `bridge_signature_stream.schema.json` (per line) | Bridge-local signature records, one per pixel/cell |
| `summary.json` | inline (no external schema) | Run-level statistics and flags |
| `manifest.json` | inline | File hashes + run context |

---

## 3. Naming Convention

Run directories: `artifacts/run_{YYYYMMDD_HHMMSS}_{source_artifact_stem}/`

Example: `artifacts/run_20260310_175615_synthetic_field/`

---

## 4. Determinism Requirement

Given identical inputs, ALL output artifact hashes MUST be identical across reruns.

Sources of non-determinism that MUST be avoided:
- `datetime.now()` in computed fields (use input-derived timestamps only)
- `uuid` in per-record IDs (use deterministic hash-based IDs)
- `dict` ordering (use `sort_keys=True` in all `json.dump` calls)
- Floating-point non-associativity (use fixed ordering for reductions)

---

## 5. Hash Policy

All input artifacts: SHA-256 hash computed from raw bytes, recorded in `field_contract.json`.
All output artifacts: SHA-256 hash computed from written bytes, recorded in `manifest.json`.

Hash failures are hard errors; partial output is never accepted.

---

## 6. Provenance Freeze

Once a `manifest.json` is written to `artifacts/`, the run is frozen.
To re-run: create a new output directory with a new timestamp.
Do NOT overwrite existing run output directories.

---

## 7. Sensitive Field Policy

Bridge runs do NOT require secrets. No API keys, credentials, or private data are stored
in `artifacts/`. If input field data is proprietary, use gitignore to exclude it from
version control.

---

## 8. What Artifacts Are NOT

- NOT papers or dashboards
- NOT TopoStream token streams (Stage 1)
- NOT validated physics outputs (see `CLAIM_TIERS.md`)
