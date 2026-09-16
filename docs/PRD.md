# Project Requirements Document (PRD)

## Project Name
AI Resume Screening and Skill Matching System - Prototype (Adversarial Robustness Focus)

## 1. Project Overview
This project is a 6-week compressed prototype of an AI Resume Screening system. Its primary goal is to evaluate **adversarial robustness against keyword stuffing** in resumes. Unlike traditional parsers, this system is designed to detect when candidates artificially inject keywords (e.g., hidden text, prompt injection, and LLM-obfuscated rewrites) to bypass automated screening systems. 

The core novelty of this system lies in its framing: it acts as a **model-agnostic, input-level, multi-signal detector** evaluated under both static and adaptive attacks, and audited for fairness, serving as a complement to model-level defenses (such as FIDS, which require retraining the screening LLM itself).

## 2. Target Users
- **HR Professionals & Recruiters**: To act as an input-level pre-filter to catch candidates who "cheat" ATS ranking algorithms through keyword stuffing and prompt injection.
- **Academic Researchers**: To study adversarial ranking attacks on NLP-based screening systems, analyze fairness (disparate impact) in algorithmic hiring (aligned with the **EU AI Act Annex III (Articles 13 & 14)** and ongoing litigation like Mobley v. Workday), and evaluate mitigation strategies against adaptive adversaries.

## 3. Core Objectives
- Identify and flag adversarially altered resumes treated as **adversarial ranking attacks**.
- Evaluate 4 attack types (Static Types A, B, C, and LLM-obfuscated Type D, strictly including **direct-instruction prompt injections** such as system overrides injected into footers/headers).
- Ensure a strict 60/20/20 data split, guaranteeing no data leakage during threshold calibration.
- Generate a comprehensive results table and evaluation curves (Precision/Recall, ROC-AUC) demonstrating the effectiveness of the multi-signal approach.
- Audit the system for fairness to evaluate potential disparate impact on diverse applicant cohorts using the **EEOC 80% (Four-Fifths) Rule**.

## 4. Features & Requirements

### 4.1 Data Processing & Synthetic Generation
- **Dataset**: 400-500 clean resumes, 150-200 adversarially stuffed resumes.
- **Dual-Use Ethics**: The synthetic dataset demonstrates how to defeat resume screening and thus poses a dual-use risk. It will be explicitly documented with responsible disclosure norms.

### 4.2 Module A: Keyword Density Detector (Statistical Anomaly)
- **Purpose**: Detect anomalous frequencies of skill keywords based on established spam-filtering principles.
- **Thresholding**: Percentile-based (e.g., 95th percentile on validation set) to flag statistical deviations from baseline means.

### 4.3 Module B: PDF Hidden-Text Forensics (Structural Anomaly)
- **Purpose**: Identify keywords hidden using structural styling tricks within the PDF layer.
- **Mechanism**: Checks for physical attributes like **font size ≤ 1pt, zero-sized bounding boxes, negative/out-of-bounds page coordinates, explicit PDF-level obfuscations like Optional Content Groups (OCGs) with visibility OFF, and text-rendering mode 3 (invisible text)**.
- **Implementation**: Uses deep `PyMuPDF` forensics for structural validation.

### 4.4 Module C: Semantic Coherence Scorer (Semantic Anomaly)
- **Purpose**: Detect context-less keywords, LLM-obfuscated injections, and semantic blurring.
- **Mechanism**: Uses `all-MiniLM-L6-v2` via a sliding-window check to score internal flow variance, specifically handling **semantic blurring** from LLM-rewritten resume snippets. 
- **Explainability**: Utilizes SHAP-based outputs to provide word-level explanations.

### 4.5 Combined Scoring Layer (Ensemble Detection)
- **Purpose**: A model-agnostic meta-classifier to combine heterogeneous anomaly scores.
- **Mechanism**: Logistic Regression model trained *only* on the validation split's module scores.

### 4.6 Evaluation & Auditing
- **Fairness Audit**: Subgroup slicing using lexical-diversity proxies to calculate False Positive Rates, integrating the **EEOC 80% Rule** to ensure compliance with EU AI Act standards.
- **Adaptive Adversary Evaluation**: Plots an **Adaptive Adversary Test degradation curve** (detection accuracy drop vs. iterative word-substitution percentages).
- **Visualization**: Generates **ROC-AUC/PR comparative curves** across individual modules vs. the meta-classifier.

## 5. Explicit Limitations & Out of Scope
- **No Commercial ATS Baseline**: Due to the proprietary nature of commercial ATS and LLM-screening products, the baseline is restricted to open-source implementations.
- **Synthetic Data Reliability**: While informed by large-scale empirical findings, the dataset is synthetic.
- **No Web/API UI**: The deliverable is a rigorous research pipeline and evaluation table, not a commercial SaaS application.
