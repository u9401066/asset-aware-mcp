"""
Domain Layer - Value Objects

Immutable objects that describe characteristics of entities.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal


class AssetType(str, Enum):
    """Asset types in a document."""

    TABLE = "table"
    FIGURE = "figure"
    SECTION = "section"
    FULL_TEXT = "full_text"


# ============================================================================
# AssetRef — 統一資產引用（支援任意來源）
# ============================================================================

# AssetRef 支援的來源類型
SourceType = Literal[
    "section",  # PDF 章節
    "figure",  # PDF 圖片
    "table",  # PDF 表格
    "full_text",  # PDF 全文
    "span",  # citation-ready evidence span
    "kg_entity",  # 知識圖譜實體
    "external",  # 外部 URL / DOI
    "user_input",  # 使用者直接提供的文字
]


@dataclass(frozen=True)
class AssetRef:
    """
    統一資產引用 — 指向任何可引用的資料來源。

    做表不依賴拆解的關鍵：支援 7 種來源類型，
    包含 PDF 資產、知識圖譜實體、外部 URL、使用者輸入。

    Examples:
        # PDF 章節引用
        AssetRef("section", doc_id="doc_xxx", asset_id="sec_methods", page=5,
                 excerpt="dose was 5mg/kg")

        # 使用者口述
        AssetRef("user_input", excerpt="Patient reported 5mg daily")

        # 外部文獻
        AssetRef("external", url="https://doi.org/10.1234", label="Smith 2024")
    """

    source_type: SourceType

    # 定位（PDF 資產用）
    doc_id: str = ""
    asset_id: str = ""
    block_id: str = ""
    span_id: str = ""
    page: int | None = None
    line_range: tuple[int, int] | None = None
    char_range: tuple[int, int] | None = None
    byte_range: tuple[int, int] | None = None
    bbox: tuple[float, float, float, float] | None = None
    source_revision_id: str = ""
    locator_version: str = ""

    # 外部來源
    url: str = ""

    # 通用
    excerpt: str = ""  # 來源節錄 ≤200 chars（驗證用）
    quote: str = ""  # Exact cited quote when narrower than the source span
    quote_sha256: str = ""
    label: str = ""  # 人類可讀標籤
    craap: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate and truncate excerpt."""
        if self.excerpt and len(self.excerpt) > 200:
            object.__setattr__(self, "excerpt", self.excerpt[:200])
        if self.quote and not self.quote_sha256:
            import hashlib

            object.__setattr__(
                self,
                "quote_sha256",
                hashlib.sha256(self.quote.encode("utf-8")).hexdigest(),
            )

    @classmethod
    def from_doc_asset(
        cls,
        source_type: SourceType,
        doc_id: str,
        asset_id: str,
        page: int | None = None,
        excerpt: str = "",
        label: str = "",
    ) -> AssetRef:
        """從 PDF 文件資產建立引用。"""
        return cls(
            source_type=source_type,
            doc_id=doc_id,
            asset_id=asset_id,
            page=page,
            excerpt=excerpt,
            label=label,
        )

    @classmethod
    def from_url(cls, url: str, label: str = "", excerpt: str = "") -> AssetRef:
        """從外部 URL/DOI 建立引用。"""
        return cls(
            source_type="external",
            url=url,
            label=label,
            excerpt=excerpt,
        )

    @classmethod
    def from_user_input(cls, excerpt: str, label: str = "") -> AssetRef:
        """從使用者輸入建立引用。"""
        return cls(
            source_type="user_input",
            excerpt=excerpt,
            label=label,
        )

    @classmethod
    def from_kg_entity(cls, label: str, excerpt: str = "") -> AssetRef:
        """從知識圖譜實體建立引用。"""
        return cls(
            source_type="kg_entity",
            label=label,
            excerpt=excerpt,
        )

    @property
    def access_path(self) -> str:
        """MCP 存取路徑，方便 Agent 跳轉。"""
        if self.source_type == "external":
            return self.url
        if self.source_type == "user_input":
            return f"[user_input] {self.excerpt[:50]}"
        if self.source_type == "kg_entity":
            return f"consult_knowledge_graph('{self.label}')"
        if self.source_type == "span":
            return f"find_evidence_spans('{self.doc_id}', span_id='{self.span_id}')"
        return (
            f"fetch_document_asset('{self.doc_id}', "
            f"'{self.source_type}', '{self.asset_id}')"
        )

    def to_short(self) -> str:
        """簡短引用文字（用於腳註）。"""
        if self.label:
            return self.label
        if self.source_type == "user_input":
            return f"user: {self.excerpt[:50]}"
        if self.source_type == "external":
            return self.url[:60]
        if self.source_type == "kg_entity":
            return f"KG: {self.excerpt[:50]}"
        parts = [self.doc_id]
        if self.asset_id:
            parts.append(self.asset_id)
        if self.span_id:
            parts.append(self.span_id)
        if self.page:
            parts.append(f"p.{self.page}")
        return "/".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """序列化為 dict（JSON 持久化用）。"""
        d: dict[str, Any] = {"source_type": self.source_type}
        if self.doc_id:
            d["doc_id"] = self.doc_id
        if self.asset_id:
            d["asset_id"] = self.asset_id
        if self.block_id:
            d["block_id"] = self.block_id
        if self.span_id:
            d["span_id"] = self.span_id
        if self.page is not None:
            d["page"] = self.page
        if self.line_range is not None:
            d["line_range"] = list(self.line_range)
        if self.char_range is not None:
            d["char_range"] = list(self.char_range)
        if self.byte_range is not None:
            d["byte_range"] = list(self.byte_range)
        if self.bbox is not None:
            d["bbox"] = list(self.bbox)
        if self.source_revision_id:
            d["source_revision_id"] = self.source_revision_id
        if self.locator_version:
            d["locator_version"] = self.locator_version
        if self.url:
            d["url"] = self.url
        if self.excerpt:
            d["excerpt"] = self.excerpt
        if self.quote:
            d["quote"] = self.quote
        if self.quote_sha256:
            d["quote_sha256"] = self.quote_sha256
        if self.label:
            d["label"] = self.label
        if self.craap is not None:
            d["craap"] = self.craap
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssetRef:
        """從 dict 反序列化。"""
        line_range = data.get("line_range")
        if line_range and isinstance(line_range, list):
            line_range = tuple(line_range)  # type: ignore[assignment]
        char_range = data.get("char_range")
        if char_range and isinstance(char_range, list):
            char_range = tuple(char_range)  # type: ignore[assignment]
        byte_range = data.get("byte_range")
        if byte_range and isinstance(byte_range, list):
            byte_range = tuple(byte_range)  # type: ignore[assignment]
        bbox = data.get("bbox")
        if bbox and isinstance(bbox, list):
            bbox = tuple(float(item) for item in bbox)  # type: ignore[assignment]
        craap = data.get("craap")
        if not isinstance(craap, dict):
            craap = None
        return cls(
            source_type=data["source_type"],
            doc_id=data.get("doc_id", ""),
            asset_id=data.get("asset_id", ""),
            block_id=data.get("block_id", ""),
            span_id=data.get("span_id", ""),
            page=data.get("page"),
            line_range=line_range,  # type: ignore[arg-type]
            char_range=char_range,  # type: ignore[arg-type]
            byte_range=byte_range,  # type: ignore[arg-type]
            bbox=bbox,  # type: ignore[arg-type]
            source_revision_id=data.get("source_revision_id", ""),
            locator_version=data.get("locator_version", ""),
            url=data.get("url", ""),
            excerpt=data.get("excerpt", ""),
            quote=data.get("quote", ""),
            quote_sha256=data.get("quote_sha256", ""),
            label=data.get("label", ""),
            craap=craap,
        )


class DocId:
    """
    Value Object for Document Identifier.

    Validated and immutable document ID.
    Format: doc_{name}_{hash}
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not self._is_valid(value):
            raise ValueError(f"Invalid doc_id format: {value}")
        self._value = value

    @staticmethod
    def _is_valid(value: str) -> bool:
        """Validate doc_id format."""
        if not value:
            return False
        # Must start with 'doc_' and contain only alphanumeric + underscore
        return bool(re.match(r"^doc_[a-z0-9_]+$", value))

    @classmethod
    def generate(cls, filename: str, unique_suffix: str) -> DocId:
        """Generate a new DocId from filename."""
        import hashlib

        # Clean filename
        name = re.sub(r"[^a-z0-9]", "_", filename.lower())[:30]
        # Add hash for uniqueness
        hash_suffix = hashlib.md5(unique_suffix.encode()).hexdigest()[:6]  # noqa: S324 — non-security use for ID generation
        return cls(f"doc_{name}_{hash_suffix}")

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"DocId({self._value!r})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, DocId):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return False

    def __hash__(self) -> int:
        return hash(self._value)


class ImageMediaType(str, Enum):
    """Supported image MIME types."""

    PNG = "image/png"
    JPEG = "image/jpeg"
    GIF = "image/gif"
    WEBP = "image/webp"
    BMP = "image/bmp"

    @classmethod
    def from_extension(cls, ext: str) -> ImageMediaType:
        """Get media type from file extension."""
        ext_map = {
            "png": cls.PNG,
            "jpg": cls.JPEG,
            "jpeg": cls.JPEG,
            "gif": cls.GIF,
            "webp": cls.WEBP,
            "bmp": cls.BMP,
        }
        return ext_map.get(ext.lower(), cls.PNG)
