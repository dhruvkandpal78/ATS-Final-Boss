import os
import pandas as pd
from typing import Dict, Any
from src.inference import load_pipeline

class AnalysisService:
    def __init__(self, models_dir: str = None, mod_a=None, mod_b=None, mod_c=None, meta_clf=None, scaler=None):
        if models_dir is not None:
            self.meta_clf, self.scaler, self.mod_a, self.mod_b, self.mod_c = load_pipeline(models_dir)
        else:
            self.mod_a = mod_a
            self.mod_b = mod_b
            self.mod_c = mod_c
            self.meta_clf = meta_clf
            self.scaler = scaler

    def analyze_text(self, text: str, b_score: float = 0.0) -> Dict[str, Any]:
        # Feature extraction
        a_res = self.mod_a.predict(text)
        c_res = self.mod_c.predict(text)
        
        a_score = a_res['anomaly_score']
        c_score = c_res['anomaly_score']
        
        features = pd.DataFrame([{
            'Module_A_Score': a_score,
            'Module_B_Score': b_score,
            'Module_C_Score': c_score
        }])
        
        is_attack_model = False
        proba_model = 0.0
        
        if self.meta_clf is not None:
            is_attack_model = bool(self.meta_clf.predict(features).item(0))
            proba_model = float(self.meta_clf.predict_proba(features).item(0))
        
        # Policy rules
        is_attack_policy = is_attack_model
        proba_policy = proba_model
        
        if c_res.get('injection_cues', 0) > 0 or b_score >= 0.9:
            is_attack_policy = True
            proba_policy = max(proba_model, 0.95)
            
        return {
            'features': features.iloc[0].to_dict(),
            'model_decision': is_attack_model,
            'model_proba': proba_model,
            'policy_decision': is_attack_policy,
            'policy_proba': proba_policy,
            'module_a': a_res,
            'module_c': c_res,
            'injection_cues': c_res.get('injection_cues', 0)
        }
