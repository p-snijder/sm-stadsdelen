import json
from pathlib import Path
from unittest.mock import patch

import pytest

from stadsdelen.json_io import (
    JsonSaveError,
    load_subsidy_array,
    save_subsidy_array,
)

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "json" / "subsidies-sample.json"
)


def test_save_subsidy_array_round_trip(tmp_path: Path) -> None:
    records = load_subsidy_array(FIXTURE)
    out = tmp_path / "out.json"
    save_subsidy_array(out, records, backup=False)
    loaded = load_subsidy_array(out)
    assert loaded == records
    text = out.read_text(encoding="utf-8")
    assert text.startswith("[\n  {")
    assert text.endswith("\n")
    parsed = json.loads(text)
    assert parsed == records


def test_save_subsidy_array_creates_bak(tmp_path: Path) -> None:
    target = tmp_path / "subsidies.json"
    target.write_text('{"old": true}\n', encoding="utf-8")
    records = [{"url": "https://example.com/a", "markdown": "x"}]
    bak = save_subsidy_array(target, records, backup=True)
    assert bak == tmp_path / "subsidies.json.bak"
    assert bak.read_text(encoding="utf-8") == '{"old": true}\n'
    assert load_subsidy_array(target) == records


def test_save_subsidy_array_skips_bak_when_disabled(tmp_path: Path) -> None:
    target = tmp_path / "subsidies.json"
    target.write_text("[]\n", encoding="utf-8")
    records = [{"url": "https://example.com/a", "markdown": "x"}]
    assert save_subsidy_array(target, records, backup=False) is None
    assert not (tmp_path / "subsidies.json.bak").exists()


def test_save_subsidy_array_preserves_original_on_replace_failure(
    tmp_path: Path,
) -> None:
    target = tmp_path / "subsidies.json"
    original = '[{"url": "https://a.nl", "markdown": "keep"}]\n'
    target.write_text(original, encoding="utf-8")
    records = [{"url": "https://b.nl", "markdown": "new"}]

    with patch("stadsdelen.json_io.os.replace", side_effect=OSError("fail")):
        with pytest.raises(JsonSaveError, match="Cannot write JSON file"):
            save_subsidy_array(target, records, backup=False)

    assert target.read_text(encoding="utf-8") == original
    assert not (tmp_path / "subsidies.json.tmp").exists()
