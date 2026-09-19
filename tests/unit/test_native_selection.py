"""Strict JSON pointers, Unicode spans and location-bound evidence identities."""

from copy import deepcopy

import pytest

from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_selection import (
    NativeSelectionReference,
    NativeSelectionSelector,
    canonical_selection,
    resolve_pointer,
    selection_record,
)
from tests.native_derivation_helpers import pair, service_at


@pytest.mark.parametrize(
    "pointer,expected",
    [
        ("", {"a/b": {"~x": [0, False, None, ""]}, "": 9, "~1": "literal"}),
        ("/a~1b/~0x/0", 0),
        ("/a~1b/~0x/1", False),
        ("/a~1b/~0x/2", None),
        ("/a~1b/~0x/3", ""),
        ("/", 9),
        ("/~01", "literal"),
    ],
)
def test_rfc6901_exact_members_and_typed_values(pointer, expected):
    data = {"a/b": {"~x": [0, False, None, ""]}, "": 9, "~1": "literal"}
    value = resolve_pointer(data, NativeSelectionSelector(pointer=pointer).pointer)
    assert value == expected and type(value) is type(expected)


@pytest.mark.parametrize(
    "pointer", ["#", "#/x", "$.x", "x", "/~", "/~2", "/\ud800", "/x" * 65]
)
def test_invalid_pointer_syntax(pointer):
    with pytest.raises(ValueError):
        NativeSelectionSelector(pointer=pointer)


@pytest.mark.parametrize(
    "pointer", ["/x/01", "/x/-", "/x/-1", "/x/+0", "/x/2", "/x/0/a", "/missing", "/é"]
)
def test_invalid_pointer_resolution(pointer):
    with pytest.raises(ValueError):
        resolve_pointer({"x": [0, 1], "e\u0301": "no normalization"}, pointer)


def test_codepoints_utf8_context_and_selector_hash(tmp_path):
    _, claim = pair(service_at(tmp_path))
    parent = NativeDocumentRequest(op="verify", reference=claim["target"]).reference
    selector = NativeSelectionSelector(
        pointer="/text", char_range={"start": 1, "end": 4}
    )
    record = selection_record(parent, selector, {"text": "前研😀e\u0301後"})
    assert record["value"] == "研😀e"
    assert record["text_context"]["char_range"] == [1, 4]
    assert record["text_context"]["utf8_byte_range"] == [3, 11]
    assert record["text_context"]["prefix"] == "前"
    assert record["text_context"]["suffix"] == "\u0301後"
    same = selection_record(
        parent, NativeSelectionSelector(pointer="/other"), {"other": "研😀e"}
    )
    assert same["value"] == record["value"]
    assert same["evidence"]["value_sha256"] != record["evidence"]["value_sha256"]
    for value in [
        {"start": 1, "end": 1},
        {"start": -1, "end": 1},
        {"start": True, "end": 2},
    ]:
        with pytest.raises(ValueError):
            NativeSelectionSelector(char_range=value)
    for value in [0, None, False, "短"]:
        with pytest.raises(ValueError):
            selection_record(parent, selector, {"text": value})


def test_selection_parent_is_full_same_identity_not_nested(tmp_path):
    _, claim = pair(service_at(tmp_path))
    parent = NativeDocumentRequest(op="verify", reference=claim["target"]).reference
    ref = selection_record(parent, NativeSelectionSelector(), {})["evidence"]
    for field, value in [
        ("asset_id", "file_" + "f" * 32),
        ("revision", "f" * 64),
        ("parent", ref),
        ("parent", claim["sources"][0]),
    ]:
        bad = deepcopy(ref)
        bad[field] = value
        with pytest.raises(ValueError):
            NativeSelectionReference.model_validate(bad)


def test_selection_serialization_budget_and_nonfinite_values():
    for value in ["x" * (16 * 1024 * 1024), float("nan"), float("inf")]:
        with pytest.raises(ValueError):
            canonical_selection(value)
