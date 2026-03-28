# Authority Levels

Authority dimensions are separate on purpose.

## 1) Lifecycle (`authority.lifecycle`)
- `current`: actively authoritative for current repo state
- `historical`: retained as snapshot/history; not current authority
- `sandbox`: bounded experiment lane only

## 2) Validation (`authority.validation`)
- `validated`: passes defined protocol gates in current repo context
- `provisional`: implemented/usable but not fully validated for broader use
- `speculative`: hypothesis-level or weakly grounded
- `blocked`: explicit blocker/open uncertainty prevents promotion

## 3) Status (`authority.status`)
- `active`: intended for normal use
- `deprecated`: superseded and not recommended for new use
- `archived`: preserved record, no active development role

## 4) Independent quality dimensions
These are not authority labels and must stay separate:
- `novelty`: `low | medium | high`
- `recency`: `stale | current | unknown`
- `credibility`: `low | medium | high`

Do not collapse these dimensions into one score.
