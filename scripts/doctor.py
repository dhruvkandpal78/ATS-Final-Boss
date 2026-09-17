import sys
import importlib.util
import os
from pathlib import Path

def check_package(name: str) -> bool:
    if importlib.util.find_spec(name) is None:
        print(f"[FAIL] Missing package: {name}")
        return False
    print(f"[PASS] Found package: {name}")
    return True

def doctor():
    print("=== ATS Final Boss Diagnostic ===")
    
    # Check Python version
    if sys.version_info >= (3, 9):
        print(f"[PASS] Python {sys.version.split()[0]} is compatible.")
    else:
        print(f"[FAIL] Python {sys.version.split()[0]} is too old. Need >= 3.9.")
        
    print("\n--- Core Packages ---")
    core = ["numpy", "pandas", "sklearn", "sentence_transformers", "torch", "fitz", "pdfplumber", "tqdm"]
    all_core = all(check_package(p) for p in core)
    
    print("\n--- Optional Packages ---")
    check_package("xgboost")
    
    print("\n--- Models and Artifacts ---")
    model_dir = Path("results/models")
    if (model_dir / "meta_classifier.pkl").exists() and (model_dir / "scaler.pkl").exists():
        print("[PASS] Local model artifacts found.")
    else:
        print("[WARN] Local model artifacts missing (meta_classifier.pkl / scaler.pkl). Run experiments script if needed.")
        
    print("\nDiagnostic complete.")
    if not all_core:
        sys.exit(1)

if __name__ == '__main__':
    doctor()
