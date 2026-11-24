import pytest

from src.domain.revision_diff import (
    revision_diff_opcodes,
    tokenize_revision_diff_text,
)


def _ops(old: str, new: str) -> list[tuple[str, str, str]]:
    old_tokens = tokenize_revision_diff_text(old)
    new_tokens = tokenize_revision_diff_text(new)
    return [
        (tag, "".join(old_tokens[i1:i2]), "".join(new_tokens[j1:j2]))
        for tag, i1, i2, j1, j2 in revision_diff_opcodes(old_tokens, new_tokens)
    ]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "plain English words",
        "依循高醫體系負責任人工智慧（Responsible AI）治理方向。",
        "ISO 42001　與 FHIR R4\t介面",
        "ひらがなとカタカナ、한국어 문장",
    ],
)
def test_tokens_concatenate_back_to_source_text(text: str) -> None:
    assert "".join(tokenize_revision_diff_text(text)) == text


def test_cjk_characters_are_single_tokens_and_latin_words_stay_whole() -> None:
    assert tokenize_revision_diff_text("導入AI模型 v2") == [
        "導",
        "入",
        "AI",
        "模",
        "型",
        " ",
        "v2",
    ]


def test_appending_to_cjk_sentence_is_a_pure_insertion() -> None:
    assert _ops("範疇三：智慧醫療補充說明", "範疇三：智慧醫療補充說明［待核對］") == [
        ("equal", "範疇三：智慧醫療補充說明", "範疇三：智慧醫療補充說明"),
        ("insert", "", "［待核對］"),
    ]


def test_single_cjk_typo_fix_touches_only_that_character() -> None:
    assert _ops("定期舉辦神查會議", "定期舉辦審查會議") == [
        ("equal", "定期舉辦", "定期舉辦"),
        ("replace", "神", "審"),
        ("equal", "查會議", "查會議"),
    ]


def test_coincidental_cjk_match_inside_a_rewrite_is_folded() -> None:
    assert _ops("提升資料的品質", "強化系統的穩定") == [
        ("replace", "提升資料的品質", "強化系統的穩定"),
    ]


def test_pure_insertions_around_a_character_are_not_widened() -> None:
    assert _ops("甲乙丙", "甲一乙二丙") == [
        ("equal", "甲", "甲"),
        ("insert", "", "一"),
        ("equal", "乙", "乙"),
        ("insert", "", "二"),
        ("equal", "丙", "丙"),
    ]


def test_space_delimited_text_keeps_word_level_diff() -> None:
    assert _ops("keep the old wording", "keep the new wording") == [
        ("equal", "keep the ", "keep the "),
        ("replace", "old", "new"),
        ("equal", " wording", " wording"),
    ]
