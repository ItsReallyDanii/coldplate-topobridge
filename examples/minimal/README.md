# Minimal Example — coldplate-topobridge Stage 1

## What this demonstrates

This example runs the bridge pipeline on a **synthetic field** (not a real CFD output).

It demonstrates:
- IMPLEMENTED: Field loading + provenance validation
- IMPLEMENTED: Bridge angle encoding (theta = atan2(v, u))
- IMPLEMENTED: Deterministic artifact bundle emission
- NOT_PROVEN: Any physical correspondence of the resulting signatures

---

## Step 1: Install the bridge

```bash
cd /path/to/coldplate-topobridge
pip install -e .
```

---

## Step 2: Generate a synthetic field artifact

Run from the repo root:

```bash
python - <<'EOF'
import numpy as np, json
from pathlib import Path

out = Path("examples/minimal")
out.mkdir(parents=True, exist_ok=True)

# --- Synthetic swirl field ---
ny, nx = 32, 32
cy, cx = ny / 2, nx / 2
y, x = np.mgrid[:ny, :nx]
dy, dx = (y - cy).astype(float), (x - cx).astype(float)
mag = np.sqrt(dx**2 + dy**2) + 1e-10
u = (-dy / mag)
v = (dx / mag)
solid_mask = np.zeros((ny, nx), dtype=np.uint8)
# Pin-fin-like obstacle in center
solid_mask[14:18, 14:18] = 1

np.savez("examples/minimal/synthetic_swirl.npz", u=u, v=v, solid_mask=solid_mask)

meta = {
    "schema_version": "1.0.0",
    "source_repo": "synthetic",
    "source_stage": "stage0_synthetic",
    "source_artifact": "synthetic_swirl.npz",
    "source_commit": None,
    "preprocessing": ["synthetic_generated_for_example"],
    "grid_nx": nx, "grid_ny": ny,
    "grid_dx": None, "grid_dy": None,
    "field_frozen_at": "2026-03-10T17:00:00Z"
}
with open("examples/minimal/synthetic_swirl.meta.json", "w") as f:
    json.dump(meta, f, indent=2)

print("Synthetic swirl field written.")
EOF
```

---

## Step 3: Run the bridge

```bash
python -m topobridge.cli run examples/minimal/synthetic_swirl.npz \
    --output artifacts/example_swirl
```

Expected output:
```
[bridge:run] Input: .../examples/minimal/synthetic_swirl.npz
[bridge:run] Loaded field: shape=(32, 32), sha256=...
[bridge:run] Encoded: n_active=..., n_solid=..., n_low_signal=..., theta_std=...
[bridge:run] Artifact bundle written to: .../artifacts/example_swirl
[bridge:run] Run SHA256: ...
[bridge:run] Files: ['field_contract.json', 'signatures.jsonl', 'summary.json']
```

---

## Step 4: Validate the artifact bundle

```bash
python -m topobridge.cli validate artifacts/example_swirl
```

Expected:
```
[bridge:validate] Validating: .../artifacts/example_swirl
[bridge:validate] PASS — all checks passed
  ✓ field_contract.json
  ✓ signatures.jsonl
  ✓ summary.json
  ✓ manifest.json
```

---

## Step 5: Inspect the outputs

```bash
python - <<'EOF'
import json
with open("artifacts/example_swirl/summary.json") as f:
    s = json.load(f)
print("Active pixels:", s["n_active_pixels"])
print("Theta std (rad):", s["theta_stats"]["std_rad"])
print("Gradient mean:", s["gradient_stats"]["mean_grad_mag"])
print()
print("Claim tier:", s["claim_tier"])
print("NOT_PROVEN:", s["NOT_PROVEN"])
EOF
```

---

## What the outputs mean (and don't mean)

| Output field | Meaning | Tier |
|---|---|---|
| `theta_bridge` | atan2(v, u) at each active pixel | IMPLEMENTED |
| `theta_stats.std_rad` | Spatial spread of flow direction | IMPLEMENTED |
| `gradient_stats.mean_grad_mag` | Average spatial change in theta | IMPLEMENTED |
| "Corresponds to a vortex" | **NOT CLAIMED** | NOT_PROVEN |
| "Predicts heat transfer" | **NOT CLAIMED** | NOT_PROVEN |

See `CLAIM_TIERS.md` and `docs/UNCERTAINTIES.md` for full epistemic state.
