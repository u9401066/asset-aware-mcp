"""Pinned, offline CSL assets and a bounded optional Node.js processor."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from src.domain.csl_citations import MAX_CSL_OUTPUT_BYTES, CslDocument

RESOURCE_ROOT = Path(__file__).with_name("csl_resources")
WORKER = Path(__file__).with_name("csl_worker.cjs")
MANIFEST_SHA256 = "97beaf131e1784d8dc694fc9de9afd7270b9cc773f46cab52ea4cf4885b4a953"


class NodeCslProcessor:
    def __init__(self, node: str | None = None, *, timeout: float = 30):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("CSL timeout must be finite and positive")
        self.node = node or shutil.which("node")
        self.timeout = timeout

    def _resources(self) -> tuple[dict[str, Any], dict[str, bytes]]:
        encoded = (RESOURCE_ROOT / "manifest.json").read_bytes()
        if hashlib.sha256(encoded).hexdigest() != MANIFEST_SHA256:
            raise ValueError("Bundled CSL manifest integrity mismatch")
        manifest = json.loads(encoded)
        data = {}
        for name, entry in manifest["files"].items():
            value = (RESOURCE_ROOT / name).read_bytes()
            if (
                len(value) != entry["size"]
                or hashlib.sha256(value).hexdigest() != entry["sha256"]
            ):
                raise ValueError("Bundled CSL resource integrity mismatch: " + name)
            data[name] = value
        return manifest, data

    def capabilities(self) -> dict[str, Any]:
        manifest, _ = self._resources()
        return {
            "processor": manifest["processor"],
            "processor_version": manifest["version"],
            "configured": bool(self.node),
            "runtime": "optional local Node.js >=20",
            "styles": manifest["styles"],
            "locales": ["en-US", "zh-TW"],
            "network": "none",
            "custom_templates": "existing citation-format-v1 is unchanged",
        }

    def render(self, document: CslDocument) -> dict[str, Any]:
        if not self.node:
            raise ValueError(
                "CSL rendering requires a local Node.js >=20 executable on PATH"
            )
        manifest, assets = self._resources()
        schema = json.loads(assets["csl-data.json"])
        # The pinned schema is self-contained. No caller schema or remote refs enter it.
        errors = Draft7Validator(schema).iter_errors(document.items)
        first = next(errors, None)
        if first:
            raise ValueError("Invalid CSL-JSON items: " + str(first.message)[:1500])
        style_name = document.style + ".csl"
        payload = {
            "document": document.model_dump(mode="json"),
            "style": assets[style_name].decode("utf-8"),
            "locales": {
                locale: assets[locale + ".xml"].decode("utf-8")
                for locale in ("en-US", "zh-TW", "zh-CN")
            },
        }
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"NODE_OPTIONS", "NODE_PATH", "NODE_REPL_EXTERNAL_MODULE"}
        }
        try:
            result = subprocess.run(
                [self.node, "--max-old-space-size=192", str(WORKER)],
                input=json.dumps(payload, ensure_ascii=False, allow_nan=False).encode(
                    "utf-8"
                ),
                capture_output=True,
                env=env,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("CSL processor exceeded its time limit") from exc
        except OSError as exc:
            raise ValueError("CSL Node.js process could not start") from exc
        if result.returncode:
            raise ValueError(
                "CSL processor failed: "
                + result.stderr[:2000].decode("utf-8", errors="replace")
            )
        if len(result.stdout) > MAX_CSL_OUTPUT_BYTES:
            raise ValueError("CSL processor exceeded output byte limit")
        rendered = json.loads(result.stdout)
        if not isinstance(rendered, dict):
            raise ValueError("CSL processor returned an invalid result")
        if rendered.get("processor_version") != manifest["processor_version"]:
            raise ValueError("Unexpected CSL processor version")
        rendered["resources"] = {
            "processor": "citeproc-js",
            "version": manifest["version"],
            "processor_version": manifest["processor_version"],
            "node_version": rendered["node_version"],
            "manifest_sha256": hashlib.sha256(
                (RESOURCE_ROOT / "manifest.json").read_bytes()
            ).hexdigest(),
            "worker_sha256": hashlib.sha256(WORKER.read_bytes()).hexdigest(),
            "files": {
                name: manifest["files"][name]
                for name in (
                    "citeproc.js",
                    style_name,
                    "en-US.xml",
                    "zh-TW.xml",
                    "zh-CN.xml",
                    "csl-data.json",
                )
            },
        }
        return rendered
