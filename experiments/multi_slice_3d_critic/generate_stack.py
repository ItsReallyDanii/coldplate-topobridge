"""Generate deterministic EXPERIMENTAL_SANDBOX multi-slice field stacks.

This module creates a bounded "simple 3D proxy" as a stack of deterministic
2D slices with controlled variation. It is intentionally separate from the
validated Stage 4 bridge pipeline and does not claim physical realism or
validated 3D ranking behavior.
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


EXPERIMENT_LABEL = "EXPERIMENTAL_SANDBOX_MULTI_SLICE_3D_CRITIC"
EXPERIMENT_ID = "multi_slice_3d_critic_v1"
FIXED_FROZEN_AT = "2026-03-11T00:00:00Z"
DEFAULT_NX = 96
DEFAULT_NY = 64
DEFAULT_N_SLICES = 5
DOMAIN_X_MIN = 0.0
DOMAIN_X_MAX = 1.0
DOMAIN_Y_MIN = -0.6
DOMAIN_Y_MAX = 0.6
DOMAIN_Z_MIN = 0.0
DOMAIN_Z_MAX = 1.0
STRAIGHT_CHANNEL_HEIGHT = 0.8
_ZIP_TIMESTAMP = (2026, 3, 11, 0, 0, 0)


@dataclass(frozen=True)
class SliceArtifact:
    case_id: str
    slice_id: str
    slice_index: int
    z_position: float
    geometry_case: str
    provenance_class: str
    npz_path: Path
    meta_path: Path


@dataclass(frozen=True)
class StackArtifact:
    case_id: str
    geometry_case: str
    provenance_class: str
    description: str
    physics_note: str
    manifest_path: Path
    slice_artifacts: List[SliceArtifact]


def generate_cases(
    output_root: Path,
    nx: int = DEFAULT_NX,
    ny: int = DEFAULT_NY,
    n_slices: int = DEFAULT_N_SLICES,
) -> List[StackArtifact]:
    """Write all multi-slice sandbox cases to ``output_root / fields``."""
    output_root = Path(output_root)
    fields_dir = output_root / "fields"
    fields_dir.mkdir(parents=True, exist_ok=True)

    z_positions = _make_z_positions(n_slices)
    case_defs = [
        _build_straight_stack_case(nx=nx, ny=ny, z_positions=z_positions),
        _build_obstruction_stack_case(nx=nx, ny=ny, z_positions=z_positions),
        _build_constriction_stack_case(nx=nx, ny=ny, z_positions=z_positions),
    ]

    git_sha = _get_repo_git_sha(output_root)
    artifacts: List[StackArtifact] = []

    for case_def in case_defs:
        case_dir = fields_dir / case_def["case_id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        slice_artifacts: List[SliceArtifact] = []

        for slice_def in case_def["slices"]:
            slice_id = str(slice_def["slice_id"])
            npz_path = case_dir / f"{slice_id}.npz"
            meta_path = case_dir / f"{slice_id}.meta.json"
            _write_deterministic_npz(
                npz_path,
                {
                    "u": slice_def["u"],
                    "v": slice_def["v"],
                    "solid_mask": slice_def["solid_mask"],
                },
            )
            _write_json(
                meta_path,
                slice_def["meta"](
                    npz_path=npz_path,
                    git_sha=git_sha,
                    slice_id=slice_id,
                ),
            )
            slice_artifacts.append(
                SliceArtifact(
                    case_id=case_def["case_id"],
                    slice_id=slice_id,
                    slice_index=int(slice_def["slice_index"]),
                    z_position=float(slice_def["z_position"]),
                    geometry_case=case_def["geometry_case"],
                    provenance_class=case_def["provenance_class"],
                    npz_path=npz_path,
                    meta_path=meta_path,
                )
            )

        manifest_path = case_dir / "stack_manifest.json"
        _write_json(
            manifest_path,
            _build_case_manifest(
                case_def=case_def,
                slice_artifacts=slice_artifacts,
                git_sha=git_sha,
                nx=nx,
                ny=ny,
            ),
        )

        artifacts.append(
            StackArtifact(
                case_id=case_def["case_id"],
                geometry_case=case_def["geometry_case"],
                provenance_class=case_def["provenance_class"],
                description=case_def["description"],
                physics_note=case_def["physics_note"],
                manifest_path=manifest_path,
                slice_artifacts=slice_artifacts,
            )
        )

    return artifacts


def _build_straight_stack_case(
    nx: int,
    ny: int,
    z_positions: np.ndarray,
) -> Dict[str, object]:
    x, _, _, y2d = _make_cell_centered_grid(nx=nx, ny=ny)
    height = np.full(nx, STRAIGHT_CHANNEL_HEIGHT, dtype=np.float64)
    u, v, solid_mask = _variable_height_channel_streamfunction(
        x=x,
        y2d=y2d,
        height=height,
    )

    slices = []
    for slice_index, z_position in enumerate(z_positions):
        slice_id = f"straight_stack__z{slice_index:02d}"

        def build_meta(
            npz_path: Path,
            git_sha: str | None,
            slice_id: str,
            slice_index: int = slice_index,
            z_position: float = float(z_position),
        ) -> Dict[str, object]:
            return _base_meta(
                case_id="straight_stack",
                geometry_case="stacked_straight_channel",
                provenance_class="EXACT_ANALYTIC",
                description=(
                    "Straight channel stack. Each slice uses the same exact "
                    "plane-Poiseuille profile as a low-complexity multi-slice baseline."
                ),
                physics_note=(
                    "Exact analytic per-slice baseline for the imposed slit geometry. "
                    "This is a deterministic stack control only."
                ),
                nx=nx,
                ny=ny,
                git_sha=git_sha,
                source_artifact=f"fields/straight_stack/{npz_path.name}",
                slice_id=slice_id,
                slice_index=slice_index,
                z_position=z_position,
                slice_generation_rule=(
                    "Identical analytic slice repeated across z to establish the "
                    "multi-slice baseline."
                ),
                geometry_parameters={
                    "channel_height": STRAIGHT_CHANNEL_HEIGHT,
                },
            )

        slices.append(
            {
                "slice_id": slice_id,
                "slice_index": slice_index,
                "z_position": float(z_position),
                "u": u.copy(),
                "v": v.copy(),
                "solid_mask": solid_mask.copy(),
                "meta": build_meta,
            }
        )

    return {
        "case_id": "straight_stack",
        "geometry_case": "stacked_straight_channel",
        "provenance_class": "EXACT_ANALYTIC",
        "description": "Straight-channel stack with identical analytic slices.",
        "physics_note": (
            "Exact analytic stack control only. No claim beyond deterministic "
            "descriptor stability in a repeated-slice baseline."
        ),
        "stack_note": (
            "All slices are identical to create a strict low-complexity baseline "
            "for the bounded simple-3D proxy."
        ),
        "slices": slices,
    }


def _build_obstruction_stack_case(
    nx: int,
    ny: int,
    z_positions: np.ndarray,
) -> Dict[str, object]:
    slices = []
    for slice_index, z_position in enumerate(z_positions):
        phase = float(z_position)
        obstacle_cx = 0.43 + 0.12 * phase
        obstacle_cy = 0.05 * np.sin(np.pi * phase)
        obstacle_radius = 0.090 + 0.015 * (np.sin(np.pi * phase) ** 2)
        wake_strength = 0.28 + 0.08 * phase
        gap_boost = 0.22 + 0.06 * (1.0 - phase)
        u, v, solid_mask = _single_obstruction_channel(
            nx=nx,
            ny=ny,
            obstacle_cx=obstacle_cx,
            obstacle_cy=obstacle_cy,
            obstacle_radius=obstacle_radius,
            wake_strength=wake_strength,
            gap_boost=gap_boost,
        )
        slice_id = f"obstruction_stack__z{slice_index:02d}"

        def build_meta(
            npz_path: Path,
            git_sha: str | None,
            slice_id: str,
            slice_index: int = slice_index,
            z_position: float = float(z_position),
            obstacle_cx: float = obstacle_cx,
            obstacle_cy: float = obstacle_cy,
            obstacle_radius: float = obstacle_radius,
            wake_strength: float = wake_strength,
            gap_boost: float = gap_boost,
        ) -> Dict[str, object]:
            return _base_meta(
                case_id="obstruction_stack",
                geometry_case="stacked_offset_obstruction_channel",
                provenance_class="SYNTHETIC",
                description=(
                    "Straight channel with one obstruction whose position and "
                    "radius vary deterministically across slices."
                ),
                physics_note=(
                    "SYNTHETIC: the slice fields are structured surrogate fields "
                    "built to test whether descriptor separation survives controlled "
                    "slice-to-slice variation."
                ),
                nx=nx,
                ny=ny,
                git_sha=git_sha,
                source_artifact=f"fields/obstruction_stack/{npz_path.name}",
                slice_id=slice_id,
                slice_index=slice_index,
                z_position=z_position,
                slice_generation_rule=(
                    "The obstruction center, radius, wake attenuation, and gap "
                    "boost vary deterministically with z."
                ),
                geometry_parameters={
                    "channel_height": STRAIGHT_CHANNEL_HEIGHT,
                    "obstacle_center_x": obstacle_cx,
                    "obstacle_center_y": obstacle_cy,
                    "obstacle_radius": obstacle_radius,
                    "wake_strength": wake_strength,
                    "gap_boost_strength": gap_boost,
                },
            )

        slices.append(
            {
                "slice_id": slice_id,
                "slice_index": slice_index,
                "z_position": float(z_position),
                "u": u,
                "v": v,
                "solid_mask": solid_mask,
                "meta": build_meta,
            }
        )

    return {
        "case_id": "obstruction_stack",
        "geometry_case": "stacked_offset_obstruction_channel",
        "provenance_class": "SYNTHETIC",
        "description": "Deterministic obstruction stack with controlled slice variation.",
        "physics_note": (
            "Structured but synthetic. It is not CFD, not physically validated, "
            "and not a ranking signal for real coldplate candidates."
        ),
        "stack_note": (
            "This stack introduces deterministic cross-slice variation to test "
            "whether the descriptors remain separable under a simple 3D proxy."
        ),
        "slices": slices,
    }


def _build_constriction_stack_case(
    nx: int,
    ny: int,
    z_positions: np.ndarray,
) -> Dict[str, object]:
    x, _, _, y2d = _make_cell_centered_grid(nx=nx, ny=ny)
    slices = []
    for slice_index, z_position in enumerate(z_positions):
        phase = float(z_position)
        throat_depth = 0.26 + 0.16 * np.sin(np.pi * phase)
        throat_sigma = 0.11 + 0.015 * np.cos(np.pi * phase)
        throat_center = 0.47 + 0.08 * (phase - 0.5)
        gaussian = np.exp(-((x - throat_center) ** 2) / (2.0 * throat_sigma**2))
        height = STRAIGHT_CHANNEL_HEIGHT * (1.0 - throat_depth * gaussian)
        u, v, solid_mask = _variable_height_channel_streamfunction(
            x=x,
            y2d=y2d,
            height=height,
        )
        slice_id = f"constriction_stack__z{slice_index:02d}"

        def build_meta(
            npz_path: Path,
            git_sha: str | None,
            slice_id: str,
            slice_index: int = slice_index,
            z_position: float = float(z_position),
            throat_depth: float = throat_depth,
            throat_sigma: float = throat_sigma,
            throat_center: float = throat_center,
        ) -> Dict[str, object]:
            return _base_meta(
                case_id="constriction_stack",
                geometry_case="stacked_breathing_constriction_channel",
                provenance_class="QUASI_ANALYTICAL",
                description=(
                    "Smooth constriction stack from a streamfunction with throat "
                    "depth, width, and center varying deterministically across slices."
                ),
                physics_note=(
                    "QUASI_ANALYTICAL: exact for the constructed streamfunction in "
                    "each slice, but not claimed as a validated Navier-Stokes or "
                    "coldplate-physics solution."
                ),
                nx=nx,
                ny=ny,
                git_sha=git_sha,
                source_artifact=f"fields/constriction_stack/{npz_path.name}",
                slice_id=slice_id,
                slice_index=slice_index,
                z_position=z_position,
                slice_generation_rule=(
                    "Constriction depth, sigma, and center vary smoothly with z "
                    "while the per-slice field remains continuity-consistent for the "
                    "constructed streamfunction."
                ),
                geometry_parameters={
                    "base_height": STRAIGHT_CHANNEL_HEIGHT,
                    "throat_depth_fraction": throat_depth,
                    "throat_sigma": throat_sigma,
                    "throat_center_x": throat_center,
                },
            )

        slices.append(
            {
                "slice_id": slice_id,
                "slice_index": slice_index,
                "z_position": float(z_position),
                "u": u,
                "v": v,
                "solid_mask": solid_mask,
                "meta": build_meta,
            }
        )

    return {
        "case_id": "constriction_stack",
        "geometry_case": "stacked_breathing_constriction_channel",
        "provenance_class": "QUASI_ANALYTICAL",
        "description": "Smooth constriction stack with deterministic z-variation.",
        "physics_note": (
            "A deterministic continuity-consistent surrogate, not a validated CFD "
            "result and not evidence of real 3D TPMS ranking."
        ),
        "stack_note": (
            "This stack is intended to test stronger descriptor separation under "
            "smooth multi-slice variation, not physical realism."
        ),
        "slices": slices,
    }


def _single_obstruction_channel(
    nx: int,
    ny: int,
    obstacle_cx: float,
    obstacle_cy: float,
    obstacle_radius: float,
    wake_strength: float,
    gap_boost: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    _, _, x2d, y2d = _make_cell_centered_grid(nx=nx, ny=ny)
    half_height = 0.5 * STRAIGHT_CHANNEL_HEIGHT
    fluid_channel = np.abs(y2d) <= half_height

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
    u = u_base * (1.0 - 0.48 * ratio * np.cos(2.0 * theta))
    v = -0.58 * u_base * ratio * np.sin(2.0 * theta)

    wake = 1.0 - (
        wake_strength
        * np.exp(-((x2d - (obstacle_cx + 1.45 * obstacle_radius)) / 0.18) ** 2)
        * np.exp(-((y2d - obstacle_cy) / 0.11) ** 2)
        * (x2d > obstacle_cx)
    )
    gap_enhancement = 1.0 + (
        gap_boost
        * np.exp(-((np.abs(dy) - obstacle_radius) / 0.06) ** 2)
        * np.exp(-(dx / 0.22) ** 2)
    )

    fluid_mask = fluid_channel & (~obstacle_mask)
    u = np.clip(u * wake * gap_enhancement, 0.0, 2.0)
    v = np.clip(v * wake, -1.0, 1.0)
    u[~fluid_mask] = 0.0
    v[~fluid_mask] = 0.0
    solid_mask = (~fluid_mask).astype(np.uint8)
    return u.astype(np.float64), v.astype(np.float64), solid_mask


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


def _make_cell_centered_grid(
    nx: int,
    ny: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    dx = (DOMAIN_X_MAX - DOMAIN_X_MIN) / nx
    dy = (DOMAIN_Y_MAX - DOMAIN_Y_MIN) / ny
    x = np.linspace(DOMAIN_X_MIN + 0.5 * dx, DOMAIN_X_MAX - 0.5 * dx, nx, dtype=np.float64)
    y = np.linspace(DOMAIN_Y_MIN + 0.5 * dy, DOMAIN_Y_MAX - 0.5 * dy, ny, dtype=np.float64)
    x2d, y2d = np.meshgrid(x, y)
    return x, y, x2d, y2d


def _make_z_positions(n_slices: int) -> np.ndarray:
    if n_slices < 3:
        raise ValueError("n_slices must be >= 3 for the bounded multi-slice critic.")
    return np.linspace(DOMAIN_Z_MIN, DOMAIN_Z_MAX, n_slices, dtype=np.float64)


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
    slice_id: str,
    slice_index: int,
    z_position: float,
    slice_generation_rule: str,
    geometry_parameters: Dict[str, object] | None = None,
) -> Dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "source_repo": "coldplate-topobridge",
        "source_stage": "experimental_multi_slice_3d_critic",
        "source_artifact": source_artifact,
        "source_commit": git_sha,
        "preprocessing": [
            "EXPERIMENTAL_SANDBOX",
            "multi_slice_3d_critic_case_generation",
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
                "z_min": DOMAIN_Z_MIN,
                "z_max": DOMAIN_Z_MAX,
            },
            "geometry_parameters": geometry_parameters or {},
            "simple_3d_proxy": {
                "representation": "stacked_2d_slices",
                "slice_id": slice_id,
                "slice_index": slice_index,
                "z_position": z_position,
                "slice_generation_rule": slice_generation_rule,
            },
            "scope_guardrails": [
                "EXPERIMENTAL_SANDBOX only",
                "No physical realism claim",
                "No vortex correspondence claim",
                "No TopoStream semantic compatibility claim",
                "No validated ranking of 3D TPMS coldplate candidates",
                "No physics validation claim",
            ],
        },
    }


def _build_case_manifest(
    case_def: Dict[str, object],
    slice_artifacts: List[SliceArtifact],
    git_sha: str | None,
    nx: int,
    ny: int,
) -> Dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "experiment_label": EXPERIMENT_LABEL,
        "experiment_id": EXPERIMENT_ID,
        "sandbox_status": "EXPERIMENTAL_SANDBOX",
        "source_repo": "coldplate-topobridge",
        "source_commit": git_sha,
        "source_stage": "experimental_multi_slice_3d_critic",
        "case_id": case_def["case_id"],
        "geometry_case": case_def["geometry_case"],
        "provenance_class": case_def["provenance_class"],
        "description": case_def["description"],
        "physics_note": case_def["physics_note"],
        "stack_note": case_def["stack_note"],
        "grid_nx": nx,
        "grid_ny": ny,
        "n_slices": len(slice_artifacts),
        "slice_artifacts": [
            {
                "slice_id": item.slice_id,
                "slice_index": item.slice_index,
                "z_position": item.z_position,
                "artifact": f"fields/{item.case_id}/{item.npz_path.name}",
                "meta": f"fields/{item.case_id}/{item.meta_path.name}",
            }
            for item in slice_artifacts
        ],
        "scope_guardrails": [
            "Deterministic bounded bridge experiment only",
            "No physical realism claim",
            "No TopoStream semantic compatibility claim",
            "No validated 3D TPMS ranking claim",
        ],
    }


def _write_deterministic_npz(path: Path, arrays: Dict[str, np.ndarray]) -> None:
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


def _format_rows(artifacts: Iterable[StackArtifact]) -> List[str]:
    rows = []
    for artifact in artifacts:
        rows.append(
            (
                f"{artifact.case_id}: {artifact.provenance_class} | "
                f"{artifact.geometry_case} | slices={len(artifact.slice_artifacts)} | "
                f"{artifact.manifest_path}"
            )
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic EXPERIMENTAL_SANDBOX multi-slice field cases."
    )
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parent / "out"),
        help="Root directory for generated sandbox fields.",
    )
    parser.add_argument("--nx", type=int, default=DEFAULT_NX, help="Grid columns.")
    parser.add_argument("--ny", type=int, default=DEFAULT_NY, help="Grid rows.")
    parser.add_argument(
        "--n-slices",
        type=int,
        default=DEFAULT_N_SLICES,
        help="Number of slices in each deterministic stack.",
    )
    args = parser.parse_args()

    artifacts = generate_cases(
        output_root=Path(args.output_root),
        nx=args.nx,
        ny=args.ny,
        n_slices=args.n_slices,
    )
    print(EXPERIMENT_LABEL)
    for row in _format_rows(artifacts):
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
