#!/usr/bin/env python3
"""Cross-slice gate calculator for bounded comparative descriptor use.

Read-only sidecar tool:
- reads existing bridge summary artifacts across z-slices
- computes cross-z sign stability, flip count, per-candidate mean/std, SNR
- emits PASS / WEAK_PASS / FAIL per metric with explicit gate rule and reason

This tool is methodological only. It does NOT infer physical performance meaning.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List, Tuple


DEFAULT_METRICS = {
    "theta_std": "theta_stats.std_rad",
    "grad_mean": "gradient_stats.mean_grad_mag",
    "solid_fraction": "solid_fraction",
}


@dataclass(frozen=True)
class GateThresholds:
    pass_snr: float = 1.0
    weak_snr: float = 0.5
    weak_flip_max: int = 1


def _extract_value(d: Dict, dotted_path: str) -> float:
    cur = d
    for part in dotted_path.split("."):
        if part not in cur:
            raise KeyError(f"Missing key path '{dotted_path}' (missing '{part}')")
        cur = cur[part]
    return float(cur)


def _load_candidate_series(artifacts_root: Path, run_prefix: str, metric_paths: Dict[str, str]) -> Dict[int, Dict[str, float]]:
    pat = re.compile(r"_z(\d+)$")
    out: Dict[int, Dict[str, float]] = {}

    for run_dir in artifacts_root.glob(f"{run_prefix}_z*"):
        if not run_dir.is_dir():
            continue
        m = pat.search(run_dir.name)
        if not m:
            continue
        z = int(m.group(1))
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            continue

        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        out[z] = {name: _extract_value(summary, path) for name, path in metric_paths.items()}

    return dict(sorted(out.items(), key=lambda kv: kv[0]))


def _sign(x: float, eps: float) -> int:
    if x > eps:
        return 1
    if x < -eps:
        return -1
    return 0


def _flip_count(signs: List[int]) -> int:
    cleaned = [s for s in signs if s != 0]
    if len(cleaned) < 2:
        return 0
    flips = 0
    for i in range(1, len(cleaned)):
        if cleaned[i] != cleaned[i - 1]:
            flips += 1
    return flips


def _gate_result(flip_count: int, snr: float, thr: GateThresholds) -> Tuple[str, str]:
    pass_rule = f"PASS if FlipCount == 0 and SNR > {thr.pass_snr}"
    weak_rule = f"WEAK_PASS if FlipCount <= {thr.weak_flip_max} and SNR > {thr.weak_snr}"

    if flip_count == 0 and snr > thr.pass_snr:
        return "PASS", f"{pass_rule}; satisfied"
    if flip_count <= thr.weak_flip_max and snr > thr.weak_snr:
        return "WEAK_PASS", f"{weak_rule}; satisfied, strict PASS not met"
    return "FAIL", f"{pass_rule}; {weak_rule}; neither satisfied"


def build_report(
    artifacts_root: Path,
    candidate_a_prefix: str,
    candidate_b_prefix: str,
    metric_paths: Dict[str, str],
    epsilon: float,
    thr: GateThresholds,
) -> Dict:
    a_series = _load_candidate_series(artifacts_root, candidate_a_prefix, metric_paths)
    b_series = _load_candidate_series(artifacts_root, candidate_b_prefix, metric_paths)

    common_z = sorted(set(a_series.keys()) & set(b_series.keys()))
    if not common_z:
        raise ValueError(
            "No overlapping z-slices found. "
            f"Checked prefixes '{candidate_a_prefix}' and '{candidate_b_prefix}' under {artifacts_root}"
        )

    metrics_report = {}
    for metric_name in metric_paths:
        a_vals = [a_series[z][metric_name] for z in common_z]
        b_vals = [b_series[z][metric_name] for z in common_z]
        diffs = [av - bv for av, bv in zip(a_vals, b_vals)]
        signs = [_sign(d, epsilon) for d in diffs]

        flips = _flip_count(signs)
        a_mu, b_mu = mean(a_vals), mean(b_vals)
        a_sd = pstdev(a_vals) if len(a_vals) > 1 else 0.0
        b_sd = pstdev(b_vals) if len(b_vals) > 1 else 0.0
        denom = max(a_sd, b_sd)
        snr = abs(a_mu - b_mu) / denom if denom > 0 else (float("inf") if a_mu != b_mu else 0.0)

        verdict, rule_text = _gate_result(flips, snr, thr)
        decision = (
            "allowed for bounded comparative descriptor use"
            if verdict in ("PASS", "WEAK_PASS")
            else "restricted to per-slice descriptive reporting only"
        )

        metrics_report[metric_name] = {
            "metric_path": metric_paths[metric_name],
            "z_slices": common_z,
            "candidate_a_values": a_vals,
            "candidate_b_values": b_vals,
            "a_minus_b": diffs,
            "ordering_sign_per_z": signs,
            "flip_count": flips,
            "candidate_a_mean": a_mu,
            "candidate_a_std_pop": a_sd,
            "candidate_b_mean": b_mu,
            "candidate_b_std_pop": b_sd,
            "snr_effect_size": snr,
            "gate_rule": rule_text,
            "verdict": verdict,
            "methodological_decision": decision,
            "reason": (
                f"FlipCount={flips}, SNR={snr:.6g}, epsilon={epsilon}. "
                "Methodological gate only; no physics/performance inference."
            ),
        }

    return {
        "tool": "cross_slice_gate_calculator",
        "schema_version": "1.0.0",
        "inputs": {
            "artifacts_root": str(artifacts_root),
            "candidate_a_prefix": candidate_a_prefix,
            "candidate_b_prefix": candidate_b_prefix,
            "metric_paths": metric_paths,
            "epsilon": epsilon,
            "gate_thresholds": {
                "pass_snr": thr.pass_snr,
                "weak_snr": thr.weak_snr,
                "weak_flip_max": thr.weak_flip_max,
            },
            "assumption": "Uses existing summary.json artifacts only; read-only computation.",
        },
        "metrics": metrics_report,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compute cross-slice descriptor gate verdicts from existing artifacts")
    p.add_argument("--artifacts-root", default="artifacts", help="Root directory containing run folders")
    p.add_argument("--candidate-a-prefix", default="stage4_full_cand01", help="Run prefix for candidate A")
    p.add_argument("--candidate-b-prefix", default="stage4_full_cand02", help="Run prefix for candidate B")
    p.add_argument("--epsilon", type=float, default=1e-9, help="Tie tolerance for sign calculation")
    p.add_argument("--out", default="", help="Optional output JSON file path")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        artifacts_root=Path(args.artifacts_root),
        candidate_a_prefix=args.candidate_a_prefix,
        candidate_b_prefix=args.candidate_b_prefix,
        metric_paths=DEFAULT_METRICS,
        epsilon=args.epsilon,
        thr=GateThresholds(),
    )

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
