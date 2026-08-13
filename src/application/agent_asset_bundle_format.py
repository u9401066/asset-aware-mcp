"""Pure serialization and Foam rendering helpers for agent asset bundles."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

BUNDLE_VERSION = "agent-asset-bundle-v1"
RECORD_VERSION = "agent-asset-v1"
DEFAULT_MAX_BUNDLE_SPANS = 50_000
DEFAULT_MAX_BUNDLE_RECORDS = 25_000
DEFAULT_MAX_BUNDLE_OUTPUT_BYTES = 256 * 1024 * 1024


class AgentAssetBundleLimitError(ValueError):
    """A stable, actionable failure for bounded bundle generation."""

    def __init__(self, metric: str, observed: int, limit: int):
        self.metric = metric
        self.observed = observed
        self.limit = limit
        super().__init__(
            f"Agent asset bundle {metric} limit exceeded: {observed} > {limit}"
        )


@dataclass
class BundleOutputBudget:
    """Track bytes before every bundle artifact write."""

    max_bytes: int = DEFAULT_MAX_BUNDLE_OUTPUT_BYTES
    used_bytes: int = 0
    projected_bytes: int = 0

    def __post_init__(self) -> None:
        if self.max_bytes <= 0:
            raise ValueError("max bundle output bytes must be > 0")

    def reserve(self, size_bytes: int) -> None:
        if size_bytes < 0:
            raise ValueError("bundle output reservation must be >= 0")
        next_total = self.used_bytes + size_bytes
        if next_total + self.projected_bytes > self.max_bytes:
            raise AgentAssetBundleLimitError(
                "output_bytes",
                next_total + self.projected_bytes,
                self.max_bytes,
            )
        self.used_bytes = next_total

    def project(self, size_bytes: int) -> None:
        """Bound in-memory records before their artifacts are serialized."""
        if size_bytes < 0:
            raise ValueError("bundle output projection must be >= 0")
        next_projection = self.projected_bytes + size_bytes
        if self.used_bytes + next_projection > self.max_bytes:
            raise AgentAssetBundleLimitError(
                "output_bytes",
                self.used_bytes + next_projection,
                self.max_bytes,
            )
        self.projected_bytes = next_projection

    def clear_projection(self) -> None:
        """Switch from conservative record projection to actual artifact bytes."""
        self.projected_bytes = 0


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def slug(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9-]+", "-", value.strip().lower()).strip("-")
    return result or "asset"


def note_metadata(asset_key: str, doc_id: str) -> dict[str, str]:
    kind, asset_id = asset_key.split(":", 1)
    stable_suffix = sha256_text(f"{doc_id}|{asset_key}")[:10]
    stem = f"{slug(doc_id)}-{kind}-{slug(asset_id)}-{stable_suffix}"
    anchor = f"asset-{slug(kind)}-{stable_suffix}"
    return {
        "path": f"notes/{stem}.md",
        "anchor": f"^{anchor}",
        "wikilink": f"[[notes/{stem}#^{anchor}|{kind}: {asset_id}]]",
    }


def counts(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        kind: sum(record["asset_type"] == kind for record in records)
        for kind in ("text", "table", "figure")
    }


def write_bundle(
    stage: Path,
    manifest: Any,
    source_identity: dict[str, Any],
    records: list[dict[str, Any]],
    budget: BundleOutputBudget,
) -> None:
    budget.clear_projection()
    for record in records:
        note_path = stage / record["foam"]["path"]
        note_path.parent.mkdir(parents=True, exist_ok=True)
        _write_text(note_path, asset_note(record), budget)

    jsonl = "".join(f"{canonical_json(record)}\n" for record in records)
    _write_text(stage / "assets.jsonl", jsonl, budget)
    _write_text(
        stage / "index.md",
        foam_index(manifest, source_identity, records),
        budget,
    )
    asset_inventory = [
        {
            "asset_key": record["asset_key"],
            "asset_id": record["asset_id"],
            "asset_type": record["asset_type"],
            "content_sha256": record["content_sha256"],
            "record_sha256": record["record_sha256"],
            "note_path": record["foam"]["path"],
            "media_path": record["content"].get("media_path", ""),
        }
        for record in records
    ]
    payload = {
        "bundle_version": BUNDLE_VERSION,
        "doc_id": manifest.doc_id,
        "source_identity": source_identity,
        "counts": counts(records),
        "asset_count": len(records),
        "assets": asset_inventory,
        "artifacts": artifact_inventory(stage),
    }
    payload["bundle_sha256"] = sha256_text(canonical_json(payload))
    _write_text(
        stage / "manifest.json",
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        budget,
    )


def _write_text(path: Path, value: str, budget: BundleOutputBudget) -> None:
    data = value.encode("utf-8")
    budget.reserve(len(data))
    path.write_bytes(data)


def asset_note(record: dict[str, Any]) -> str:
    source = record["source_identity"]
    foam = record["foam"]
    lines = [
        "---",
        f"title: {json.dumps(record['asset_key'], ensure_ascii=False)}",
        f"type: {json.dumps(record['asset_type'] + '_agent_asset')}",
        'tags: ["asset-aware", "agent-asset", "foam"]',
        f"source_doc_id: {json.dumps(record['doc_id'])}",
        f"source_sha256: {json.dumps(source['source_sha256'])}",
        f"source_kind: {json.dumps(source['source_kind'])}",
        f"source_media_type: {json.dumps(source['source_media_type'])}",
        f"asset_id: {json.dumps(record['asset_id'], ensure_ascii=False)}",
        f"content_sha256: {json.dumps(record['content_sha256'])}",
        "---",
        "",
        f"# Agent Asset: {record['asset_key']}",
        "",
        f"- `source_doc_id`: `{record['doc_id']}`",
        f"- `record_sha256`: `{record['record_sha256']}`",
        f"- `page`: {record['locator'].get('page') or '?'}",
        "",
    ]
    content = record["content"]
    if record["asset_type"] == "figure":
        if content.get("media_path"):
            lines.extend([f"![{record['asset_id']}](../{content['media_path']})", ""])
        if content.get("caption"):
            lines.extend([str(content["caption"]), ""])
    elif record["asset_type"] == "table":
        lines.extend([str(content.get("markdown") or content.get("preview") or ""), ""])
    else:
        lines.extend([str(content.get("text") or ""), ""])
    lines.extend(
        [
            foam["anchor"],
            "",
            "## Citation provenance",
            "",
            "```json",
            json.dumps(
                record["citation"], ensure_ascii=False, indent=2, sort_keys=True
            ),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def foam_index(
    manifest: Any,
    source_identity: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    title = manifest.title or manifest.filename or manifest.doc_id
    lines = [
        "---",
        f"title: {json.dumps('Agent assets: ' + title, ensure_ascii=False)}",
        'type: "agent_asset_hub"',
        'tags: ["asset-aware", "agent-assets", "foam"]',
        f"source_doc_id: {json.dumps(manifest.doc_id)}",
        f"source_sha256: {json.dumps(source_identity['source_sha256'])}",
        f"source_kind: {json.dumps(source_identity['source_kind'])}",
        f"source_media_type: {json.dumps(source_identity['source_media_type'])}",
        "---",
        "",
        f"# Agent Assets: {title}",
        "",
        "> Portable Foam subtree: keep `index.md`, `notes/**`, and the bundle "
        "artifacts together.",
        "",
        "- [Bundle manifest](manifest.json)",
        "- [Agent-readable JSONL](assets.jsonl)",
        f"- `source_doc_id`: `{manifest.doc_id}`",
        f"- `identity_sha256`: `{source_identity['identity_sha256']}`",
        "",
        "## Assets",
        "",
    ]
    for record in records:
        lines.append(
            f"- {record['foam']['wikilink']} `{record['content_sha256'][:12]}`"
        )
    return "\n".join(lines).rstrip() + "\n"


def artifact_inventory(stage: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(stage).as_posix(),
            "sha256": file_sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(item for item in stage.rglob("*") if item.is_file())
    ]
