"""Document-context citation inputs, distinct from canonical source evidence."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

MAX_CSL_INPUT_BYTES = 2 * 1024 * 1024
MAX_CSL_OUTPUT_BYTES = 8 * 1024 * 1024
CslStyle = Literal[
    "apa", "chicago-author-date", "chicago-notes-bibliography", "vancouver"
]
CslId = Annotated[str, StringConstraints(min_length=1, max_length=256)]


class CslModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CslCite(CslModel):
    id: CslId
    locator: str | None = Field(None, min_length=1, max_length=256)
    label: Literal[
        "book",
        "chapter",
        "column",
        "figure",
        "folio",
        "issue",
        "line",
        "note",
        "opus",
        "page",
        "paragraph",
        "part",
        "section",
        "sub-verbo",
        "verse",
        "volume",
        "number",
        "timestamp",
    ] = "page"
    prefix: str = Field("", max_length=1024)
    suffix: str = Field("", max_length=1024)
    suppress_author: bool = False
    source_keys: list[CslId] = Field(default_factory=list, max_length=100)


class CslCluster(CslModel):
    id: CslId
    note_index: int = Field(0, ge=0, le=1_000_000)
    cites: list[CslCite] = Field(min_length=1, max_length=100)


class CslDocument(CslModel):
    version: Literal["csl-citation-document-v1"] = "csl-citation-document-v1"
    style: CslStyle
    locale: Literal["en-US", "zh-TW"] = "en-US"
    items: list[dict[str, Any]] = Field(min_length=1, max_length=500)
    clusters: list[CslCluster] = Field(min_length=1, max_length=1000)
    uncited_ids: list[CslId] = Field(default_factory=list, max_length=500)
    sources: dict[CslId, dict[str, Any]] = Field(default_factory=dict, max_length=1000)

    @model_validator(mode="after")
    def check_document(self) -> CslDocument:
        pending = [(self.model_dump(mode="python"), 0)]
        while pending:
            value, depth = pending.pop()
            if depth > 32:
                raise ValueError("Citation document nesting exceeds 32 levels")
            if isinstance(value, dict):
                if {"__proto__", "constructor", "prototype"} & value.keys():
                    raise ValueError("Reserved JavaScript property in CSL metadata")
                pending.extend((child, depth + 1) for child in value.values())
            elif isinstance(value, list):
                pending.extend((child, depth + 1) for child in value)
        encoded = json.dumps(
            self.model_dump(mode="json"), ensure_ascii=False, allow_nan=False
        )
        if len(encoded.encode("utf-8")) > MAX_CSL_INPUT_BYTES:
            raise ValueError("Citation document exceeds input byte limit")
        ids = [item.get("id") for item in self.items]
        if any(not isinstance(i, str) or not i or len(i) > 256 for i in ids):
            raise ValueError(
                "CSL items require nonempty string IDs of at most 256 characters"
            )
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate CSL item ID")
        cluster_ids = [cluster.id for cluster in self.clusters]
        if len(set(cluster_ids)) != len(cluster_ids):
            raise ValueError("Duplicate citation cluster ID")
        used = {cite.id for cluster in self.clusters for cite in cluster.cites}
        if (used | set(self.uncited_ids)) - set(ids):
            raise ValueError("Citation or uncited item ID is missing from items")
        if len(set(self.uncited_ids)) != len(self.uncited_ids):
            raise ValueError("Duplicate uncited item ID")
        keys = {
            key
            for cluster in self.clusters
            for cite in cluster.cites
            for key in cite.source_keys
        }
        if keys != set(self.sources):
            raise ValueError(
                "Source keys must exactly match the references used by citations"
            )
        if self.style == "chicago-notes-bibliography":
            notes = [cluster.note_index for cluster in self.clusters]
            if any(n <= 0 for n in notes) or notes != sorted(notes):
                raise ValueError(
                    "Chicago notes require positive, ordered note_index values"
                )
        elif any(cluster.note_index for cluster in self.clusters):
            raise ValueError("In-text citation styles require note_index=0")
        return self


class CslProcessor(Protocol):
    def capabilities(self) -> dict[str, Any]: ...

    def render(self, document: CslDocument) -> dict[str, Any]: ...
