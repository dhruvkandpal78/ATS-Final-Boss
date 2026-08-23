# System Architecture & Technical Stack

## 1. Architectural Philosophy
The system is designed as a **model-agnostic, input-level pre-filter**. Unlike model-level defenses that require retraining or fine-tuning the downstream ATS ranking models (such as FIDS), this architecture sits in front of the screening pipeline. It assesses resumes for adversarial ranking attacks (keyword stuffing, hidden text, prompt injection) before they enter the candidate evaluation phase.

## 2. Application Flow

`[Raw Resumes (PDFs/Text)]` 
       ↓
`[Data Prep & Adversarial Injection]` -> Generates Types A, B, C (Static) and Type D (LLM-Obfuscated + Header/Footer Prompt Overrides).
       ↓
`[Strict Splitting Layer]` -> Train (60) / Val (20) / Test (20) 
       ↓
`[Feature Extraction: The Multi-Signal Detector]`
       ├── Module A (Statistical): Keyword Density Scorer
       ├── Module B (Structural): Deep PDF Forensics (PyMuPDF - checking Render Mode 3, OCGs OFF, zero-size BBox, out-of-bounds coords)
       └── Module C (Semantic): Coherence Scorer handling semantic blurring (MiniLM) + SHAP Explainer
       ↓
`[Ensemble Combined Scoring]` -> Logistic Regression Meta-Classifier (calibrated on Val set only)
       ↓
`[Evaluation Engine]` -> Metrics Calculation, Curves Generation, Fairness Auditing

## 3. Tech Stack
- **Language**: Python 3.10+
- **PDF Forensics**: `PyMuPDF` (fitz) and `pdfplumber` (for byte-level structural extraction, catching zero-sized bounding boxes and rendering modes).
- **NLP & Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`) for off-the-shelf semantic encoding.
- **Explainability**: `shap` for word-level attribution of semantic anomalies.
- **Machine Learning**: `scikit-learn` (Logistic Regression for the meta-classifier, evaluation metrics).
- **Data Manipulation**: `pandas`, `numpy`
- **Visualization**: `matplotlib`, `seaborn` (for ROC-AUC, PR Curves, and Degradation plotting)

## 4. Folder & File Structure

```text
/
├── data/
│   ├── raw/                 # Original clean Kaggle resumes
│   ├── processed/           # Cleaned texts, simulated stuffed texts
│   └── pdf_samples/         # 30-50 real PDFs for Module B structural validation
├── src/
│   ├── data_prep/
│   │   ├── cleaner.py       # Cleans Kaggle dataset
│   │   ├── injector.py      # Injects attacks (Including prompt-overrides in headers/footers)
│   │   └── splitter.py      # Strict 60/20/20 train/val/test splitting
│   ├── modules/
│   │   ├── module_a.py      # Keyword density calculation (Statistical)
│   │   ├── module_b.py      # PDF deep structural forensics (PyMuPDF)
│   │   └── module_c.py      # MiniLM sliding-window for semantic blurring + SHAP
│   ├── models/
│   │   └── meta_classifier.py # Logistic Regression combined scoring
│   └── evaluation/
│       ├── metrics.py       # Base metric calculations
│       ├── fairness.py      # EEOC 80% Rule Disparate impact auditing
│       └── curves.py        # ROC-AUC, PR, and Adaptive Degradation plots
├── notebooks/               # Jupyter notebooks for EDA and SHAP visualization
├── requirements.txt
├── README.md
├── rules.md
├── phases.md
└── PRD.md
```
