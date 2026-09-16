# Dual-Use Ethics and Responsible Disclosure Statement

## Context
This repository contains the codebase and data pipelines for an AI Resume Screening Adversarial Robustness detector. To rigorously evaluate the defensive mechanisms (Modules A, B, and C), we explicitly generate adversarial resumes employing techniques such as keyword stuffing, hidden text, and LLM-obfuscated prompt injections.

## Dual-Use Nature of the Dataset
The scripts contained in `src/data_prep/injector.py` and the resulting dataset of poisoned resumes are inherently dual-use. By demonstrating how to effectively defeat applicant tracking systems (ATS) using adversarial ranking attacks, this project inadvertently provides a blueprint for generating such attacks in the real world. 

## Responsible Disclosure
In alignment with academic cybersecurity norms, we adopt the following principles:
1. **Focus on Mitigation**: The generation of adversarial examples is strictly for the purpose of designing, calibrating, and evaluating the multi-signal detection ensemble. 
2. **Transparency in Evaluation**: We publish the methodologies of the attacks to ensure transparency, reproducibility, and rigorous scientific evaluation of the defensive claims.
3. **Restricted Distribution**: While the code to generate the attacks is open-source for peer-review purposes, large-scale pre-generated poisoned datasets are not distributed without verification of academic intent, to limit immediate misuse by bad actors.
4. **No Direct Commercial Exploitation**: This project is an academic prototype and is not intended to be a commercial product sold as an "ATS-beater" service.

By engaging with this repository, researchers and developers agree to use these methodologies solely for improving the robustness and fairness of automated hiring systems, in compliance with regulations such as the EU AI Act (Annex III).
