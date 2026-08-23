# AI Resume Screening & Adversarial Robustness Detector

Welcome to the prototype repository for the Capstone Research Project on **Adversarial Robustness in AI Resume Screening**. 

## Project Motivation
Applicant Tracking Systems (ATS) and LLM-based resume screeners are increasingly vulnerable to **adversarial ranking attacks**—techniques like keyword stuffing, hidden text (white font), and prompt injection used by candidates to artificially inflate their ranking. With the rising legal and ethical stakes surrounding automated hiring (e.g., EU AI Act, algorithmic bias litigation), detecting and mitigating these attacks is a critical challenge.

This project implements a **model-agnostic, input-level, multi-signal detector**. Rather than attempting to retrain or fine-tune downstream screening models (which is often expensive or impossible with closed-source ATS), this system acts as a pre-filter, analyzing resumes across statistical, structural, and semantic dimensions to flag adversarial manipulation before the candidate is ranked.

## The Multi-Signal Architecture

The detector ensemble comprises three distinct modules:

1. **Module A (Statistical Anomaly - Keyword Density)**: 
   - Rooted in established spam-filtering methodologies, this module identifies unnatural statistical deviations in skill keyword frequencies relative to total text length.

2. **Module B (Structural Anomaly - PDF Forensics)**:
   - Evaluates the physical and structural properties of PDF documents. It looks past the visible text to detect obfuscation techniques like text-rendering mode 3, Optical Content Groups (OCGs) set to OFF, hidden bounding boxes, and font size manipulations (≤ 1pt).

3. **Module C (Semantic Anomaly - Coherence & Explainability)**:
   - Utilizes off-the-shelf sentence embeddings (`all-MiniLM-L6-v2`) via a sliding-window approach to detect context-less jargon injected into natural sentences, plus a direct-instruction prompt-injection detector for Type-D footer/header overrides. It is paired with **leave-one-sentence-out attribution** (a Shapley-style approximation) to highlight the exact clauses that trigger the anomaly.

4. **The Ensemble Meta-Classifier**:
   - A Logistic Regression layer that takes the heterogeneous scores from the three modules and outputs a calibrated, combined decision on whether a resume constitutes an adversarial attack.

## Evaluation & Rigor
This prototype evaluates the detector against four distinct attack typologies (including LLM-obfuscated prompt injections) utilizing a strict 60/20/20 data split. Furthermore, the pipeline includes:
- **Fairness Auditing**: Analyzing false positive rates across lexical-diversity proxies to check for disparate impact.
- **Adaptive Adversary Testing**: Measuring how the defense degrades against an active attacker attempting synonym-based evasion.
- **Bootstrapped Confidence Intervals**: Ensuring the reported F1/Precision/Recall metrics are robust given the synthetic dataset constraints.

## Interactive Tooling & Live Demos ("Crazy Tier")

Beyond the core research pipeline, three elite-tier demonstrations make the system tangible:

### 1. Interactive XAI Web App — `src/app/server.py` (recommended)
A cinematic, Apple-style **scroll-driven single-page app** served by a
zero-dependency (stdlib-only) Python server that runs the *real* pipeline behind
a JSON API. Scroll through a narrative that introduces the threat and reveals
each detection stage (Modules A → B → C → Meta) with scroll-triggered animation;
at the end, **paste text or drop a `.pdf`/`.txt`** into the upload zone. On
analyze, your document animates *into* the glowing AI core, a scan sequence
ticks through each module, and a fully detailed result unfolds: verdict, animated
threat meter, per-module radial gauges, and sentence-level heat-mapping.

```bash
python src/app/server.py      # then open http://localhost:8000
```

Real `.pdf` uploads run genuine PyMuPDF structural forensics (Module B) server-side.

**Explainability:** Module C's *leave-one-sentence-out* attribution heat-maps the
exact clauses that triggered the flag — a Shapley-style marginal-contribution
approximation grounded in the detector's own decision function. All display units
are embedded once and every ablation reuses the cached vectors, so it stays fast
even on full-page PDFs.

> A simpler Streamlit variant also exists at `src/app/dashboard.py`
> (`streamlit run src/app/dashboard.py`) if you prefer a single-screen dashboard.

### 2. Red Team vs. Blue Team — `src/evaluation/llm_ats_proof.py`
A live proof of the real-world vulnerability. A local HuggingFace `gpt2` model
plays an *unprotected* HR ATS: fed a prompt-injection resume, it gets hijacked.
The same resume is then routed through the Defense Shield, which intercepts the
attack **before** it ever reaches the LLM. No API key required.

```bash
python src/evaluation/llm_ats_proof.py
```

### 3. Stealth-Mode Adaptive Attacker — `src/models/adaptive_attacker.py`
An evolutionary loop that plays the adversary: it greedily mutates a clean resume,
injecting as many keywords as possible while staying under the meta-classifier's
0.5 threshold. It plots its own trajectory (`results/plots/adaptive_attacker_curve.png`)
showing evasion probability climbing toward the boundary before the defense holds.

```bash
python src/models/adaptive_attacker.py
```

## Limitations & Scope
This project relies on a synthetic dataset (informed by real-world prompt injection studies) and uses open-source baseline comparisons, as commercial ATS algorithms are proprietary. It is designed to produce a rigorous analytical pipeline for a research paper. The interactive dashboard above is a demonstration/XAI aid, not a production SaaS deployment.
