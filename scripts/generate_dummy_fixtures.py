import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.preprocessing import StandardScaler
import os

os.makedirs('tests/fixtures', exist_ok=True)

# Dummy scaler
scaler = StandardScaler()
scaler.fit(pd.DataFrame({'Module_A_Score': [0, 1], 'Module_B_Score': [0, 1], 'Module_C_Score': [0, 1]}))
joblib.dump(scaler, 'tests/fixtures/dummy_scaler.pkl')

# Dummy classifier
clf = DummyClassifier(strategy='constant', constant=1)
clf.fit([[0, 0, 0], [1, 1, 1]], [0, 1])
joblib.dump(clf, 'tests/fixtures/dummy_meta_classifier.pkl')
