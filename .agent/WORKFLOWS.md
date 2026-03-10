# WORKFLOWS.md
# Agent Workflows — coldplate-topobridge

## Stage 1: Run the full bridge pipeline

```bash
# Install bridge
pip install -e .

# Run bridge on a field artifact (synthetic example)
python -m topobridge.cli run examples/minimal/synthetic_field.npz \
    --output artifacts/run_001 \
    --source-repo coldplate-design-engine \
    --stage stage1_2d

# Validate artifact bundle
python -m topobridge.cli validate artifacts/run_001/manifest.json

# Run tests
pytest tests/ -v
```

## Stage 1: Generate synthetic test field

```bash
python -c "
import numpy as np
ny, nx = 32, 32
u = np.ones((ny, nx), dtype=np.float64)
v = np.zeros((ny, nx), dtype=np.float64)
solid_mask = np.zeros((ny, nx), dtype=np.uint8)
np.savez('examples/minimal/synthetic_field.npz', u=u, v=v, solid_mask=solid_mask)
print('Saved synthetic uniform-flow field.')
"
```

## Stage 1: Validate bridge-local schemas

```bash
python -m topobridge.io.schema_validate \
    artifacts/run_001/field_contract.json \
    schemas/bridge_field_frame.schema.json
```

## Escalation workflow

1. If a run fails with `ESCALATE:` prefix in stderr, stop immediately.
2. Write a `BLOCKER_REPORT.md` at the repo root with:
   - Failure class
   - Repair attempts (max 2)
   - Root cause
   - What is needed to proceed
3. Do NOT attempt workaround beyond 2 repair loops.

## Adding a new field artifact

1. Place artifact in `artifacts/` as `.npz` with keys: `u`, `v`, `solid_mask`.
   Optional keys: `scalar`.
2. Write a sidecar `{artifact_name}.meta.json` with provenance metadata
   matching `docs/FIELD_CONTRACT.md`.
3. Run `python -m topobridge.cli run` with `--source-repo` and `--stage` flags.
4. Check `manifest.json` for hash verification.
