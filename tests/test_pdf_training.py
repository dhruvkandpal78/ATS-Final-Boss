import pandas as pd
import pytest

from scripts.generate_pdf_smoke import generate
from src.evaluation.train_pdf_candidate import _read_split_manifest, validate_train_validation


def test_manifests_reject_leakage_and_unreviewed_labels(tmp_path):
    generate(tmp_path)
    train = _read_split_manifest(tmp_path / "train.csv")
    validation = _read_split_manifest(tmp_path / "validation.csv")
    validate_train_validation(train, validation)
    validation.loc[0, "source_id"] = train.loc[0, "source_id"]
    with pytest.raises(ValueError, match="overlap"):
        validate_train_validation(train, validation)
    frame = pd.read_csv(tmp_path / "train.csv")
    frame.loc[0, "is_adversarial"] = None
    frame.to_csv(tmp_path / "unreviewed.csv", index=False)
    with pytest.raises(ValueError, match="missing"):
        _read_split_manifest(tmp_path / "unreviewed.csv")
