import os
import sys
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.modules.module_b import PDFForensicsDetector

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "results")
PDF_DIR = os.path.join(OUTPUT_DIR, "standalone_pdfs")

def create_pdf(filename, text, hidden_text=None):
    os.makedirs(PDF_DIR, exist_ok=True)
    filepath = os.path.join(PDF_DIR, filename)
    c = canvas.Canvas(filepath, pagesize=letter)
    
    # Write normal text
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0, 0, 0) # Black
    y = 750
    # Just draw a few lines so it's not empty
    for line in text.split()[:50]:
        c.drawString(50, y, line)
        y -= 15
        if y < 50:
            break
            
    # Write hidden text
    if hidden_text:
        # Simulate tiny white font
        c.setFont("Helvetica", 1)
        c.setFillColorRGB(1, 1, 1) # White
        y = 30
        for line in hidden_text.split()[:20]:
            c.drawString(50, y, line)
            y -= 2
            
    c.save()
    return filepath

def run_standalone_eval():
    print("Running standalone Module B evaluation on real PDFs...")
    # Load dataset
    df_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "full_dataset.csv")
    if not os.path.exists(df_path):
        print("Data not found. Please ensure data is present.")
        return
        
    df = pd.read_csv(df_path)
    
    # Grab 50 clean
    clean_df = df[df["attack_type"] == "CLEAN"].sample(50, random_state=42)
    # Grab 50 Type B
    typeb_df = df[df["attack_type"] == "TYPE_B"].sample(50, random_state=42)
    
    detector = PDFForensicsDetector()
    y_true = []
    y_pred = []
    
    print("Generating and analyzing Clean PDFs...")
    for i, row in clean_df.iterrows():
        filepath = create_pdf(f"clean_{i}.pdf", row['text'])
        res = detector.analyze_pdf(filepath)
        y_true.append(0)
        y_pred.append(1 if res['anomaly_score'] > 0.5 else 0)
        
    print("Generating and analyzing Type-B PDFs (Hidden Text)...")
    for i, row in typeb_df.iterrows():
        # Extracted injected content from text if possible, or just generate dummy
        hidden = "python java javascript react sql aws kubernetes blockchain smart contracts"
        filepath = create_pdf(f"typeb_{i}.pdf", row['text'], hidden_text=hidden)
        res = detector.analyze_pdf(filepath)
        y_true.append(1)
        y_pred.append(1 if res['anomaly_score'] > 0.5 else 0)
        
    # Calculate metrics
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    print(f"Module B Standalone Precision: {precision:.4f}")
    print(f"Module B Standalone Recall: {recall:.4f}")
    print(f"Module B Standalone F1: {f1:.4f}")
    
    # Append to report
    report_path = os.path.join(OUTPUT_DIR, "evaluation_report.md")
    if os.path.exists(report_path):
        with open(report_path, "a") as f:
            f.write("\n## 5. Standalone Module B Evaluation (Real PDFs)\n")
            f.write("Because the main evaluation uses a CSV dataset, Module B's main metrics are based on a synthetic text marker proxy. ")
            f.write("To validate its true forensic capabilities, a standalone evaluation was run on 100 generated PDFs (50 Clean, 50 with hidden text using 1pt white font).\n\n")
            f.write(f"- **Precision**: `{precision:.4f}`\n")
            f.write(f"- **Recall**: `{recall:.4f}`\n")
            f.write(f"- **F1-Score**: `{f1:.4f}`\n")
            f.write(f"- **False Positives**: `{fp} / 50`\n")
            f.write(f"- **False Negatives**: `{fn} / 50`\n")
    
if __name__ == "__main__":
    run_standalone_eval()
