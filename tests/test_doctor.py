"""Diagnostics must detect unusable calibration without loading models."""
import json

import pytest

from scripts.doctor import check_thresholds


@pytest.mark.parametrize("value", [0, -1, None, True, "0.1", float("nan"), float("inf")])
def test_invalid_thresholds_are_actionable(tmp_path, value):
    path = tmp_path / "thresholds.json"
    path.write_text(json.dumps({"mod_a_threshold": value, "mod_c_variance_threshold": 0.1}))
    checks = check_thresholds(path)
    assert checks[0]["ok"] is False
    assert "validation data" in checks[0]["detail"]
    assert checks[1]["ok"] is True


@pytest.mark.parametrize("content", ["[]", "{", "null"])
def test_malformed_threshold_file(tmp_path, content):
    path = tmp_path / "thresholds.json"
    path.write_text(content)
    assert check_thresholds(path)[0]["ok"] is False


def test_valid_thresholds(tmp_path):
    path = tmp_path / "thresholds.json"
    path.write_text(json.dumps({"mod_a_threshold": 0.1, "mod_c_variance_threshold": 0.02}))
    assert all(check["ok"] for check in check_thresholds(path))
