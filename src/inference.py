"""
inference.py — Real-Time Resume Screening Demo
==============================================
Provides a command-line interface (CLI) to run a single resume (text or PDF)
through the entire detection pipeline (Modules A, B, C + Meta-Classifier).
Perfect for live Capstone demonstrations.
"""

import sys
import os
import argparse
import pickle
import logging
from termcolor import colored

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.modules.module_a import KeywordDensityDetector
from src.modules.module_b import PDFForensicsDetector
from src.modules.module_c import SemanticCoherenceScorer
from src.evaluation.evaluate import simulate_module_b_proxy

logging.basicConfig(level=logging.ERROR) # Suppress debug logs for clean CLI output

def print_banner():
    print(colored("=" * 60, "cyan", attrs=["bold"]))
    print(colored("  AI RESUME SCREENING & ADVERSARIAL DETECTION SYSTEM  ", "cyan", attrs=["bold"]))
    print(colored("=" * 60, "cyan", attrs=["bold"]))

def load_pipeline(models_dir):
    try:
        with open(os.path.join(models_dir, "meta_classifier.pkl"), "rb") as f:
            meta_clf = pickle.load(f)
        with open(os.path.join(models_dir, "scaler.pkl"), "rb") as f:
            scaler = pickle.load(f)
    except FileNotFoundError:
        print(colored("[ERROR] Trained models not found. Run evaluate.py first.", "red"))
        sys.exit(1)
        
    import json
    config_dir = os.path.join(os.path.dirname(__file__), "..", "configs")
    try:
        with open(os.path.join(config_dir, "thresholds.json"), "r") as f:
            thresholds = json.load(f)
        with open(os.path.join(config_dir, "model_config.json"), "r") as f:
            model_cfg = json.load(f)
    except FileNotFoundError:
        print(colored("[ERROR] Config files missing. Run evaluate.py to generate them.", "red"))
        sys.exit(1)

    mod_a = KeywordDensityDetector()
    mod_a.threshold = thresholds.get("mod_a_threshold", 0.08)
    
    mod_c = SemanticCoherenceScorer(model_name=model_cfg.get("embedding_model", "all-MiniLM-L6-v2"), window_size=2)
    mod_c.variance_threshold = thresholds.get("mod_c_variance_threshold", 0.015)
    
    mod_b = PDFForensicsDetector()
    
    return meta_clf, scaler, mod_a, mod_b, mod_c

def run_inference(file_path: str):
    print_banner()
    print(colored(f"\nAnalyzing File: {os.path.basename(file_path)}", "yellow"))
    print("-" * 60)
    
    models_dir = os.path.join(os.path.dirname(__file__), "..", "results", "models")
    meta_clf, scaler, mod_a, mod_b, mod_c = load_pipeline(models_dir)
    
    is_pdf = file_path.lower().endswith(".pdf")
    text_content = ""
    
    # 1. Module B (Structural Forensics)
    print(colored("[Module B] Executing Deep Structural Forensics...", "blue"))
    if is_pdf:
        b_res = mod_b.analyze_pdf(file_path)
        b_score = b_res.get('anomaly_score', 0.0)
        
        # Actually extract text from the PDF
        import fitz
        try:
            doc = fitz.open(file_path)
            text_content = " ".join(page.get_text() for page in doc)
            doc.close()
        except Exception as e:
            print(colored(f"[ERROR] Failed to extract text from PDF: {e}", "red"))
            text_content = ""
            
        print(colored("  -> PDF structural analysis complete.", "green"))
    else:
        # Load text file
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()
        b_score = simulate_module_b_proxy(text_content)
        print(colored("  -> Text file detected. Running CSV structural simulation...", "green"))
        
    print(f"  -> Structural Anomaly Score: {b_score:.4f}")

    if not text_content.strip():
        print(colored("[WARNING] No text extracted. Using empty string.", "yellow"))
        text_content = " "
        
    # 2. Module A (Keyword Density)
    print(colored("\n[Module A] Executing Statistical Density Analysis...", "blue"))
    a_res = mod_a.predict(text_content)
    a_score = a_res['anomaly_score']
    print(f"  -> Keyword Density Anomaly Score: {a_score:.4f}")
    
    # 3. Module C (Semantic Coherence)
    print(colored("\n[Module C] Executing Semantic Coherence Scoring (MiniLM-L6-v2)...", "blue"))
    c_res = mod_c.predict(text_content)
    c_score = c_res['anomaly_score']
    print(f"  -> Semantic Variance Score: {c_score:.4f}")
    
    # 4. Meta-Classifier
    print(colored("\n[Meta-Classifier] Aggregating multi-modal signals...", "blue"))
    import pandas as pd
    features = pd.DataFrame([{
        "Module_A_Score": a_score,
        "Module_B_Score": b_score,
        "Module_C_Score": c_score
    }])
    
    is_attack = bool(meta_clf.predict(features)[0])
    attack_proba = float(meta_clf.predict_proba(features)[0][1])
    
    print("-" * 60)
    if is_attack:
        print(colored(f"[!] ALERT: ADVERSARIAL ATTACK DETECTED [!]", "red", attrs=["bold"]))
        print(colored(f"Confidence: {attack_proba * 100:.2f}%", "red"))
        print(colored("Reason: This resume exhibits synthetic keyword stuffing or prompt injection traits.", "red"))
    else:
        print(colored(f"[OK] PASSED: LEGITIMATE RESUME [OK]", "green", attrs=["bold"]))
        print(colored(f"Adversarial Probability: {attack_proba * 100:.2f}%", "green"))
        
    print(colored("=" * 60, "cyan", attrs=["bold"]))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run adversarial detection on a single resume.")
    parser.add_argument("file", help="Path to the resume file (.txt or .pdf) to analyze.")
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(colored(f"Error: File '{args.file}' not found.", "red"))
        sys.exit(1)
        
    run_inference(args.file)
