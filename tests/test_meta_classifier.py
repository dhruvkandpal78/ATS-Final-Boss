import pytest
import pandas as pd
from src.models.meta_classifier import EnsembleMetaClassifier
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


def sample_features(n=12):
    return pd.DataFrame({
        'Module_A_Score': [0.1, 0.9, 0.2, 0.8, 0.1, 0.9, 0.2, 0.8, 0.1, 0.9, 0.2, 0.8][:n],
        'Module_B_Score': [0.0, 0.8, 0.1, 0.9, 0.0, 0.9, 0.1, 0.8, 0.0, 0.9, 0.1, 0.8][:n],
        'Module_C_Score': [0.2, 0.7, 0.1, 0.8, 0.2, 0.8, 0.1, 0.7, 0.2, 0.8, 0.1, 0.7][:n]
    })

def test_meta_classifier_train_predict():
    clf = EnsembleMetaClassifier()
    X = sample_features()
    y = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    
    # Train
    clf.train(X, y)
    
    # Predict
    preds = clf.predict(X)
    assert len(preds) == len(y)
    
    # Probabilities
    probs = clf.predict_proba(X)
    assert len(probs) == len(y)
    assert probs.shape == (len(y),)
    assert (probs >= 0).all() and (probs <= 1).all()


def test_small_minority_class_uses_adaptive_inner_cv():
    clf = EnsembleMetaClassifier()
    X = sample_features(6)
    y = [0, 1, 0, 1, 0, 0]

    clf.train(X, y)

    assert clf.model.cv == 2
    assert clf.n_jobs == 1
    assert clf.model.n_jobs == 1
    assert clf.model.named_estimators_['rf'].n_jobs == 1
    assert clf.use_xgboost is False


@pytest.mark.parametrize(
    "labels, message",
    [
        ([0, 0, 0, 0, 0, 0], "both classes"),
        ([0, 1, 0, 1, 0, 2], "binary values"),
        ([0, 1, 0], "match the feature row count"),
        ([0, 0, 0, 0, 0, 1], "at least two examples"),
    ],
)
def test_train_rejects_invalid_or_undersupported_labels(labels, message):
    clf = EnsembleMetaClassifier()

    with pytest.raises(ValueError, match=message):
        clf.train(sample_features(6), labels)

def test_meta_classifier_save_load(tmp_path):
    clf = EnsembleMetaClassifier()
    X = sample_features()
    y = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    
    clf.train(X, y)
    
    save_dir = str(tmp_path)
    clf.save_model(save_dir)
    
    assert os.path.exists(os.path.join(save_dir, 'meta_classifier.pkl'))
    assert os.path.exists(os.path.join(save_dir, 'scaler.pkl'))
    
    clf2 = EnsembleMetaClassifier()
    clf2.load_model(save_dir)
    
    preds1 = clf.predict(X)
    preds2 = clf2.predict(X)
    assert (preds1 == preds2).all()
