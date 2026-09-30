import hashlib
import pytest

from src.core.artifacts import POLICY_FILES, verify_policy


def test_policy_freeze_requires_all_files_and_rejects_changed_code(tmp_path):
    hashes = {}
    for name in POLICY_FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"frozen fixture")
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"policy": {"version": "2.0", "code_hashes": hashes}}
    verify_policy(manifest, tmp_path)
    (tmp_path / POLICY_FILES[0]).write_bytes(b"modified fixture")
    with pytest.raises(ValueError, match="changed after candidate freeze"):
        verify_policy(manifest, tmp_path)
    with pytest.raises(ValueError, match="current policy"):
        verify_policy({"policy": {"version": "2.0", "code_hashes": {}}}, tmp_path)


def test_zero_observed_false_positives_does_not_imply_zero_upper_bound():
    import pandas as pd
    from src.evaluation.evaluate_holdout import evaluate_on_dataframe
    class Service:
        def analyze_pdf(self, path):
            return {"status": "complete", "score": 0.1, "decision": "no_signals_detected"}
    data = pd.DataFrame([{"source_id": str(i), "pdf_path": str(i), "is_adversarial": 0} for i in range(100)])
    result = evaluate_on_dataframe(data, Service())
    assert result["False-positive rate"] == 0
    upper = result["false_positive_source_groups"]["one_sided_95pct_upper"]
    assert upper == pytest.approx(1 - 0.05 ** (1 / 100))
    assert 0.029 < upper < 0.030
