"""coldplate-topobridge: Bridge layer between coldplate-design-engine and topostream_stage0_specs.

Stage 1: Read-only ingestion layer.

This package:
- Reads frozen 2D field artifacts (u, v, solid_mask, optional scalar)
- Validates provenance
- Encodes to bridge-local signature stream (theta = atan2(v, u) + descriptors)
- Emits deterministic artifact bundle

It does NOT:
- Import coldplate-design-engine or topostream_stage0_specs at runtime
- Produce TopoStream token_type records
- Claim physics equivalence between domains
- Modify either parent repo

See docs/FIELD_CONTRACT.md and CLAIM_TIERS.md for epistemic constraints.
"""

__version__ = "0.1.0"
__schema_version__ = "1.0.0"
__stage__ = "stage1_bridge_readonly"
