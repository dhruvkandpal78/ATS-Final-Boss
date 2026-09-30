import argparse
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging
import json
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-7s | %(message)s')
logger = logging.getLogger(__name__)

SPLITS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "splits")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "results")
MODELS_DIR = os.path.join(RESULTS_DIR, "models")

def calc_metrics(y_true, y_pred, y_prob=None):
    if len(y_true) == 0:
        raise ValueError("A holdout evaluation needs at least one labeled row")
    
    metrics = {
        "Precision": precision_score(y_true, y_pred, zero_division=0),
        "Recall": recall_score(y_true, y_pred, zero_division=0),
        "F1": f1_score(y_true, y_pred, zero_division=0)
    }
    negatives = sum(int(value == 0) for value in y_true)
    false_positives = sum(int(actual == 0 and predicted == 1) for actual, predicted in zip(y_true, y_pred))
    metrics["False-positive rate"] = false_positives / negatives if negatives else None
    metrics["N"] = len(y_true)
    metrics["TP"] = sum(int(a == 1 and p == 1) for a, p in zip(y_true, y_pred))
    metrics["FP"] = false_positives
    metrics["TN"] = sum(int(a == 0 and p == 0) for a, p in zip(y_true, y_pred))
    metrics["FN"] = sum(int(a == 1 and p == 0) for a, p in zip(y_true, y_pred))
    if y_prob is not None and len(set(y_true)) > 1:
        metrics["ROC-AUC"] = roc_auc_score(y_true, y_prob)
    else:
        metrics["ROC-AUC"] = None
    return metrics

from src.core.analysis_service import AnalysisService

def evaluate_on_dataframe(df, analysis_service):
    """Evaluate only rows with real PDF evidence through deployed inference.

    Historic text-only CSVs contain synthetic structural proxy values. Passing
    those values to the deployed service would misrepresent PDF forensics, so
    this adapter fails closed until a PDF-ground-truth holdout is supplied.
    """
    required = {'pdf_path', 'is_adversarial'}
    if not required.issubset(df.columns):
        raise ValueError(
            "Holdout evaluation requires pdf_path and is_adversarial columns "
            "with real PDF files; synthetic text proxy scores are not deployable evidence."
        )
    y_true = df['is_adversarial'].values
    y_pred_hybrid = []
    y_prob_hybrid = []
    
    for _, row in df.iterrows():
        res = analysis_service.analyze_pdf(row['pdf_path'])
        if res['status'] != 'complete' or res['score'] is None:
            raise ValueError(
                "Holdout row could not be fully scored through the deployed PDF "
                "service; no aggregate metric was written."
            )
        y_pred_hybrid.append(int(res['decision'] == 'review_recommended'))
        y_prob_hybrid.append(res['score'])
        
    metrics = calc_metrics(y_true, y_pred_hybrid, y_prob_hybrid)
    metrics["family_counts"] = {}
    if "family" in df.columns:
        for family in sorted(df["family"].dropna().unique()):
            mask = df["family"].to_numpy() == family
            actual = y_true[mask]
            predicted = np.asarray(y_pred_hybrid)[mask]
            metrics["family_counts"][str(family)] = {
                "n": int(mask.sum()), "flagged": int(predicted.sum()),
                "known_added_attack": int(actual.sum())}
    if "source_id" in df.columns and df["source_id"].nunique() >= 5:
        groups = df["source_id"].astype(str).to_numpy()
        unique = np.unique(groups)
        rng = np.random.default_rng(42)
        samples = {"F1": [], "False-positive rate": [], "Recall": []}
        predictions = np.asarray(y_pred_hybrid)
        from scipy.stats import beta
        negative_groups = [group for group in unique if np.any((groups == group) & (y_true == 0))]
        false_positive_groups = sum(bool(np.any((groups == group) & (y_true == 0) & (predictions == 1)))
                                    for group in negative_groups)
        n_groups = len(negative_groups)
        if n_groups:
            metrics["false_positive_source_groups"] = {
                "flagged": false_positive_groups, "n": n_groups,
                "one_sided_95pct_upper": (1.0 if false_positive_groups == n_groups else
                    float(beta.ppf(0.95, false_positive_groups + 1, n_groups - false_positive_groups)))}
        for _ in range(1000):
            selected = rng.choice(unique, size=len(unique), replace=True)
            indices = np.concatenate([np.flatnonzero(groups == group) for group in selected])
            subset = calc_metrics(y_true[indices], predictions[indices])
            for name in samples:
                if subset[name] is not None:
                    samples[name].append(subset[name])
        metrics["group_bootstrap_95pct"] = {
            name: [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]
            for name, values in samples.items() if values}
    return metrics

def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate a real-PDF holdout through deployed inference.")
    parser.add_argument("--pdf-holdout", required=True,
                        help="CSV with pdf_path and is_adversarial columns")
    parser.add_argument("--report-path", default=os.path.join(RESULTS_DIR, "reports", "holdout_comparison.md"))
    parser.add_argument("--models-dir", required=True, help="Frozen candidate bundle directory")
    parser.add_argument("--final-evaluation", action="store_true", required=True,
                        help="Explicitly open the final held-out evaluation after freezing")
    args = parser.parse_args(argv)
    if Path(args.report_path).exists():
        raise ValueError("Final evaluation report already exists; refusing to overwrite it")
    csv_path = Path(args.pdf_holdout).resolve()
    from src.core.artifacts import verify_candidate
    from src.evaluation.train_pdf_candidate import source_hash, sha256_file
    manifest = verify_candidate(args.models_dir)
    from src.core.artifacts import verify_policy
    verify_policy(manifest)
    receipt = Path(args.models_dir) / "final_evaluation_receipt.json"
    if receipt.exists():
        raise ValueError("This candidate has already opened its final evaluation; do not tune and rerun")
    # Reserve before opening heldout labels: even a failed run counts as access.
    with receipt.open("x", encoding="utf-8") as handle:
        json.dump({"status": "started", "holdout_manifest_sha256": sha256_file(csv_path)}, handle)
    frame = pd.read_csv(csv_path)
    if 'pdf_path' not in frame.columns:
        raise ValueError("A real-PDF holdout with pdf_path is required; legacy text CSVs are unsupported")
    frame['pdf_path'] = frame['pdf_path'].map(
        lambda value: str((csv_path.parent / str(value)).resolve())
        if not Path(str(value)).is_absolute() else str(value)
    )
    if 'source_id' not in frame or frame['source_id'].isna().any():
        raise ValueError("Final evaluation requires source_id provenance")
    known = manifest['sources']
    used_sources = set(known['train_source_hashes'] + known['validation_source_hashes'])
    used_pdfs = set(known['train_pdf_hashes'] + known['validation_pdf_hashes'])
    if any(source_hash(str(value)) in used_sources for value in frame['source_id']):
        raise ValueError("Holdout source groups overlap development data")
    if any(sha256_file(Path(path)) in used_pdfs for path in frame['pdf_path']):
        raise ValueError("Holdout PDFs overlap development data")
    if frame['is_adversarial'].isna().any() or not frame['is_adversarial'].isin([0, 1]).all():
        raise ValueError("Holdout requires verified binary labels")
    analysis_service = AnalysisService(args.models_dir)
    metrics = evaluate_on_dataframe(frame, analysis_service)
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    auc = "N/A (single class)" if metrics['ROC-AUC'] is None else f"{metrics['ROC-AUC']:.4f}"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("> **Generated by:** `src/evaluation/evaluate_holdout.py`\n\n")
        f.write("# Real-PDF Holdout Evaluation\n\n")
        f.write("Decision metrics use the deployed review policy. ROC-AUC uses the separate uncalibrated experimental model score. All rows required complete PDF evidence. These figures do not validate hiring outcomes.\n\n")
        f.write("| Dataset | Precision | Recall | F1 Score | ROC-AUC |\n")
        f.write("|---------|-----------|--------|----------|---------|\n")
        f.write(f"| {csv_path.name} | {metrics['Precision']:.4f} | {metrics['Recall']:.4f} | {metrics['F1']:.4f} | {auc} |\n")
        f.write(f"\nDecision confusion counts: TP={metrics['TP']}, FP={metrics['FP']}, TN={metrics['TN']}, FN={metrics['FN']}. ")
        fpr = metrics["False-positive rate"]
        f.write("False-positive rate on labeled no-added-attack rows: " +
                (f"{fpr:.4f}" if fpr is not None else "N/A (no negatives)") + ".\n\n")
        for family, counts in metrics.get("family_counts", {}).items():
            f.write(f"- {family}: {counts['flagged']}/{counts['n']} flagged; {counts['known_added_attack']} known added attacks.\n")
        f.write("\nSource-group bootstrap 95% intervals (1,000 draws; small groups may be unstable):\n")
        for name, (lower, upper) in metrics.get("group_bootstrap_95pct", {}).items():
            f.write(f"- {name}: [{lower:.4f}, {upper:.4f}]\n")
        group_fpr = metrics.get("false_positive_source_groups")
        if group_fpr:
            f.write(f"\nSource groups with any no-added-attack false positive: {group_fpr['flagged']}/{group_fpr['n']}. "
                    f"Exact one-sided 95% upper bound on that group-level rate: {group_fpr['one_sided_95pct_upper']:.4f}. "
                    "This assumes independent source groups and does not cover label uncertainty or deployment shift; a zero bootstrap interval does not prove zero risk.\n")
    logger.info("Report saved to %s", report_path)
    receipt.write_text(json.dumps({"status": "complete", "report_sha256": sha256_file(report_path),
                                   "holdout_manifest_sha256": sha256_file(csv_path)}, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
