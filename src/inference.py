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
    from src.core.analysis_service import AnalysisService
    analysis_service = AnalysisService(models_dir)
    
    is_pdf = file_path.lower().endswith(".pdf")
    text_content = ""
    b_score = 0.0
    
    if is_pdf:
        print(colored("\n[Module B] Executing PDF Structural Forensics...", "blue"))
        b_res = analysis_service.mod_b.analyze_pdf(file_path)
        b_score = b_res['anomaly_score']
        print(f"  -> Structural Anomaly Score: {b_score:.4f}")
        
        print(colored("  -> Extracting visible text layers...", "blue"))
        try:
            import fitz
            doc = fitz.open(file_path)
            text_content = "\n".join([page.get_text() for page in doc])
            doc.close()
        except Exception as e:
            print(colored(f"  -> [WARNING] Text extraction failed: {e}", "yellow"))
    else:
        print(colored("\n[Module B] Skipped (Input is plain text).", "blue"))
        with open(file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
            
    if not text_content.strip():
        print(colored("[WARNING] No text extracted. Using empty string.", "yellow"))
        text_content = " "
        
    print(colored("\n[Module A & C] Executing Text Analysis...", "blue"))
    res = analysis_service.analyze_text(text_content, b_score)
    
    print(f"  -> Keyword Density Anomaly Score: {res['features']['Module_A_Score']:.4f}")
    print(f"  -> Semantic Variance Score: {res['features']['Module_C_Score']:.4f}")
    
    # 4. Meta-Classifier
    print(colored("\n[Meta-Classifier] Aggregating multi-modal signals...", "blue"))
    is_attack = res['policy_decision']
    attack_proba = res['policy_proba']
    
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
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of human-readable text.")
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(colored(f"Error: File '{args.file}' not found.", "red"), file=sys.stderr)
        sys.exit(1)
        
    if args.json:
        # Load directly
        import json
        models_dir = os.path.join(os.path.dirname(__file__), "..", "results", "models")
        from src.core.analysis_service import AnalysisService
        analysis_service = AnalysisService(models_dir)
        
        is_pdf = args.file.lower().endswith(".pdf")
        text_content = ""
        b_score = 0.0
        pdf_details = None
        
        if is_pdf:
            b_res = analysis_service.mod_b.analyze_pdf(args.file)
            b_score = b_res['anomaly_score']
            pdf_details = b_res.get('details', {})
            try:
                import fitz
                doc = fitz.open(args.file)
                text_content = "\n".join([page.get_text() for page in doc])
                doc.close()
            except Exception:
                text_content = ""
        else:
            with open(args.file, 'r', encoding='utf-8') as f:
                text_content = f.read()
                
        if not text_content.strip():
            text_content = " "
            
        res = analysis_service.analyze_text(text_content, b_score)
        
        from src.core.schemas import AnalysisResult, ModuleAData, ModuleBData, ModuleCData
        from datetime import datetime
        
        result = AnalysisResult(
            timestamp=datetime.utcnow().isoformat(),
            input_mode="pdf" if is_pdf else "text",
            features={
                "Module_A_Score": round(res['features']['Module_A_Score'], 4),
                "Module_B_Score": round(b_score, 4),
                "Module_C_Score": round(res['features']['Module_C_Score'], 4),
            },
            model_decision=res['model_decision'],
            model_proba=round(res['model_proba'], 4),
            policy_decision=res['policy_decision'],
            policy_proba=round(res['policy_proba'], 4),
            module_a=ModuleAData(
                score=round(res['features']['Module_A_Score'], 4),
                density=round(res['module_a']["density"], 4),
                is_flagged=bool(res['module_a']["is_flagged"])
            ),
            module_b=ModuleBData(
                score=round(b_score, 4),
                is_flagged=b_score >= 0.5,
                details=pdf_details or {}
            ),
            module_c=ModuleCData(
                score=round(res['features']['Module_C_Score'], 4),
                variance=round(res['module_c']["variance"], 4),
                injection_cues=int(res['module_c'].get("injection_cues", 0)),
                is_flagged=bool(res['module_c']["is_flagged"]),
                sentences=[] # sentences omitted for brevity in CLI
            )
        )
        print(json.dumps(result.model_dump(), indent=2))
    else:
        run_inference(args.file)
