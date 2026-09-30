import hashlib
import json

import pytest

from src.core.artifacts import FILES, FEATURE_ORDER, verify_candidate


def test_candidate_rejects_tampering_before_loading_weights(tmp_path):
    hashes = {}
    for name in FILES:
        (tmp_path / name).write_bytes(b"synthetic bytes")
        hashes[name] = hashlib.sha256(b"synthetic bytes").hexdigest()
    manifest = {"schema_version": "1.0", "kind": "real_pdf_candidate", "input_mode": "pdf",
                "feature_order": FEATURE_ORDER, "artifacts": hashes}
    (tmp_path / "candidate_manifest.json").write_text(json.dumps(manifest))
    assert verify_candidate(tmp_path) == manifest
    (tmp_path / "thresholds.json").write_text("{}")
    with pytest.raises(ValueError, match="integrity"):
        verify_candidate(tmp_path)
