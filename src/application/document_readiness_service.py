"""Read-only document readiness contract for AI-facing MCP workflows."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

READINESS_SCHEMA_VERSION = "document-readiness-v2"

AI_READINESS_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("manifest", "{doc_id}_manifest.json"),
    ("markdown", "{doc_id}_full.md"),
    ("blocks", "blocks.json"),
    ("segmentation", "segmentation.json"),
    ("citation_index", "citation_index.jsonl"),
    ("citation_status", "citation_index.status.json"),
    ("ai_safety_report", "ai_safety_report.json"),
    ("native_structure", "native_structure.json"),
    ("segmentation_coverage", "segmentation_coverage.json"),
    ("accessibility_report", "accessibility_report.json"),
    ("section_pointer_index", "section_pointer_index.jsonl"),
)

AI_READINESS_REQUIRED_AUDITS: tuple[str, ...] = (
    "ai_safety_report",
    "native_structure",
    "segmentation_coverage",
    "accessibility_report",
)

_CAPABILITY_NAMES: tuple[tuple[str, str], ...] = (
    ("has_markdown", "markdown"),
    ("has_blocks", "blocks"),
    ("has_segmentation", "segmentation"),
    ("has_citation_index", "citation_index"),
    ("has_citation_status", "citation_status"),
    ("has_ai_safety_report", "ai_safety_report"),
    ("has_native_structure", "native_structure"),
    ("has_coverage_report", "segmentation_coverage"),
    ("has_accessibility_report", "accessibility_report"),
    ("has_section_pointer_index", "section_pointer_index"),
)

_WARNING_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("blocks", "missing_blocks"),
    ("segmentation", "missing_segmentation"),
    ("citation_index", "missing_citation_index"),
    ("citation_status", "missing_citation_status"),
    ("section_pointer_index", "missing_section_pointer_index"),
)

_INVALID_AUDIT_STATUSES = {"unavailable", "skipped", "failed", "error"}


class DocumentReadinessService:
    """Build agent-friendly readiness payloads without mutating document storage."""

    def __init__(self, repository: Any):
        self.repository = repository

    def artifact_paths(self, doc_id: str, doc_dir: Path) -> dict[str, Path]:
        return {
            name: doc_dir / template.format(doc_id=doc_id)
            for name, template in AI_READINESS_ARTIFACTS
        }

    def discover_artifacts(
        self,
        doc_id: str,
        *,
        artifacts: Any = None,
        manifest: Any | None = None,
    ) -> dict[str, str]:
        """Return known artifact paths without calling create-on-read APIs."""
        discovered = self._normalize_artifacts(artifacts)
        loaded_manifest = (
            manifest if manifest is not None else self._load_manifest(doc_id)
        )
        doc_dir = self.existing_doc_dir(doc_id, loaded_manifest)
        if doc_dir is None:
            return discovered

        for name, path in self.artifact_paths(doc_id, doc_dir).items():
            if path.exists():
                discovered[name] = str(path)
        return discovered

    def build_payload(self, doc_id: str) -> dict[str, Any]:
        manifest = self._load_manifest(doc_id)
        if manifest is None:
            return self._unavailable_payload(doc_id)

        doc_dir = self.existing_doc_dir(doc_id, manifest)
        artifact_paths = self.artifact_paths(doc_id, doc_dir) if doc_dir else {}
        artifacts = self.discover_artifacts(doc_id, manifest=manifest)
        capabilities = self.capabilities(artifacts)
        audit_artifacts = self.audit_artifacts(
            artifacts,
            manifest=manifest,
            doc_dir=doc_dir,
        )
        missing_audits = [
            name for name in AI_READINESS_REQUIRED_AUDITS if name not in artifacts
        ]
        invalid_audits = [
            name
            for name, status in audit_artifacts.items()
            if not bool(status.get("valid", True))
        ]
        ocr_recommended = bool(getattr(manifest, "ocr_recommended", False))
        blockers = self.blockers(
            capabilities,
            missing_audits,
            invalid_audits,
            ocr_recommended,
        )
        warnings = self.warnings(capabilities)
        status = "ready" if not blockers else "needs_attention"
        next_actions = self.next_actions(
            doc_id,
            capabilities=capabilities,
            blockers=blockers,
            ocr_recommended=ocr_recommended,
        )
        return {
            "schema_version": READINESS_SCHEMA_VERSION,
            "doc_id": doc_id,
            "status": status,
            "blockers": blockers,
            "warnings": warnings,
            "text_quality": getattr(manifest, "text_quality_status", "unknown"),
            "ocr_recommended": ocr_recommended,
            "capabilities": capabilities,
            "artifacts": {
                name: artifacts.get(name)
                for name, _template in AI_READINESS_ARTIFACTS
                if name in artifacts or name in artifact_paths
            },
            "missing_audits": missing_audits,
            "invalid_audits": invalid_audits,
            "audit_artifacts": audit_artifacts,
            "next_actions": next_actions,
        }

    @staticmethod
    def capabilities(artifacts: dict[str, str]) -> dict[str, bool]:
        return {
            capability: artifact_name in artifacts
            for capability, artifact_name in _CAPABILITY_NAMES
        }

    @staticmethod
    def blockers(
        capabilities: dict[str, bool],
        missing_audits: list[str],
        invalid_audits: list[str],
        ocr_recommended: bool,
    ) -> list[str]:
        blockers: list[str] = []
        if not capabilities.get("has_markdown", False):
            blockers.append("missing_markdown")
        if ocr_recommended:
            blockers.append("ocr_recommended")
        blockers.extend(f"missing_{name}" for name in missing_audits)
        blockers.extend(f"invalid_{name}" for name in invalid_audits)
        return blockers

    @staticmethod
    def warnings(capabilities: dict[str, bool]) -> list[str]:
        return [
            warning
            for capability, warning in _WARNING_ARTIFACTS
            if not capabilities.get(f"has_{capability}", False)
        ]

    @staticmethod
    def next_actions(
        doc_id: str,
        *,
        capabilities: dict[str, bool],
        blockers: list[str],
        ocr_recommended: bool,
    ) -> list[str]:
        actions = [f'document(op="inspect", doc_id="{doc_id}")']
        audit_blockers = {
            "missing_ai_safety_report",
            "missing_native_structure",
            "missing_segmentation_coverage",
            "missing_accessibility_report",
            "invalid_ai_safety_report",
            "invalid_native_structure",
            "invalid_segmentation_coverage",
            "invalid_accessibility_report",
        }
        if audit_blockers.intersection(blockers):
            actions.append(f'document(op="audit", doc_id="{doc_id}")')
        if not capabilities.get("has_section_pointer_index", False):
            actions.append(f'document(op="pointer_index", doc_id="{doc_id}")')
        actions.append(f'document(op="prepare_ai", doc_id="{doc_id}")')
        if not capabilities.get("has_segmentation", False):
            actions.append(f'document(op="export_segmentation", doc_id="{doc_id}")')
        actions.append(f'document_asset(op="tree", doc_id="{doc_id}")')
        actions.append(f'evidence(op="find", doc_id="{doc_id}", query="...")')
        if ocr_recommended:
            actions.append('document(op="ocr", pdf_path="...")')
        return actions

    def existing_doc_dir(self, doc_id: str, manifest: Any | None = None) -> Path | None:
        base_doc_dir = self._base_doc_dir(doc_id)
        for raw_path in (
            getattr(manifest, "manifest_path", "") if manifest is not None else "",
            getattr(manifest, "markdown_path", "") if manifest is not None else "",
        ):
            if not raw_path:
                continue
            doc_dir = self._safe_manifest_doc_dir(
                doc_id,
                raw_path,
                base_doc_dir=base_doc_dir,
            )
            if doc_dir is not None:
                return doc_dir

        return base_doc_dir if base_doc_dir and base_doc_dir.exists() else None

    def _base_doc_dir(self, doc_id: str) -> Path | None:
        repository_attrs = getattr(self.repository, "__dict__", {})
        base_dir = repository_attrs.get("base_dir") if repository_attrs else None
        if base_dir is None:
            return None
        if not isinstance(base_dir, str | os.PathLike):
            return None
        try:
            root = Path(base_dir).resolve()
            candidate = (root / doc_id).resolve()
            candidate.relative_to(root)
        except (OSError, TypeError, ValueError):
            return None
        return candidate

    @staticmethod
    def _safe_manifest_doc_dir(
        doc_id: str,
        raw_path: str,
        *,
        base_doc_dir: Path | None,
    ) -> Path | None:
        try:
            candidate = Path(raw_path).expanduser().resolve()
        except (OSError, TypeError):
            return None
        doc_dir = candidate.parent if candidate.suffix else candidate
        if base_doc_dir is not None:
            try:
                doc_dir.resolve().relative_to(base_doc_dir.resolve())
            except (OSError, ValueError):
                return None
        elif doc_dir.name != doc_id:
            return None
        return doc_dir if doc_dir.exists() else None

    def _load_manifest(self, doc_id: str) -> Any | None:
        load_manifest = getattr(self.repository, "load_manifest", None)
        if load_manifest is None:
            return None
        try:
            return load_manifest(doc_id)
        except Exception:
            return None

    def audit_artifacts(
        self,
        artifacts: dict[str, str],
        *,
        manifest: Any,
        doc_dir: Path | None,
    ) -> dict[str, dict[str, Any]]:
        segmentation_identity = self._load_segmentation_identity(doc_dir)
        return {
            name: self._audit_artifact_status(
                name,
                artifacts[name],
                manifest=manifest,
                segmentation_identity=segmentation_identity,
            )
            for name in AI_READINESS_REQUIRED_AUDITS
            if name in artifacts
        }

    @staticmethod
    def _audit_artifact_status(
        name: str,
        raw_path: str,
        *,
        manifest: Any,
        segmentation_identity: dict[str, str],
    ) -> dict[str, Any]:
        status: dict[str, Any] = {
            "path": raw_path,
            "valid": True,
            "status": "unknown",
            "reason": "",
        }
        try:
            payload = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            status.update({"valid": False, "reason": f"invalid_json:{exc}"})
            return status
        if not isinstance(payload, dict):
            status.update({"valid": False, "reason": "invalid_json_root"})
            return status

        report_status = str(payload.get("status", "") or "").strip().lower()
        if not report_status:
            status.update({"valid": False, "reason": "missing_status"})
            return status
        status["status"] = report_status
        if report_status in _INVALID_AUDIT_STATUSES:
            status.update({"valid": False, "reason": f"status_{report_status}"})
            return status

        report_doc_id = str(payload.get("doc_id", "") or "")
        manifest_doc_id = str(getattr(manifest, "doc_id", "") or "")
        if not report_doc_id:
            status.update({"valid": False, "reason": "missing_doc_id"})
            return status
        if manifest_doc_id and report_doc_id != manifest_doc_id:
            status.update({"valid": False, "reason": "doc_id_mismatch"})
            return status

        source_pdf_sha256 = str(payload.get("source_pdf_sha256", "") or "")
        manifest_sha256 = str(getattr(manifest, "source_pdf_sha256", "") or "")
        if manifest_sha256:
            if not source_pdf_sha256:
                status.update({"valid": False, "reason": "missing_source_pdf_sha256"})
                return status
            if source_pdf_sha256 != manifest_sha256:
                status.update({"valid": False, "reason": "stale_source_pdf_sha256"})
                return status

        if name in {"segmentation_coverage", "accessibility_report"}:
            for key in ("source_revision_id", "locator_source_sha256"):
                expected = segmentation_identity.get(key, "")
                actual = str(payload.get(key, "") or "")
                if expected:
                    if not actual:
                        status.update({"valid": False, "reason": f"missing_{key}"})
                        return status
                    if actual != expected:
                        status.update({"valid": False, "reason": f"stale_{key}"})
                        return status
                elif not actual:
                    status.update({"valid": False, "reason": f"missing_{key}"})
                    return status
        return status

    @staticmethod
    def _load_segmentation_identity(doc_dir: Path | None) -> dict[str, str]:
        if doc_dir is None:
            return {}
        path = doc_dir / "segmentation.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            "source_revision_id": str(payload.get("source_revision_id", "") or ""),
            "locator_source_sha256": str(
                payload.get("locator_source_sha256", "") or ""
            ),
        }

    @staticmethod
    def _normalize_artifacts(artifacts: Any) -> dict[str, str]:
        if not isinstance(artifacts, dict):
            return {}
        return {
            str(name): str(path)
            for name, path in artifacts.items()
            if isinstance(name, str) and path
        }

    @staticmethod
    def _unavailable_payload(doc_id: str) -> dict[str, Any]:
        return {
            "schema_version": READINESS_SCHEMA_VERSION,
            "doc_id": doc_id,
            "status": "unavailable",
            "blockers": ["document_not_found"],
            "warnings": [],
            "text_quality": "unknown",
            "ocr_recommended": False,
            "capabilities": {
                capability: False for capability, _artifact in _CAPABILITY_NAMES
            },
            "artifacts": {},
            "missing_audits": list(AI_READINESS_REQUIRED_AUDITS),
            "invalid_audits": [],
            "audit_artifacts": {},
            "next_actions": ['document(op="list")'],
        }
