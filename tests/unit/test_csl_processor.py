"""Real CSL document context: previous citations, sorting, notes and rich output."""

import json
import shutil
from copy import deepcopy

import pytest

from src.application.csl_markup import safe_csl_html
from src.domain.csl_citations import CslDocument
from src.infrastructure.csl_processor import NodeCslProcessor


def book(item_id, title, family="Doe", given="Jane", year=2020):
    return {
        "id": item_id,
        "type": "book",
        "title": title,
        "author": [{"family": family, "given": given}],
        "issued": {"date-parts": [[year]]},
        "publisher": "Example Press",
    }


def document(style="apa", *, ids=("b", "a", "b"), notes=False):
    return CslDocument.model_validate(
        {
            "style": style,
            "items": [book("a", "Alpha"), book("b", "Beta")],
            "clusters": [
                {
                    "id": f"cite-{i}",
                    "note_index": i + 1 if notes else 0,
                    "cites": [{"id": item_id}],
                }
                for i, item_id in enumerate(ids)
            ],
        }
    )


@pytest.fixture
def processor():
    if not shutil.which("node"):
        pytest.skip("CSL integration requires optional Node.js >=20")
    return NodeCslProcessor()


def test_apa_retroactively_disambiguates_prior_citations_and_sorts_bibliography(
    processor,
):
    doc = document()
    original = deepcopy(doc.model_dump())
    result = processor.render(doc)
    assert result["text"]["citations"] == [
        "(Doe, 2020b)",
        "(Doe, 2020a)",
        "(Doe, 2020b)",
    ]
    assert result["text"]["entry_ids"] == [["a"], ["b"]]
    assert result["text"]["bibliography"] == [
        "Doe, J. (2020a). Alpha. Example Press.\n",
        "Doe, J. (2020b). Beta. Example Press.\n",
    ]
    assert "<i>Alpha</i>" in result["html"]["bibliography"][0]
    assert doc.model_dump() == original
    assert processor.render(doc) == result


def test_vancouver_uses_first_citation_order_and_reuses_numbers(processor):
    result = processor.render(document("vancouver"))
    assert result["text"]["citations"] == ["(1)", "(2)", "(1)"]
    assert result["text"]["entry_ids"] == [["b"], ["a"]]


def test_chicago_first_and_subsequent_notes(processor):
    doc = document("chicago-notes-bibliography", ids=("a", "a"), notes=True)
    result = processor.render(doc)
    assert result["text"]["citations"] == [
        "Jane Doe, Alpha (Example Press, 2020).",
        "Doe, Alpha.",
    ]
    assert result["text"]["entry_ids"] == [["a"]]


def test_chicago_author_date_retains_cluster_order_when_style_has_no_citation_sort(
    processor,
):
    raw = document("chicago-author-date").model_dump()
    raw["clusters"] = [{"id": "group", "cites": [{"id": "b"}, {"id": "a"}]}]
    result = processor.render(CslDocument.model_validate(raw))
    # Official Chicago 18 CSL has bibliography sort, but no citation sort element.
    assert result["text"]["citations"] == ["(Doe 2020b, 2020a)"]


def test_apa_sorts_cluster_authors_and_collapses_repeated_years(processor):
    raw = document().model_dump()
    raw["items"][1]["author"] = [{"family": "Zhang", "given": "Min"}]
    raw["clusters"] = [{"id": "group", "cites": [{"id": "b"}, {"id": "a"}]}]
    result = processor.render(CslDocument.model_validate(raw))
    assert result["text"]["citations"] == ["(Doe, 2020; Zhang, 2020)"]


def test_javascript_prototype_names_are_safe_bibliographic_ids(processor):
    raw = document().model_dump()
    raw["items"][0]["id"] = "__proto__"
    raw["clusters"] = [{"id": "constructor", "cites": [{"id": "__proto__"}]}]
    result = processor.render(CslDocument.model_validate(raw))
    assert result["text"]["citations"] == ["(Doe, 2020)"]
    assert result["text"]["entry_ids"] == [["__proto__"]]


def test_literal_unicode_names_dates_locators_and_uncited_items(processor):
    raw = document().model_dump()
    raw["locale"] = "zh-TW"
    raw["items"][0]["author"] = [{"literal": "國家研究院"}]
    raw["clusters"] = [{"id": "unicode", "cites": [{"id": "a", "locator": "007–009"}]}]
    raw["uncited_ids"] = ["b"]
    result = processor.render(CslDocument.model_validate(raw))
    assert "國家研究院" in result["text"]["citations"][0]
    assert "007" in result["text"]["citations"][0]
    assert {x[0] for x in result["text"]["entry_ids"]} == {"a", "b"}


@pytest.mark.parametrize(
    "mutate",
    [
        lambda x: x["items"].append(x["items"][0]),
        lambda x: x["clusters"].append(x["clusters"][0]),
        lambda x: x["clusters"][0]["cites"][0].update(id="missing"),
        lambda x: x["clusters"][0]["cites"][0].update(source_keys=["missing"]),
        lambda x: x.update(sources={"unused": {}}),
        lambda x: x["items"][0].update(id=True),
        lambda x: x["clusters"][0].update(note_index=1),
    ],
)
def test_rejects_inconsistent_citation_graph(mutate):
    raw = document().model_dump()
    mutate(raw)
    with pytest.raises(ValueError):
        CslDocument.model_validate(raw)


def test_official_schema_rejects_flat_authors_and_unknown_fields(processor):
    raw = document().model_dump()
    raw["items"][0]["author"] = "Jane Doe"
    with pytest.raises(ValueError, match="CSL-JSON"):
        processor.render(CslDocument.model_validate(raw))


def test_safe_typography_removes_attributes_links_embeds_and_wikilinks():
    result = safe_csl_html(
        '<div class="csl-entry" onclick="bad()"><i>Title</i> <span style="font-variant:small-caps;">Name</span><a href="javascript:bad()">Link</a><script>bad()</script> [[secret]]<img src="https://tracking.invalid"></div>'
    )
    assert (
        result
        == '<div class="csl-entry"><i>Title</i> <span style="font-variant:small-caps;">Name</span>Linkbad() &#91;&#91;secret&#93;&#93;</div>'
    )


def test_node_missing_is_explicit(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    processor = NodeCslProcessor()
    assert not processor.capabilities()["configured"]
    with pytest.raises(ValueError, match=r"Node\.js"):
        processor.render(document())


def test_real_worker_timeout_is_bounded(processor):
    processor.timeout = 0.001
    with pytest.raises(ValueError, match="time limit"):
        processor.render(document())


def test_resource_drift_fails_before_execution(monkeypatch, tmp_path):
    from src.infrastructure import csl_processor

    shutil.copytree(csl_processor.RESOURCE_ROOT, tmp_path / "resources")
    monkeypatch.setattr(csl_processor, "RESOURCE_ROOT", tmp_path / "resources")
    (tmp_path / "resources" / "apa.csl").write_text("drift", encoding="utf-8")
    with pytest.raises(ValueError, match="integrity mismatch"):
        NodeCslProcessor().capabilities()


def test_vendored_processor_matches_audited_npm_release():
    from src.infrastructure.csl_processor import RESOURCE_ROOT

    manifest = json.loads((RESOURCE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    lock = json.loads((RESOURCE_ROOT / "package-lock.json").read_text(encoding="utf-8"))
    package = lock["packages"]["node_modules/citeproc"]
    assert package["version"] == manifest["version"] == "2.4.63"
    assert package["integrity"] == manifest["npm_integrity"]
    assert package["resolved"] == manifest["files"]["citeproc.js"]["url"]
    assert manifest["processor_version"] == "1.4.61"


def test_node_options_cannot_inject_a_preload(processor, monkeypatch):
    monkeypatch.setenv("NODE_OPTIONS", "--require /does-not-exist.cjs")
    assert processor.render(document())["text"]["citations"][0] == "(Doe, 2020b)"


def test_raw_metadata_markup_never_becomes_active_wiki_content(processor):
    raw = document().model_dump()
    raw["items"][0]["title"] = "<i>Alpha</i> [[unrelated]] <script>alert(1)</script>"
    raw["items"][0]["URL"] = "javascript:alert(2)"
    result = processor.render(CslDocument.model_validate(raw))
    safe = safe_csl_html(result["html"]["bibliography"][0])
    assert "<script" not in safe and "href=" not in safe and "[[unrelated]]" not in safe
    assert "<i>" in safe
