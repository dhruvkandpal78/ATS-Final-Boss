"""
cleaner.py — Phase 1: Data Cleaning Pipeline
=============================================
Cleans the raw Kaggle resume dataset (snehaanbhawal/resume-dataset) into a
publication-grade baseline of ~2,000+ clean resumes for IEEE-level evaluation.

Steps:
    1. Load raw CSV and validate schema.
    2. Strip all HTML tags and entities using BeautifulSoup.
    3. Normalize whitespace, remove non-printable characters.
    4. Drop exact duplicates and near-duplicates.
    5. Filter by word count (min 50, max 5000) to remove broken entries.
    6. Assign unique IDs and compute metadata (word_count, lexical_diversity).
    7. Save the full cleaned dataset — no downsampling.

Output:
    data/processed/cleaned_resumes.csv
        Columns: resume_id, category, clean_text, word_count, unique_word_count,
                 lexical_diversity, char_count
"""

import pandas as pd
import numpy as np
import re
import os
import logging
import hashlib

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("BeautifulSoup is required. Install it: pip install beautifulsoup4")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RAW_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "raw", "resume-dataset", "Resume", "Resume.csv"
)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "cleaned_resumes.csv")

MIN_WORD_COUNT = 50      # Resumes shorter than this are likely parsing errors
MAX_WORD_COUNT = 5000     # Resumes longer than this are outliers
NEAR_DUP_THRESHOLD = 0.95  # Jaccard similarity threshold for near-duplicate detection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def strip_html(raw_html: str) -> str:
    """
    Removes all HTML tags and decodes HTML entities from a raw resume string.
    Uses BeautifulSoup for robust parsing — handles malformed HTML gracefully.
    """
    if not isinstance(raw_html, str):
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ")
    return text


def normalize_text(text: str) -> str:
    """
    Normalizes cleaned text:
      - Strips leading/trailing whitespace.
      - Collapses multiple spaces/newlines into single spaces.
      - Removes non-printable/control characters (keeps standard punctuation).
      - Preserves periods, commas, hyphens (needed for Module C coherence).
    """
    # Remove non-printable characters (keep ASCII 32-126 and common Unicode)
    text = re.sub(r"[^\x20-\x7E\u00C0-\u024F]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_lexical_diversity(text: str) -> float:
    """
    Computes Type-Token Ratio (TTR) as a lexical diversity proxy.
    TTR = unique_words / total_words.
    This metric is used later in the fairness audit (EEOC 80% Rule)
    to create subgroup proxies.
    """
    words = text.lower().split()
    if len(words) == 0:
        return 0.0
    unique = set(words)
    return len(unique) / len(words)


def text_fingerprint(text: str) -> str:
    """
    Generates an MD5 fingerprint of the normalized lowercase text
    for near-duplicate detection.
    """
    normalized = re.sub(r"\s+", "", text.lower())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Jaccard similarity between two word sets."""
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Main Cleaning Pipeline
# ---------------------------------------------------------------------------
def clean_dataset():
    """
    Executes the full cleaning pipeline and saves the IEEE-grade baseline dataset.
    """
    # ------------------------------------------------------------------
    # Step 1: Load raw CSV
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("PHASE 1: DATA CLEANING PIPELINE")
    logger.info("=" * 60)

    raw_path = os.path.normpath(RAW_CSV_PATH)
    logger.info(f"Loading raw dataset from: {raw_path}")

    df = pd.read_csv(raw_path)
    logger.info(f"Raw dataset loaded: {df.shape[0]} rows, {df.shape[1]} columns")
    logger.info(f"Columns: {df.columns.tolist()}")

    # Identify the resume text column (dataset uses 'Resume_str' or similar)
    text_col = None
    for candidate in ["Resume_str", "resume_str", "Resume", "resume", "Text", "text"]:
        if candidate in df.columns:
            text_col = candidate
            break

    if text_col is None:
        raise ValueError(
            f"Could not identify the resume text column. Available columns: {df.columns.tolist()}"
        )

    # Identify the category column
    cat_col = None
    for candidate in ["Category", "category", "Label", "label"]:
        if candidate in df.columns:
            cat_col = candidate
            break

    logger.info(f"Resume text column: '{text_col}' | Category column: '{cat_col}'")

    # ------------------------------------------------------------------
    # Step 2: Drop rows with missing text
    # ------------------------------------------------------------------
    initial_count = len(df)
    df = df.dropna(subset=[text_col])
    dropped_null = initial_count - len(df)
    logger.info(f"Dropped {dropped_null} rows with null/empty resume text.")

    # ------------------------------------------------------------------
    # Step 3: Strip HTML and normalize
    # ------------------------------------------------------------------
    logger.info("Stripping HTML tags and normalizing text...")
    df["clean_text"] = df[text_col].apply(strip_html).apply(normalize_text)

    # ------------------------------------------------------------------
    # Step 4: Compute word counts and filter by length
    # ------------------------------------------------------------------
    df["word_count"] = df["clean_text"].apply(lambda x: len(x.split()))

    before_filter = len(df)
    df = df[(df["word_count"] >= MIN_WORD_COUNT) & (df["word_count"] <= MAX_WORD_COUNT)]
    dropped_length = before_filter - len(df)
    logger.info(
        f"Filtered by word count ({MIN_WORD_COUNT}-{MAX_WORD_COUNT}): "
        f"dropped {dropped_length} resumes. Remaining: {len(df)}"
    )

    # ------------------------------------------------------------------
    # Step 5: Remove exact duplicates (by text fingerprint)
    # ------------------------------------------------------------------
    df["fingerprint"] = df["clean_text"].apply(text_fingerprint)

    before_dedup = len(df)
    df = df.drop_duplicates(subset=["fingerprint"], keep="first")
    dropped_exact_dup = before_dedup - len(df)
    logger.info(f"Removed {dropped_exact_dup} exact duplicates. Remaining: {len(df)}")

    # ------------------------------------------------------------------
    # Step 6: Remove near-duplicates (Jaccard similarity > threshold)
    # ------------------------------------------------------------------
    logger.info(
        f"Checking for near-duplicates (Jaccard > {NEAR_DUP_THRESHOLD})... "
        f"This may take a moment for {len(df)} resumes."
    )
    word_sets = df["clean_text"].apply(lambda x: set(x.lower().split())).tolist()
    indices = df.index.tolist()
    to_drop = set()

    for i in range(len(indices)):
        if indices[i] in to_drop:
            continue
        for j in range(i + 1, len(indices)):
            if indices[j] in to_drop:
                continue
            sim = jaccard_similarity(word_sets[i], word_sets[j])
            if sim > NEAR_DUP_THRESHOLD:
                to_drop.add(indices[j])

    df = df.drop(index=to_drop)
    logger.info(f"Removed {len(to_drop)} near-duplicates. Remaining: {len(df)}")

    # ------------------------------------------------------------------
    # Step 7: Compute metadata columns
    # ------------------------------------------------------------------
    df["unique_word_count"] = df["clean_text"].apply(lambda x: len(set(x.lower().split())))
    df["lexical_diversity"] = df.apply(
        lambda row: row["unique_word_count"] / row["word_count"] if row["word_count"] > 0 else 0,
        axis=1,
    )
    df["char_count"] = df["clean_text"].apply(len)

    # Assign unique resume IDs
    df = df.reset_index(drop=True)
    df["resume_id"] = [f"RES_{str(i).zfill(5)}" for i in range(len(df))]

    # Rename category column for consistency
    if cat_col:
        df = df.rename(columns={cat_col: "category"})
    else:
        df["category"] = "Unknown"

    # ------------------------------------------------------------------
    # Step 8: Select final columns and save
    # ------------------------------------------------------------------
    output_cols = [
        "resume_id",
        "category",
        "clean_text",
        "word_count",
        "unique_word_count",
        "lexical_diversity",
        "char_count",
    ]
    df_final = df[output_cols].copy()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_final.to_csv(OUTPUT_FILE, index=False)

    # ------------------------------------------------------------------
    # Summary Report
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("CLEANING COMPLETE — SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Final clean dataset size: {len(df_final)} resumes")
    logger.info(f"Saved to: {os.path.normpath(OUTPUT_FILE)}")
    logger.info(f"Category distribution:")
    for cat, count in df_final["category"].value_counts().items():
        logger.info(f"  {cat}: {count}")
    logger.info(f"Word count — Mean: {df_final['word_count'].mean():.0f}, "
                f"Median: {df_final['word_count'].median():.0f}, "
                f"Min: {df_final['word_count'].min()}, "
                f"Max: {df_final['word_count'].max()}")
    logger.info(f"Lexical diversity — Mean: {df_final['lexical_diversity'].mean():.3f}, "
                f"Std: {df_final['lexical_diversity'].std():.3f}")
    logger.info("=" * 60)

    return df_final


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    clean_dataset()
