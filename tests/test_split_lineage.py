"""Frozen synthetic lineage controls; never loads train/validation/test data."""
import pandas as pd
import pytest
from src.data_prep.splitter import split_by_source


def test_variants_never_cross_splits_and_are_reproducible():
    rows = [{"source_id": f"source-{i}", "resume_id": f"{i}-{variant}",
             "attack_type": "CLEAN" if variant == 0 else "TYPE_A"}
            for i in range(30) for variant in range(3)]
    frame = pd.DataFrame(rows)
    splits = split_by_source(frame)
    groups = [set(part.source_id) for part in splits]
    assert not groups[0] & groups[1] and not groups[0] & groups[2] and not groups[1] & groups[2]
    assert sum(map(len, splits)) == len(frame)
    assert set(pd.concat(splits).resume_id) == set(frame.resume_id)
    for left, right in zip(splits, split_by_source(frame)):
        pd.testing.assert_frame_equal(left, right)


@pytest.mark.parametrize("frame", [pd.DataFrame({"text": ["missing"]}),
    pd.DataFrame({"source_id": [None, "a"]}), pd.DataFrame({"source_id": [" "] * 10})])
def test_missing_lineage_fails_closed(frame):
    with pytest.raises(ValueError):
        split_by_source(frame)
