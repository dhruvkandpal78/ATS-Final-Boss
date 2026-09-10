"""
adaptive_attacker.py — Stealth Mode Evolutionary Loop
=====================================================
Simulates an advanced, adaptive attacker attempting to bypass the defense system.
Uses a greedy evolutionary loop to inject as many keywords as possible into a 
clean resume without triggering the Meta-Classifier (keeping P(Attack) < 0.5).
"""

import sys
import os
import random
import logging
import pandas as pd
from termcolor import colored

# Windows consoles default to cp1252 and choke on the demo's emoji — force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.inference import load_pipeline
from src.evaluation.evaluate import simulate_module_b_proxy
from src.evaluation.curves import plot_attacker_success_curve

logging.basicConfig(level=logging.ERROR)

SKILL_KEYWORDS = ["python", "java", "aws", "docker", "kubernetes", "machine learning", "sql", "react"]

def get_scores(text: str, meta_clf, scaler, mod_a, mod_b, mod_c):
    """Utility to get the P(Attack) score for a given text."""
    b_score = simulate_module_b_proxy(text)
    a_score = mod_a.predict(text)['anomaly_score']
    c_score = mod_c.predict(text)['anomaly_score']
    
    features = pd.DataFrame([{
        "Module_A_Score": a_score,
        "Module_B_Score": b_score,
        "Module_C_Score": c_score
    }])
    
    features_scaled = scaler.transform(features)
    attack_proba = meta_clf.predict_proba(features_scaled)[0][1]
    return attack_proba, a_score, c_score

def mutate(text: str) -> str:
    """Randomly injects a keyword into the text."""
    words = text.split()
    insert_idx = random.randint(0, len(words))
    kw = random.choice(SKILL_KEYWORDS)
    words.insert(insert_idx, kw)
    return " ".join(words)

def run_adaptive_attack():
    print(colored("=" * 70, "red", attrs=["bold"]))
    print(colored("[!] INITIATING STEALTH MODE ADAPTIVE ATTACKER [!]", "red", attrs=["bold"]))
    print(colored("=" * 70, "red", attrs=["bold"]))

    models_dir = os.path.join(os.path.dirname(__file__), "..", "..", "results", "models")
    meta_clf, scaler, mod_a, mod_b, mod_c = load_pipeline(models_dir)

    # Base clean resume — realistic length gives the attacker headroom to inject
    # several keywords before density/coherence anomalies cross the threshold.
    base_resume = (
        "Experienced software engineer with a strong background in backend development "
        "and distributed systems. Led a team of four engineers to deliver a customer "
        "billing platform serving millions of monthly transactions. Designed and "
        "maintained relational databases, built resilient REST APIs, and improved "
        "service reliability through automated testing and observability. Partnered "
        "closely with product managers to translate business requirements into "
        "well-scoped technical roadmaps and mentored junior developers on code quality."
    )
    
    current_text = base_resume
    injected_count = 0
    max_generations = 20
    mutations_per_gen = 5

    print(colored(f"\n[Target]: Inject maximum keywords without exceeding 50% Threat Probability.", "yellow"))
    print(colored(f"Base Resume: '{base_resume}'\n", "white"))

    # History for the success-rate curve (Feature 3).
    history_gen = [0]
    history_proba = [get_scores(base_resume, meta_clf, scaler, mod_a, mod_b, mod_c)[0]]
    history_injected = [0]

    for gen in range(1, max_generations + 1):
        # Generate mutations
        candidates = []
        for _ in range(mutations_per_gen):
            mutated_text = mutate(current_text)
            proba, a_score, c_score = get_scores(mutated_text, meta_clf, scaler, mod_a, mod_b, mod_c)
            candidates.append((mutated_text, proba, a_score, c_score))
            
        # Filter for candidates that stay under detection threshold
        # Moving Target Defense (MTD): Randomize the threshold between 0.40 and 0.50
        dynamic_thresh = random.uniform(0.40, 0.50)
        evasive_candidates = [c for c in candidates if c[1] < dynamic_thresh]
        
        if not evasive_candidates:
            print(colored(f"\n[Generation {gen}] Attacker is STUCK.", "green", attrs=["bold"]))
            print(colored(f"  -> Any further injections trigger the defense shield.", "green"))
            break
            
        # Select the candidate that is closest to the boundary but still safe (greedy)
        # Sort by proba descending, take the highest one that is < 0.5
        best_candidate = sorted(evasive_candidates, key=lambda x: x[1], reverse=True)[0]
        
        current_text = best_candidate[0]
        current_proba = best_candidate[1]
        a_score = best_candidate[2]
        c_score = best_candidate[3]
        injected_count += 1
        
        history_gen.append(gen)
        history_proba.append(current_proba)
        history_injected.append(injected_count)

        print(colored(f"[Gen {gen}] Successful Injection! Total Injected: {injected_count} | Threat Prob: {current_proba*100:.1f}%", "red"))
        print(colored(f"  -> Mod A (Density): {a_score:.3f} | Mod C (Variance): {c_score:.3f}", "yellow"))

    print(colored("\n" + "=" * 70, "cyan", attrs=["bold"]))
    print(colored("ATTACK SUMMARY", "cyan", attrs=["bold"]))
    print(colored(f"Total Keywords Injected Before Detection: {injected_count}", "white"))
    print(colored("Defense Status: " + ("HELD" if injected_count < 10 else "COMPROMISED"), "green" if injected_count < 10 else "red"))
    print(colored("=" * 70, "cyan", attrs=["bold"]))

    # Emit the adaptive-attacker success curve (Feature 3).
    plot_path = os.path.join(os.path.dirname(__file__), "..", "..", "results", "plots",
                             "adaptive_attacker_curve.png")
    try:
        plot_attacker_success_curve(history_gen, history_proba, history_injected, plot_path)
        print(colored(f"\n[+] Attacker trajectory curve saved to results/plots/adaptive_attacker_curve.png", "cyan"))
    except Exception as e:
        print(colored(f"\n[!] Could not render attacker curve: {e}", "yellow"))

if __name__ == "__main__":
    run_adaptive_attack()
