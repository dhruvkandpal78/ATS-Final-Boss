"""
curves.py — Evaluation Curves & Visualizations
==============================================
Generates ROC-AUC and Precision-Recall comparative curves across individual 
modules versus the meta-classifier. Also plots the Adaptive Adversary Test 
degradation curve.
"""

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, auc, precision_recall_curve, average_precision_score
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Aesthetic configuration matching design.md
plt.style.use('dark_background')
COLORS = {
    'Module A': '#F59E0B', # Amber
    'Module B': '#10B981', # Emerald
    'Module C': '#8B5CF6', # Purple
    'Meta-Classifier': '#3B82F6', # Blue
    'Baseline': '#EF4444' # Red
}

def plot_roc_curves(y_true, proba_dict: dict, output_path: str):
    """
    Plots comparative ROC curves for multiple models/modules.
    :param proba_dict: Dictionary mapping model name to predicted probabilities.
    """
    plt.figure(figsize=(10, 8))
    
    for name, y_proba in proba_dict.items():
        fpr, tpr, _ = roc_curve(y_true, y_proba)
        roc_auc = auc(fpr, tpr)
        color = COLORS.get(name, '#FFFFFF')
        
        plt.plot(fpr, tpr, color=color, lw=2, label=f'{name} (AUC = {roc_auc:.3f})')

    plt.plot([0, 1], [0, 1], color='#94A3B8', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate', fontsize=12)
    plt.ylabel('True Positive Rate', fontsize=12)
    plt.title('Receiver Operating Characteristic (ROC) - Adversarial Detection', fontsize=14, pad=15)
    plt.legend(loc="lower right", fontsize=11)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#0F172A')
    plt.close()
    logger.info(f"Saved ROC curve to {output_path}")

def plot_degradation_curve(substitution_percentages: list, accuracy_drops: list, output_path: str):
    """
    Plots the Adaptive Adversary Test degradation curve.
    """
    plt.figure(figsize=(10, 6))
    
    plt.plot(substitution_percentages, accuracy_drops, color=COLORS['Meta-Classifier'], marker='o', lw=2, markersize=8)
    
    plt.xlim([0.0, max(substitution_percentages) + 10])
    plt.ylim([0.0, 1.0])
    plt.xlabel('Word Substitution Budget (%)', fontsize=12)
    plt.ylabel('Detection Accuracy (F1)', fontsize=12)
    plt.title('Adaptive Adversary Degradation (Meta-Classifier)', fontsize=14, pad=15)
    plt.grid(True, linestyle=':', alpha=0.3)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#0F172A')
    plt.close()
    logger.info(f"Saved Degradation curve to {output_path}")

def plot_attacker_success_curve(generations: list, threat_probs: list, injected_counts: list,
                                output_path: str, threshold: float = 0.5):
    """
    Plots the Stealth-Mode Adaptive Attacker's trajectory over generations
    (Feature 3). Shows how the attacker's evasion probability climbs toward the
    Meta-Classifier's 0.5 decision boundary as it stuffs more keywords, and where
    the defense finally holds the line.

    :param generations:    x-axis, the generation index of each successful injection.
    :param threat_probs:   P(Attack) achieved by the attacker at each generation.
    :param injected_counts: cumulative keywords successfully injected per generation.
    """
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Threat probability trajectory (left axis) vs. the defense threshold.
    ax1.plot(generations, threat_probs, color=COLORS['Baseline'], marker='o',
             lw=2.5, markersize=7, label='Attacker P(evasion)')
    ax1.axhline(y=threshold, color='#94A3B8', lw=2, linestyle='--',
                label=f'Defense threshold ({threshold:.2f})')
    ax1.fill_between(generations, threat_probs, threshold,
                     where=[p >= threshold for p in threat_probs],
                     color=COLORS['Baseline'], alpha=0.15, interpolate=True)

    ax1.set_xlabel('Generation', fontsize=12)
    ax1.set_ylabel('Threat Probability P(Attack)', fontsize=12, color=COLORS['Baseline'])
    ax1.set_ylim([0.0, 1.0])
    ax1.tick_params(axis='y', labelcolor=COLORS['Baseline'])

    # Cumulative keywords injected (right axis).
    ax2 = ax1.twinx()
    ax2.plot(generations, injected_counts, color=COLORS['Module C'], marker='s',
             lw=2, markersize=6, linestyle=':', label='Keywords injected')
    ax2.set_ylabel('Cumulative Keywords Injected', fontsize=12, color=COLORS['Module C'])
    ax2.tick_params(axis='y', labelcolor=COLORS['Module C'])

    # Merge legends from both axes.
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)

    plt.title('Stealth-Mode Adaptive Attacker vs. Defense Shield', fontsize=14, pad=15)
    ax1.grid(True, linestyle=':', alpha=0.3)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#0F172A')
    plt.close()
    logger.info(f"Saved Adaptive Attacker success curve to {output_path}")

if __name__ == "__main__":
    pass
