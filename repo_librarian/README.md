# repo_librarian

Minimal read-only knowledge catalog sidecar for `coldplate-topobridge`.

## Scope

`repo_librarian` is **not** a chatbot, **not** a scientist, and **not** a discovery engine.
It only records explicit repository knowledge objects and their support/caveats.

This sidecar is intentionally separate from the core pipeline.

## What it tracks

Each catalog entry stores:
- object identity (`entry_id`, `title`, `object_type`, `path`)
- authority/status labels (`lifecycle`, `validation`, `status`)
- claim text
- supporting evidence links (file + line span)
- caveats
- separate ratings for novelty, recency, and credibility

## Files

- `catalog.schema.json` — schema for one catalog entry
- `catalog.jsonl` — line-delimited entry records
- `authority_levels.md` — authority/status semantics
- `check_in.py` — minimal validator + append-only check-in helper

## Minimal usage

Validate current catalog:

```bash
python repo_librarian/check_in.py validate \
  --catalog repo_librarian/catalog.jsonl \
  --schema repo_librarian/catalog.schema.json
```

Append one checked-in file entry:

```bash
python repo_librarian/check_in.py check-in \
  --catalog repo_librarian/catalog.jsonl \
  --entry-id rl_0005 \
  --title "Example" \
  --object-type claim_boundary \
  --path docs/CHECKPOINT_STATUS.md \
  --lifecycle current \
  --validation validated \
  --status active \
  --claim "Protocol-scoped claim boundary." \
  --evidence-file docs/CHECKPOINT_STATUS.md \
  --evidence-lines 44-57 \
  --caveat "No physical ranking claim."
```

Notes:
- No repo discovery logic is included.
- No scientific or physical interpretation is added.
