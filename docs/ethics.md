# Dual-Use Ethics and Responsible Disclosure Statement

## Context
This repository contains the codebase and data pipelines for an AI Resume Screening Adversarial Robustness detector. To rigorously evaluate the defensive mechanisms (Modules A, B, and C), we explicitly generate adversarial resumes employing techniques such as keyword stuffing, hidden text, and LLM-obfuscated prompt injections.

## Dual-Use Nature of the Dataset
The scripts contained in `src/data_prep/injector.py` and the resulting dataset of poisoned resumes are inherently dual-use. By demonstrating how to effectively defeat applicant tracking systems (ATS) using adversarial ranking attacks, this project inadvertently provides a blueprint for generating such attacks in the real world. 

## Responsible Disclosure
In alignment with academic cybersecurity norms, we adopt the following principles:
1. **Focus on Mitigation**: The generation of adversarial examples is strictly for the purpose of designing, calibrating, and evaluating the multi-signal detection ensemble. 
2. **Transparency in Evaluation**: We publish the methodologies of the attacks to ensure transparency, reproducibility, and rigorous scientific evaluation of the defensive claims.
3. **Restricted Distribution**: Peer review does not override the repository's mixed ownership terms. New additions have reserved-rights terms; earlier MIT permissions remain preserved. Large pre-generated poisoned datasets are not part of the source-only publication.
4. **No Direct Commercial Exploitation**: This project is an academic prototype and is not intended to be a commercial product sold as an "ATS-beater" service.

The proposed customer pilot is defensive document inspection with human review, subject to customer privacy, legal and licensing approval. Signals must not automatically reject candidates or establish dishonesty. Repository use alone does not demonstrate regulatory compliance.
