import csv
import hashlib
import json

import fitz

from scripts.build_controlled_pdf_benchmark import build


def test_controlled_benchmark_keeps_source_groups_disjoint(tmp_path):
    corpus = tmp_path / "corpus"
    pdfs = corpus / "pdfs"
    pdfs.mkdir(parents=True)
    records = []
    for index in range(48):
        source = pdfs / f"{index}.pdf"
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_textbox(fitz.Rect(40, 40, 560, 700),
                                (f"Synthetic developer {index} maintained SQL reports. " * 12), fontsize=10)
            doc.save(source)
        records.append({"pdf_path": f"pdfs/{index}.pdf", "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "source_id": f"synthetic-{index}"})
    (corpus / "provenance.json").write_text(json.dumps({"source": "synthetic",
        "archive_sha256": "synthetic", "records": records}))
    output = tmp_path / "benchmark"
    build(corpus, output)
    seen = []
    for split, source_count in (("train", 24), ("validation", 12), ("holdout", 12)):
        with (output / f"{split}.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == source_count * 3
        assert {int(row["is_adversarial"]) for row in rows} == {0, 1}
        assert all(sum(row["source_id"] == source for row in rows) == 3
                   for source in {row["source_id"] for row in rows})
        seen.append({row["source_id"] for row in rows})
    assert not seen[0] & seen[1] and not seen[0] & seen[2] and not seen[1] & seen[2]
