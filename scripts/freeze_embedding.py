"""Freeze an operator-reviewed offline embedding export into an exclusive manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.embedding_artifacts import MANIFEST_NAME, freeze_embedding


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="explicit approved local export directory")
    parser.add_argument("--model-id", required=True, help="reviewed upstream model identity")
    parser.add_argument("--upstream-revision", required=True, help="full 40-digit upstream commit hash")
    args = parser.parse_args(argv)
    try:
        digest = freeze_embedding(args.directory, args.model_id, args.upstream_revision)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Embedding freeze failed: {exc}\n")
    print(json.dumps({"manifest": str(args.directory / MANIFEST_NAME),
                      "manifest_sha256": digest, "model_id": args.model_id,
                      "note": "Pin this digest independently; the manifest does not establish publisher identity."},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
