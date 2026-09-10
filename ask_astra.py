import os
import requests
import json

api_key = os.environ.get("EXPLABS_API_KEY")

prompt = """
You are gpt-6-astra. I am building an adversarial ATS resume detection system for an IEEE paper.
We have 3 modules:
1. Keyword Density (Statistical)
2. PDF Structural Forensics (Hidden text detection)
3. Semantic Coherence (all-MiniLM-L6-v2)

Our current Meta-Classifier is a simple scikit-learn Logistic Regression model. The F1-score is around 0.66.
Please provide the absolute BEST, most advanced Python code to replace our Logistic Regression Meta-Classifier in `src/models/meta_classifier.py` to push the F1-score to the maximum possible (e.g., 0.95+). Consider using XGBoost, Random Forest, or an advanced Ensemble method with hyperparameter tuning (GridSearchCV/Optuna). Provide just the Python code for the new Meta-Classifier class.
"""

url = "https://api.experientiallabs.ai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
data = {
    "model": "gpt-6-astra",
    "messages": [
        {"role": "system", "content": "You are an elite AI researcher."},
        {"role": "user", "content": prompt}
    ]
}

try:
    print("Asking Astra...")
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    print("Astra's Response:\n")
    print(response.json()["choices"][0]["message"]["content"])
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(e.response.text)
