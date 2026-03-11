"""Generate deterministic EXPERIMENTAL_SANDBOX 2D channel fields.

This module is intentionally sandboxed. It does NOT modify the validated
Stage 4 bridge pipeline and it does NOT claim physical realism beyond the
explicit provenance class attached to each case.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np


EXPERIMENT_LABEL = "EXPERIMENTAL_SANDBOX_ANALYTICAL_2D_CRITIC"
EXPERIMENT_ID = "analytical_2d_critic_v1"
FIXED_FROZEN_AT = "2026-03-11T00:00:00Z"
DEFAULT_NX = 96
DEFAULT_NY = 64
DOMAIN_X_MIN = 0.0
DOMAIN_X_MAX = 1.0
DOMAIN_Y_MIN = -0.6
DOMAIN_Y_MAX = 0.6
STRAIGHT_CHANNEL_HEIGHT = 0.8
_ZIP_TIMESTAMP = (2026, 3, 11, 0, 0, 0)


@dataclass(frozen=True)
class CaseArtifact:
    case_id: str
    geometry_case: str
    provenance_class: str
    description: str
    physics_note: str
    npz_path: Path
    meta_path: Path


def generate_cases(
    output_root: Path,
    nx: int = DEFAULT_NX,
    ny: int = DEFAULT_NY,
) -> List[CaseArtifact]:
    """Write all sandbox field cases to ``output_root / fields``."""
    output_root = Path(output_root)
    fields_dir = output_root / "fields"
    fields_dir.mkdir(parents=True, exist_ok=True)

    case_defs = [
        _build_straight_channel_case(nx=nx, ny=ny),
        _build_single_obstruction_case(nx=nx, ny=ny),
        _build_constricted_channel_case(nx=nx, ny=ny),
    ]

    artifacts: List[CaseArtifact] = []
    git_sha = _get_repo_git_sha(output_root)

    for case_def in case_defs:
        npz_path = fields_dir / f"{case_def['case_id']}.npz"
        meta_path = fields_dir / f"{case_def['case_id']}.meta.json"
        _write_deterministic_npz(
            npz_path,
            {
                "u": case_def["u"],
                "v": case_def["v"],
                "solid_mask": case_def["solid_mask"],
            },
        )
        _write_json(meta_path, case_def["meta"](npz_path=npz_path, git_sha=git_sha))
        artifacts.append(
            CaseArtifact(
                case_id=case_def["case_id"],
                geometry_case=case_def["geometry_case"],
                provenance_class=case_def["provenance_class"],
                description=case_def["description"],
                physics_note=case_def["physics_note"],
                npz_path=npz_path,
                meta_path=meta_path,
            )
        )

    return artifacts


def _build_straight_channel_case(nx: int, ny: int) -> Dict[str, object]:
    x, _, _, y2d = _make_cell_centered_grid(nx=nx, ny=ny)
    height = np.full(nx, STRAIGHT_CHANNEL_HEIGHT, dtype=np.float64)
    u, v, solid_mask = _variable_height_channel_streamfunction(
        x=x,
        y2d=y2d,
        height=height,
    )

    def build_meta(npz_path: Path, git_sha: str | None) -> Dict[str, object]:
        return _base_meta(
            case_id="straight_channel",
            geometry_case="uniform_straight_channel",
            provenance_class="EXACT_ANALYTIC",
            description=(
                "Straight 2D channel using the fully developed plane-Poiseuille "
                "profile u(y) with v=0 on a fixed-width slit."
            ),
            physics_note=(
                "Exact analytic baseline for the imposed straight-channel geometry. "
                "This is the control case for descriptor stability only."
            ),
            nx=nx,
            ny=ny,
            git_sha=git_sha,
            source_artifact=f"fields/{npz_path.name}",
        )

    return {
        "case_id": "straight_channel",
        "geometry_case": "uniform_straight_channel",
        "provenance_class": "EXACT_ANALYTIC",
        "description": (
            "Straight channel baseline with exact analytic plane-Poiseuille profile."
        ),
        "physics_note": (
            "Analytic baseline only. No claim beyond descriptor stability in a simple slit."
        ),
        "u": u,
        "v": v,
        "solid_mask": solid_mask,
        "meta": build_meta,
    }


def _build_constricted_channel_case(nx: int, ny: int) -> Dict[str, object]:
    x, _, _, y2d = _make_cell_centered_grid(nx=nx, ny=ny)
    throat_depth = 0.35
    throat_sigma = 0.12
    throat_center = 0.5
    gaussian = np.exp(-((x - throat_center) ** 2) / (2.0 * throat_sigma**2))
    height = STRAIGHT_CHANNEL_HEIGHT * (1.0 - throat_depth * gaussian)
    u, v, solid_mask = _variable_height_channel_streamfunction(
        x=x,
        y2d=y2d,
        height=height,
    )

    def build_meta(npz_path: Path, git_sha: str | None) -> Dict[str, object]:
        return _base_meta(
            case_id="constricted_channel",
            geometry_case="smooth_constricted_channel",
            provenance_class="QUASI_ANALYTICAL",
            description=(
                "Smoothly constricted channel from an imposed streamfunction with "
                "x-varying gap height. Produces a deterministic parabolic profile "
                "plus continuity-driven transverse component."
            ),
            physics_note=(
                "QUASI_ANALYTICAL: exact for the constructed streamfunction, but not "
                "claimed as an exact Navier-Stokes solution for a real constricted channel."
            ),
            nx=nx,
            ny=ny,
            git_sha=git_sha,
            source_artifact=f"fields/{npz_path.name}",
            geometry_parameters={
                "base_height": STRAIGHT_CHANNEL_HEIGHT,
                "throat_depth_fraction": throat_depth,
                "throat_sigma": throat_sigma,
                "throat_center_x": throat_center,
            },
        )

    return {
        "case_id": "constricted_channel",
        "geometry_case": "smooth_constricted_channel",
        "provenance_class": "QUASI_ANALYTICAL",
        "description": (
            "Constricted channel with quasi-analytical streamfunction-derived field."
        ),
        "physics_note": (
            "A deterministic continuity-consistent surrogate, not a validated CFD result."
        ),
        "u": u,
        "v": v,
        "solid_mask": solid_mask,
        "meta": build_meta,
    }


def _build_single_obstruction_case(nx: int, ny: int) -> Dict[str, object]:
    _, _, x2d, y2d = _make_cell_centered_grid(nx=nx, ny=ny)
    half_height = 0.5 * STRAIGHT_CHANNEL_HEIGHT
    fluid_channel = np.abs(y2d) <= half_height

    obstacle_cx = 0.48
    obstacle_cy = 0.0
    obstacle_radius = 0.11
    dx = x2d - obstacle_cx
    dy = y2d - obstacle_cy
    radius = np.sqrt(dx**2 + dy**2)
    theta = np.arctan2(dy, dx)
    obstacle_mask = radius <= obstacle_radius

    eta = np.zeros_like(y2d, dtype=np.float64)
    eta[fluid_channel] = y2d[fluid_channel] / half_height
    u_base = np.zeros_like(y2d, dtype=np.float64)
    u_base[fluid_channel] = 1.0 - eta[fluid_channel] ** 2

    ratio = (obstacle_radius**2) / np.maximum(radius**2, obstacle_radius**2 * 1.0001)
    u = u_base * (1.0 - 0.55 * ratio * np.cos(2.0 * theta))
    v = -0.65 * u_base * ratio * np.sin(2.0 * theta)

    wake = 1.0 - (
        0.35
        * np.exp(-((x2d - (obstacle_cx + 1.5 * obstacle_radius)) / 0.16) ** 2)
        * np.exp(-(y2d / 0.10) ** 2)
        * (x2d > obstacle_cx)
    )
    gap_boost = 1.0 + (
        0.30
        * np.exp(-((np.abs(dy) - obstacle_radius) / 0.05) ** 2)
        * np.exp(-(dx / 0.20) ** 2)
    )

    fluid_mask = fluid_channel & (~obstacle_mask)
    u = np.clip(u * wake * gap_boost, 0.0, 2.0)
    v = np.clip(v * wake, -1.0, 1.0)
    u[~fluid_mask] = 0.0
    v[~fluid_mask] = 0.0
    solid_mask = (~fluid_mask).astype(np.uint8)

    def build_meta(npz_path: Path, git_sha: str | None) -> Dict[str, object]:
        return _base_meta(
            case_id="single_obstruction",
            geometry_case="single_circular_obstruction_channel",
            provenance_class="SYNTHETIC",
            description=(
                "Straight channel with one circular obstruction. The field is a "
                "deterministic synthetic blend of a Poiseuille envelope, "
                "cylinder-like deflection, and wake attenuation."
            ),
            physics_note=(
                "SYNTHETIC: built to create structured directional variation around "
                "a simple obstacle. It is not a CFD solution and is not claimed as physically realistic."
            ),
            nx=nx,
            ny=ny,
            git_sha=git_sha,
            source_artifact=f"fields/{npz_path.name}",
            geometry_parameters={
                "channel_height": STRAIGHT_CHANNEL_HEIGHT,
                "obstacle_center_x": obstacle_cx,
                "obstacle_center_y": obstacle_cy,
                "obstacle_radius": obstacle_radius,
            },
        )

    return {
        "case_id": "single_obstruction",
        "geometry_case": "single_circular_obstruction_channel",
        "provenance_class": "SYNTHETIC",
        "description": (
            "Single-obstruction channel with deterministic synthetic deflection field."
        ),
        "physics_note": (
            "Structured but explicitly synthetic. No physical realism claim is attached."
        ),
        "u": u.astype(np.float64),
        "v": v.astype(np.float64),
        "solid_mask": solid_mask,
        "meta": build_meta,
    }


def _variable_height_channel_streamfunction(
    x: np.ndarray,
    y2d: np.ndarray,
    height: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Streamfunction-derived channel field for a slit with variable height."""
    height2d = np.broadcast_to(height[np.newaxis, :], y2d.shape)
    half_height2d = 0.5 * height2d
    fluid_mask = np.abs(y2d) <= half_height2d

    dheight_dx = np.gradient(height, x, edge_order=2)
    dheight_dx_2d = np.broadcast_to(dheight_dx[np.newaxis, :], y2d.shape)

    q_flux = 0.5 * STRAIGHT_CHANNEL_HEIGHT

    eta = np.zeros_like(y2d, dtype=np.float64)
    eta[fluid_mask] = 2.0 * y2d[fluid_mask] / height2d[fluid_mask]

    u = np.zeros_like(y2d, dtype=np.float64)
    v = np.zeros_like(y2d, dtype=np.float64)
    u[fluid_mask] = (2.0 * q_flux / height2d[fluid_mask]) * (1.0 - eta[fluid_mask] ** 2)
    v[fluid_mask] = (
        q_flux
        * eta[fluid_mask]
        * (1.0 - eta[fluid_mask] ** 2)
        * dheight_dx_2d[fluid_mask]
        / height2d[fluid_mask]
    )

    solid_mask = (~fluid_mask).astype(np.uint8)
    return u, v, solid_mask


def _make_cell_centered_grid(nx: int, ny: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    dx = (DOMAIN_X_MAX - DOMAIN_X_MIN) / nx
    dy = (DOMAIN_Y_MAX - DOMAIN_Y_MIN) / ny
    x = np.linspace(DOMAIN_X_MIN + 0.5 * dx, DOMAIN_X_MAX - 0.5 * dx, nx, dtype=np.float64)
    y = np.linspace(DOMAIN_Y_MIN + 0.5 * dy, DOMAIN_Y_MAX - 0.5 * dy, ny, dtype=np.float64)
    x2d, y2d = np.meshgrid(x, y)
    return x, y, x2d, y2d


def _base_meta(
    case_id: str,
    geometry_case: str,
    provenance_class: str,
    description: str,
    physics_note: str,
    nx: int,
    ny: int,
    git_sha: str | None,
    source_artifact: str,
    geometry_parameters: Dict[str, object] | None = None,
) -> Dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "source_repo": "coldplate-topobridge",
        "source_stage": "experimental_analytical_2d_critic",
        "source_artifact": source_artifact,
        "source_commit": git_sha,
        "preprocessing": [
            "EXPERIMENTAL_SANDBOX",
            "analytical_2d_critic_case_generation",
        ],
        "grid_nx": nx,
        "grid_ny": ny,
        "grid_dx": (DOMAIN_X_MAX - DOMAIN_X_MIN) / nx,
        "grid_dy": (DOMAIN_Y_MAX - DOMAIN_Y_MIN) / ny,
        "field_frozen_at": FIXED_FROZEN_AT,
        "experimental_case": {
            "experiment_label": EXPERIMENT_LABEL,
            "experiment_id": EXPERIMENT_ID,
            "case_id": case_id,
            "geometry_case": geometry_case,
            "provenance_class": provenance_class,
            "description": description,
            "physics_note": physics_note,
            "domain_bounds": {
                "x_min": DOMAIN_X_MIN,
                "x_max": DOMAIN_X_MAX,
                "y_min": DOMAIN_Y_MIN,
                "y_max": DOMAIN_Y_MAX,
            },
            "geometry_parameters": geometry_parameters or {},
            "scope_guardrails": [
                "EXPERIMENTAL_SANDBOX only",
                "No TopoStream semantic integration",
                "No TPMS ranking claim",
                "No claim that descriptor structure equals real vortices",
            ],
        },
    }


def _write_deterministic_npz(path: Path, arrays: Dict[str, np.ndarray]) -> None:
    path = Path(path)
    with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for key in sorted(arrays.keys()):
            buffer = io.BytesIO()
            np.save(buffer, arrays[key], allow_pickle=False)
            info = zipfile.ZipInfo(filename=f"{key}.npy", date_time=_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o600 << 16
            archive.writestr(info, buffer.getvalue())


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _get_repo_git_sha(output_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(Path(output_root).resolve().parents[1]),
            check=False,
        )
    except Exception:
        return None

    if result.returncode == 0:
        return result.stdout.strip()
    return None


def _format_rows(artifacts: Iterable[CaseArtifact]) -> List[str]:
    rows = []
    for artifact in artifacts:
        rows.append(
            (
                f"{artifact.case_id}: {artifact.provenance_class} | "
                f"{artifact.geometry_case} | {artifact.npz_path}"
            )
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic EXPERIMENTAL_SANDBOX 2D field cases."
    )
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parent / "out"),
        help="Root directory for generated sandbox fields.",
    )
    parser.add_argument("--nx", type=int, default=DEFAULT_NX, help="Grid columns.")
    parser.add_argument("--ny", type=int, default=DEFAULT_NY, help="Grid rows.")
    args = parser.parse_args()

    artifacts = generate_cases(output_root=Path(args.output_root), nx=args.nx, ny=args.ny)
    print(EXPERIMENT_LABEL)
    for row in _format_rows(artifacts):
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
