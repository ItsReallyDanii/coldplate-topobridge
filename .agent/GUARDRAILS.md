# GUARDRAILS.md
# Hard Guardrails — coldplate-topobridge

## What MAY NOT be written or claimed in any file in this repo

1. **No physics analogy conflation**
   - DO NOT equate bridge-local angle signatures with spin-field vortex charges.
   - DO NOT equate coldplate flow recirculation with XY-model vortex-antivortex pairs.
   - DO NOT state that fluid vortices are topologically equivalent to spin defects.

2. **No TopoStream schema forced mapping**
   - DO NOT emit records conforming to `topology_event_stream.schema.json` *as if* they
     represent XY-model outputs.
   - DO NOT label bridge descriptors as `token_type: vortex`, `pair`, or `sweep_delta`.
   - BRIDGE-LOCAL schemas only in Stage 1 outputs.

3. **No integration claims**
   - DO NOT write "this completes integration with TopoStream."
   - DO NOT write "topology-aware design stack is operational."
   - Stage 1 establishes plumbing only; claims require validated bridge outputs.

4. **No unsupported promotion up CLAIM_TIERS**
   - DO NOT promote any claim to VALIDATED unless deterministic rerun AND both controls pass.
   - DO NOT promote to PROVEN from this repo alone.

5. **No parent-repo modification**
   - DO NOT write to `../coldplate-design-engine/**`.
   - DO NOT write to `../topostream_stage0_specs/**`.

6. **No paper-style or dashboard artifacts**
   - DO NOT create Jupyter notebooks, HTML dashboards, or paper-style LaTeX in this run.

7. **No new subprojects**
   - DO NOT create new top-level packages outside `src/topobridge/`.

## Claim Tier Reference

See `CLAIM_TIERS.md` for tier definitions.
Every claim in `docs/` must carry an explicit tier label: IMPLEMENTED, VALIDATED, HYPOTHESIS, NOT_PROVEN.
