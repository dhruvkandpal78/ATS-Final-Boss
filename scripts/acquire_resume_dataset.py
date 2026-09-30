"""Download a pinned public PDF corpus as unlabeled research material.

Does not execute dataset content, assign clean labels, train, or open test splits.
"""
import hashlib
import json
from pathlib import Path
import zipfile

import requests

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.kaggle.com/api/v1/datasets/download/snehaanbhawal/resume-dataset?datasetVersionNumber=1"


def acquire():
    destination = ROOT / "data" / "external" / "kaggle-resume-v1"
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "source.zip"
    if not archive.exists():
        partial = destination / "source.partial"
        with requests.get(URL, stream=True, timeout=(15, 90)) as response:
            response.raise_for_status()
            total = 0
            with partial.open("wb") as output:
                for chunk in response.iter_content(1024 * 1024):
                    total += len(chunk)
                    if total > 150 * 1024 * 1024:
                        raise ValueError("Download exceeds corpus budget")
                    output.write(chunk)
        partial.replace(archive)
    rows = []
    with zipfile.ZipFile(archive) as bundle:
        entries = [item for item in bundle.infolist() if item.filename.lower().endswith(".pdf")]
        if sum(item.file_size for item in entries) > 500 * 1024 * 1024:
            raise ValueError("Uncompressed PDFs exceed corpus budget")
        for item in entries:
            if item.file_size > 5 * 1024 * 1024:
                continue
            raw = bundle.read(item)
            if not raw.startswith(b"%PDF-"):
                raise ValueError("Invalid PDF signature")
            digest = hashlib.sha256(raw).hexdigest()
            # Content-addressed paths avoid archive traversal and preserve deduplication.
            output = destination / "pdfs" / (digest + ".pdf")
            output.parent.mkdir(exist_ok=True)
            if not output.exists():
                output.write_bytes(raw)
            rows.append({"pdf_path": str(output.relative_to(destination)), "sha256": digest,
                         "source_id": "kaggle-resume-v1:" + digest,
                         "label_status": "unreviewed", "is_adversarial": None})
    metadata = {"source": "https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset",
                "version": 1, "publisher_license": "CC0: Public Domain",
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "pdf_count": len(rows), "unique_pdf_count": len({row['sha256'] for row in rows}),
                "usage": "Unreviewed real resume documents; not verified manipulation ground truth.",
                "records": rows}
    (destination / "provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in metadata.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    acquire()
