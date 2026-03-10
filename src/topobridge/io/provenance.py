"""Provenance capture for bridge runs.

Records bridge-side git SHA, timestamp, and run parameters.
Does NOT capture parent repo internals at runtime.
"""

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any


def get_bridge_git_sha() -> Optional[str]:
    """Get git SHA of the bridge repo (coldplate-topobridge).

    Returns None if not in a git repo or git unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(Path(__file__).resolve().parent.parent.parent.parent),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_bridge_git_status() -> Optional[str]:
    """Return 'clean' or 'dirty' for the bridge repo, or None."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(Path(__file__).resolve().parent.parent.parent.parent),
        )
        if result.returncode == 0:
            return "dirty" if result.stdout.strip() else "clean"
    except Exception:
        pass
    return None


def build_run_provenance(
    input_sha256: str,
    source_repo: str,
    source_stage: str,
    source_artifact: str,
    source_commit: Optional[str],
    preprocessing: list,
    grid_shape: tuple,
    low_signal_threshold: float,
) -> Dict[str, Any]:
    """Build a provenance record for a bridge run.

    Args:
        input_sha256: SHA-256 of the input field artifact.
        source_repo: Name of originating repository.
        source_stage: Pipeline stage (e.g., 'stage1_2d').
        source_artifact: Relative path to source artifact.
        source_commit: Git SHA of source repo at time of artifact creation.
        preprocessing: List of preprocessing steps applied.
        grid_shape: (ny, nx) of the field.
        low_signal_threshold: Threshold used to define low-signal pixels.

    Returns:
        Dict with all provenance fields. All entries are deterministic
        given the same inputs (run_timestamp is the only non-deterministic field,
        and it is informational only, not used in hash computations).
    """
    ny, nx = grid_shape
    bridge_sha = get_bridge_git_sha()
    bridge_status = get_bridge_git_status()

    return {
        "schema_version": "1.0.0",
        "bridge_repo": "coldplate-topobridge",
        "bridge_git_sha": bridge_sha,
        "bridge_git_status": bridge_status,
        "input_sha256": input_sha256,
        "source_repo": source_repo,
        "source_stage": source_stage,
        "source_artifact": source_artifact,
        "source_commit": source_commit,
        "preprocessing": preprocessing,
        "grid_ny": ny,
        "grid_nx": nx,
        "low_signal_threshold": low_signal_threshold,
        "run_timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(
    output_dir: Path,
    input_sha256: str,
    run_provenance: Dict[str, Any],
) -> Dict[str, Any]:
    """Build manifest.json by hashing all output files.

    Args:
        output_dir: Directory containing bridge run outputs.
        input_sha256: SHA-256 of the input artifact.
        run_provenance: Run provenance dict.

    Returns:
        Manifest dict. The bridge_run_sha256 field is computed from
        sorted file hashes for determinism.
    """
    expected_files = [
        "field_contract.json",
        "signatures.jsonl",
        "summary.json",
    ]

    file_hashes: Dict[str, str] = {}
    for fname in expected_files:
        fpath = output_dir / fname
        if fpath.exists():
            file_hashes[fname] = compute_file_sha256(fpath)

    # Deterministic run-level hash: sha256(sorted file hashes)
    h = hashlib.sha256()
    for fname in sorted(file_hashes.keys()):
        h.update(f"{fname}:{file_hashes[fname]}".encode("utf-8"))
    bridge_run_sha256 = h.hexdigest()

    return {
        "schema_version": "1.0.0",
        "bridge_schema_id": "bridge_manifest",
        "bridge_run_sha256": bridge_run_sha256,
        "input_sha256": input_sha256,
        "bridge_git_sha": run_provenance.get("bridge_git_sha"),
        "bridge_git_status": run_provenance.get("bridge_git_status"),
        "run_timestamp": run_provenance.get("run_timestamp"),
        "files": file_hashes,
        "provenance": run_provenance,
    }
