"""Schema validation for bridge-local output artifacts.

IMPLEMENTED: jsonschema validation for bridge_field_frame and bridge_signature_stream.
"""

import json
from pathlib import Path
from typing import Union, Any

try:
    import jsonschema
    _JSONSCHEMA_AVAILABLE = True
except ImportError:
    _JSONSCHEMA_AVAILABLE = False


# Schema file locations relative to this module
_SCHEMA_DIR = Path(__file__).parent.parent.parent.parent / "schemas"


def _load_schema(schema_name: str) -> dict:
    """Load a bridge-local schema by filename (without .schema.json extension)."""
    schema_path = _SCHEMA_DIR / f"{schema_name}.schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(
            f"Schema not found: {schema_path}\n"
            f"Expected in: {_SCHEMA_DIR}"
        )
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_field_frame(record: dict) -> None:
    """Validate a field_contract.json record against bridge_field_frame.schema.json.

    Args:
        record: Dict loaded from field_contract.json.

    Raises:
        jsonschema.ValidationError: If validation fails.
        ImportError: If jsonschema is not installed.
        FileNotFoundError: If schema file not found.
    """
    if not _JSONSCHEMA_AVAILABLE:
        raise ImportError(
            "jsonschema is required for schema validation. "
            "Install with: pip install jsonschema"
        )
    schema = _load_schema("bridge_field_frame")
    jsonschema.validate(instance=record, schema=schema)


def validate_signature_record(record: dict) -> None:
    """Validate one record from signatures.jsonl against bridge_signature_stream.schema.json.

    Args:
        record: Dict representing one JSONL line.

    Raises:
        jsonschema.ValidationError: If validation fails.
    """
    if not _JSONSCHEMA_AVAILABLE:
        raise ImportError(
            "jsonschema is required for schema validation. "
            "Install with: pip install jsonschema"
        )
    schema = _load_schema("bridge_signature_stream")
    jsonschema.validate(instance=record, schema=schema)


def validate_manifest(manifest_path: Union[str, Path]) -> dict:
    """Load and basic-validate a manifest.json artifact bundle.

    Does not validate against a schema (manifest is free-form),
    but checks required top-level keys.

    Args:
        manifest_path: Path to manifest.json.

    Returns:
        Loaded manifest dict.

    Raises:
        ValueError: If required keys are missing.
        FileNotFoundError: If file not found.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    required_keys = [
        "schema_version", "bridge_run_sha256", "input_sha256",
        "files", "bridge_git_sha",
    ]
    missing = [k for k in required_keys if k not in manifest]
    if missing:
        raise ValueError(
            f"Manifest missing required keys: {missing}\n"
            f"Available keys: {list(manifest.keys())}"
        )

    return manifest


def validate_bundle_dir(output_dir: Union[str, Path]) -> dict:
    """Validate a complete bridge output artifact bundle directory.

    Checks:
    - All expected files exist
    - field_contract.json validates against bridge_field_frame schema
    - First 3 records in signatures.jsonl validate against bridge_signature_stream schema
    - manifest.json has required keys

    Args:
        output_dir: Path to bridge run output directory.

    Returns:
        Dict with validation results.

    Raises:
        FileNotFoundError: If output_dir or required files are missing.
    """
    output_dir = Path(output_dir)
    results = {
        "valid": False,
        "errors": [],
        "warnings": [],
        "files_checked": [],
    }

    required_files = [
        "field_contract.json",
        "signatures.jsonl",
        "summary.json",
        "manifest.json",
    ]

    # Check files exist
    for fname in required_files:
        fpath = output_dir / fname
        if not fpath.exists():
            results["errors"].append(f"Missing required file: {fname}")
        else:
            results["files_checked"].append(fname)

    if results["errors"]:
        return results

    # Validate field_contract.json schema
    try:
        with open(output_dir / "field_contract.json", "r") as f:
            fc = json.load(f)
        validate_field_frame(fc)
    except Exception as e:
        results["errors"].append(f"field_contract.json validation failed: {e}")

    # Validate first 3 signature records
    try:
        with open(output_dir / "signatures.jsonl", "r") as f:
            for i, line in enumerate(f):
                if i >= 3:
                    break
                if line.strip():
                    rec = json.loads(line.strip())
                    validate_signature_record(rec)
    except Exception as e:
        results["errors"].append(f"signatures.jsonl validation failed: {e}")

    # Validate manifest
    try:
        validate_manifest(output_dir / "manifest.json")
    except Exception as e:
        results["errors"].append(f"manifest.json validation failed: {e}")

    results["valid"] = len(results["errors"]) == 0
    return results
