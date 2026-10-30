import pytest

from stadsdelen.markdown import (
    MarkdownUpdateStatus,
    format_stadsdeel_sentence,
    parse_leading_stadsdeel,
    update_markdown,
)


def test_format_stadsdeel_sentence_single_and_multi() -> None:
    assert format_stadsdeel_sentence(["Subsidies Centrum"]) == (
        "Stadsdeel: Subsidies Centrum."
    )
    assert format_stadsdeel_sentence(["Subsidies Centrum", "Subsidies Noord"]) == (
        "Stadsdeel: Subsidies Centrum, Subsidies Noord."
    )


def test_format_stadsdeel_sentence_rejects_empty() -> None:
    with pytest.raises(ValueError):
        format_stadsdeel_sentence([])


def test_parse_leading_stadsdeel_none_when_absent() -> None:
    body = "First body paragraph."
    assert parse_leading_stadsdeel(body) == (None, body)


def test_parse_leading_stadsdeel_extracts_remainder() -> None:
    text = "Stadsdeel: A, B.\n\nBody here."
    districts, remainder = parse_leading_stadsdeel(text)
    assert districts == ("A", "B")
    assert remainder == "\n\nBody here."


def test_parse_leading_stadsdeel_not_at_start_is_ignored() -> None:
    text = "Intro.\n\nStadsdeel: A."
    assert parse_leading_stadsdeel(text) == (None, text)


def test_update_markdown_prepends_with_blank_line_before_body() -> None:
    body = "First body paragraph."
    districts = ("Subsidies Centrum", "Subsidies Noord")
    new_md, status = update_markdown(body, districts)
    assert status is MarkdownUpdateStatus.UPDATED
    assert new_md == (
        "Stadsdeel: Subsidies Centrum, Subsidies Noord.\n\nFirst body paragraph."
    )


def test_update_markdown_prepends_on_empty_body() -> None:
    new_md, status = update_markdown("", ["Subsidies Centrum"])
    assert status is MarkdownUpdateStatus.UPDATED
    assert new_md == "Stadsdeel: Subsidies Centrum."


def test_update_markdown_skips_when_district_set_matches() -> None:
    original = "Stadsdeel: Subsidies Noord, Subsidies Centrum.\n\nBody."
    districts = ("Subsidies Centrum", "Subsidies Noord")
    new_md, status = update_markdown(original, districts)
    assert status is MarkdownUpdateStatus.SKIPPED
    assert new_md == original


def test_update_markdown_replaces_prefix_only_when_districts_change() -> None:
    original = "Stadsdeel: Subsidies Centrum.\n\nKeep this body."
    new_md, status = update_markdown(
        original,
        ("Subsidies Centrum", "Subsidies Noord"),
    )
    assert status is MarkdownUpdateStatus.UPDATED
    assert new_md == (
        "Stadsdeel: Subsidies Centrum, Subsidies Noord.\n\nKeep this body."
    )


def test_update_markdown_preserves_remainder_without_extra_newlines() -> None:
    original = "Stadsdeel: Old.\nBody glued to prefix."
    new_md, status = update_markdown(original, ["Subsidies Centrum"])
    assert status is MarkdownUpdateStatus.UPDATED
    assert new_md == "Stadsdeel: Subsidies Centrum.\nBody glued to prefix."
