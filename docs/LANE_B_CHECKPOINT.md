# Lane B Checkpoint: Cross-z Scalar CV Analysis
# Date: 2026-03-13

## Method

Source: `signatures.jsonl` artifacts for four runs across five z-slices (z5, z15, z25, z35, z45).

Metric definitions:
- **NON_SOLID**: pixels where `is_solid == false`
- **vz**: `scalar` field value per pixel
- **CV_all(vz)**: population std(scalar over NON_SOLID) / mean(scalar over NON_SOLID)
- **low_signal_fraction**: fraction of NON_SOLID pixels with `is_low_signal == true`

## Cross-z Table

| Run | z | n_non_solid | mean_all(vz) | std_all(vz) | CV_all(vz) | low_signal_fraction |
|---|---|---|---|---|---|---|
| stage4_full_cand01 | z5  | 1402 | 139.109 | 33.183 | 0.239 | 0.0000 |
| stage4_full_cand01 | z15 | 1362 | 140.012 | 24.675 | 0.176 | 0.0007 |
| stage4_full_cand01 | z25 | 1406 | 138.919 | 35.058 | 0.252 | 0.0000 |
| stage4_full_cand01 | z35 | 1382 | 139.338 | 30.096 | 0.216 | 0.0000 |
| stage4_full_cand01 | z45 | 1371 | 140.124 | 28.037 | 0.200 | 0.0022 |
| stage4_full_cand02 | z5  | 1422 | 140.439 | 32.524 | 0.232 | 0.0000 |
| stage4_full_cand02 | z15 | 1380 | 141.863 | 24.147 | 0.170 | 0.0014 |
| stage4_full_cand02 | z25 | 1426 | 140.370 | 34.734 | 0.247 | 0.0000 |
| stage4_full_cand02 | z35 | 1396 | 141.262 | 29.033 | 0.206 | 0.0000 |
| stage4_full_cand02 | z45 | 1405 | 140.640 | 27.819 | 0.198 | 0.0028 |
| ctrl_uniform_channel | z5  | 2500 | 204.082 | 0.000 | 0.000 | 1.0000 |
| ctrl_uniform_channel | z15 | 2500 | 204.082 | 0.000 | 0.000 | 1.0000 |
| ctrl_uniform_channel | z25 | 2500 | 204.082 | 0.000 | 0.000 | 1.0000 |
| ctrl_uniform_channel | z35 | 2500 | 204.082 | 0.000 | 0.000 | 1.0000 |
| ctrl_uniform_channel | z45 | 2500 | 204.082 | 0.000 | 0.000 | 1.0000 |
| ctrl_single_obstruction | z5  | 2500 | 198.114 | 11.140 | 0.056 | 0.0672 |
| ctrl_single_obstruction | z15 | 2400 | 206.369 | 2.893 | 0.014 | 0.0000 |
| ctrl_single_obstruction | z25 | 2400 | 206.369 | 1.210 | 0.006 | 0.0000 |
| ctrl_single_obstruction | z35 | 2400 | 206.369 | 3.477 | 0.017 | 0.0017 |
| ctrl_single_obstruction | z45 | 2500 | 198.114 | 9.718 | 0.049 | 0.0448 |

## Result

Across all five tested z-slices, CV_all(vz) ordering is consistent with no crossover:

```
ctrl_uniform_channel (0.000) < ctrl_single_obstruction (0.006–0.056) < stage4_full_cand01/cand02 (0.170–0.252)
```

`ctrl_uniform_channel` holds CV = 0.000 at every slice (constant scalar field; all NON_SOLID pixels flagged low-signal).
`ctrl_single_obstruction` CV ranges 0.006–0.056 across slices.
Both candidate runs occupy the range 0.170–0.252 with a mild z15 dip (lower std, lower CV) observed in both.

## What is supported

- **Class-level CV separation across all tested slices.** The three run classes occupy non-overlapping CV ranges at every z with no ordering flip.
- **cand01 and cand02 are indistinguishable at this aggregation level.** CV difference between the two candidates is ≤ 0.007 at every slice. The scalar-based descriptor does not resolve the two designs.

## What is not supported

- **Candidate-level ranking.** The descriptor does not separate cand01 from cand02.
- **Physical validation.** The scalar field's relationship to flow, heat transfer, or any physical target is unestablished. Every artifact carries explicit `NOT_PROVEN` flags covering physical interpretation, flow topology correspondence, and TopoStream semantic equivalence.
- **Family-general claims.** Results cover two candidate instances and two controls in one constrained pipeline run. No generalization to the broader TPMS family or other geometries is warranted.

## Status

- USABLE FOR CLASS-LEVEL SCREENING
- NOT USABLE FOR CANDIDATE-LEVEL RANKING
- STILL NOT PHYSICS-VALIDATED
