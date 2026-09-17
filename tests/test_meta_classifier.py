import pytest
import pandas as pd
from src.models.meta_classifier import EnsembleMetaClassifier
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

def test_meta_classifier_train_predict():
    clf = EnsembleMetaClassifier()
    
    # Create synthetic features
    # 'Module_A_Score', 'Module_B_Score', 'Module_C_Score'
    X = pd.DataFrame({
        'Module_A_Score': [0.1, 0.9, 0.2, 0.8, 0.1, 0.9, 0.2, 0.8, 0.1, 0.9, 0.2, 0.8],
        'Module_B_Score': [0.0, 0.8, 0.1, 0.9, 0.0, 0.9, 0.1, 0.8, 0.0, 0.9, 0.1, 0.8],
        'Module_C_Score': [0.2, 0.7, 0.1, 0.8, 0.2, 0.8, 0.1, 0.7, 0.2, 0.8, 0.1, 0.7]
    })
    y = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    
    # Train
    clf.train(X, y)
    
    # Predict
    preds = clf.predict(X)
    assert len(preds) == len(y)
    
    # Probabilities
    probs = clf.predict_proba(X)
    assert len(probs) == len(y)
    assert probs.shape[1] == 2
    assert (probs >= 0).all() and (probs <= 1).all()

def test_meta_classifier_save_load(tmp_path):
    clf = EnsembleMetaClassifier()
    
    X = pd.DataFrame({
        'Module_A_Score': [0.1, 0.9, 0.2, 0.8, 0.1, 0.9, 0.2, 0.8, 0.1, 0.9, 0.2, 0.8],
        'Module_B_Score': [0.0, 0.8, 0.1, 0.9, 0.0, 0.8, 0.1, 0.9, 0.0, 0.8, 0.1, 0.9],
        'Module_C_Score': [0.2, 0.7, 0.1, 0.8, 0.2, 0.7, 0.1, 0.8, 0.2, 0.7, 0.1, 0.8]
    })
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
