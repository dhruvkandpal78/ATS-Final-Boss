"""Launch the loopback demo with an explicitly pinned local research bundle.

This launcher does not approve a candidate for private deployment. Model files
remain outside the tracked source tree and are never copied by this script.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.artifacts import read_candidate_artifact, verify_candidate, verify_policy
from src.core.embedding_artifacts import verify_embedding


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--candidate-pin", required=True)
    parser.add_argument("--embedding", required=True, type=Path)
    parser.add_argument("--embedding-pin", required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be a valid TCP port")

    candidate = args.candidate.resolve(strict=True)
    embedding = args.embedding.resolve(strict=True)
    manifest = verify_candidate(candidate, args.candidate_pin)
    verify_policy(manifest)
    model_id = json.loads(read_candidate_artifact(candidate, "model_config.json"))["embedding_model"]
    verify_embedding(embedding, args.embedding_pin, expected_model_id=model_id)

    scratch = ROOT / ".test-tmp" / "local-demo-temp"
    scratch.mkdir(parents=True, exist_ok=True)
    # Exercise the exact directory lifecycle used by the worker before serving.
    with tempfile.TemporaryDirectory(prefix="ats-analysis-", dir=scratch):
        pass
    env = os.environ.copy()
    env.update({
        "ATS_DEPLOYMENT_MODE": "local",
        "ATS_MODELS_DIR": str(candidate),
        "ATS_CANDIDATE_MANIFEST_SHA256": args.candidate_pin.lower(),
        "ATS_EMBEDDING_DIR": str(embedding),
        "ATS_EMBEDDING_MANIFEST_SHA256": args.embedding_pin.lower(),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TMP": str(scratch),
        "TEMP": str(scratch),
        "TMPDIR": str(scratch),
        "HOST": "127.0.0.1",
        "PORT": str(args.port),
    })
    print(f"Verified local research bundle; starting loopback demo on port {args.port}.")
    return subprocess.call([sys.executable, "-m", "src.app.server"], cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
