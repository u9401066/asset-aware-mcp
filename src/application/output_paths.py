"""Safe output path resolution for document-scoped artifacts."""

from __future__ import annotations

from pathlib import Path


def resolve_document_output_path(
    doc_dir: Path,
    output_path: str | None,
    *,
    default_name: str,
    allowed_suffixes: set[str] | None = None,
    reserved_names: set[str] | None = None,
) -> Path:
    """Resolve an output path while keeping writes inside a document directory."""
    base_dir = doc_dir.resolve()
    candidate = Path(output_path) if output_path else base_dir / default_name
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    resolved = candidate.resolve()

    try:
        resolved.relative_to(base_dir)
    except ValueError as exc:
        raise ValueError(
            f"Output path must stay within document directory: {base_dir}"
        ) from exc

    if allowed_suffixes is not None and resolved.suffix.lower() not in allowed_suffixes:
        suffixes = ", ".join(sorted(allowed_suffixes))
        raise ValueError(f"Output path must use one of: {suffixes}")

    if reserved_names and resolved.name.lower() in {
        name.lower() for name in reserved_names
    }:
        names = ", ".join(sorted(reserved_names))
        raise ValueError(
            f"Output path must not overwrite reserved document files: {names}"
        )

    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def resolve_document_output_dir(
    base_dir: Path,
    output_dir: str | None,
    *,
    default_name: str,
    create: bool = True,
) -> Path:
    """Resolve an output directory while keeping writes inside a safe base dir."""
    root = base_dir.resolve()
    candidate = Path(output_dir) if output_dir else root / default_name
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Output directory must stay within: {root}") from exc

    if create:
        resolved.mkdir(parents=True, exist_ok=True)
    return resolved
