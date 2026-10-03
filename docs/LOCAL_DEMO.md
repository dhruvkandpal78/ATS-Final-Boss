# Local pinned analysis demo

The browser can load before the analysis model does. `/health` reports
`model_ready: false` until a successful analysis starts the worker; this is a
cold state, not proof that the model bundle is broken. A 503 from `/analyze`
means the request did not complete and must not be replaced with a score or
heuristic result.

Use a **data-only V2 candidate** frozen for the current policy code and an
offline safetensors embedding export. Record each manifest's SHA-256 from the
reviewed source through an independent channel. The local launcher requires
both pins and verifies candidate integrity, frozen policy code and the exact
embedding tree before starting the loopback server:

```powershell
venv/Scripts/python.exe scripts/start_local_demo.py `
  --candidate 'C:\path\to\reviewed\candidate' `
  --candidate-pin '<64-digit candidate manifest SHA-256>' `
  --embedding 'C:\path\to\reviewed\embedding' `
  --embedding-pin '<64-digit embedding manifest SHA-256>'
```

The launcher runs the model offline and uses `.test-tmp/local-demo-temp` as
the parent for per-request temporary directories. It checks that directory
creation and cleanup work before serving. It does not select a replacement
candidate, download model files, or relax the private deployment controls.
The local server remains bound to `127.0.0.1`.

Research candidates refrozen against changed policy code are new experimental
bundles. Keeping coefficients and thresholds unchanged does not transfer
calibration, validation, or deployment approval. Private mode requires an
explicitly approved candidate in addition to both independent pins and the
existing startup checks.

## Current checkout example (October 3, 2026)

The old `results/models` directory contains only unsupported pickle files.
An earlier local server started without a candidate path, so its first model
load failed closed with 503. This Windows environment also denied access to
some Python-created directories under the default system temporary directory;
the launcher uses a workspace-local parent and checks the exact temporary
directory lifecycle before serving.

The ignored local research bundle for this checkout can be started with:

```powershell
venv/Scripts/python.exe scripts/start_local_demo.py `
  --candidate .test-tmp/local-demo-current-policy-20261003/candidate `
  --candidate-pin 8e9259ed6e9a20d15fa6790f1c57aa06ffba08b670be2c5862f6e1fcbc5c899e `
  --embedding .test-tmp/github-publication/.test-tmp/kaggle-model-20261003/embedding `
  --embedding-pin d322a13d4a68f9ee3defed17d8fa1638f36bd63772748b30dae5f71e6060702e
```

Those hashes are local integrity records for this experimental demo, not
independent deployment approvals. The bundle is ignored and must not be
committed or uploaded. The public checkout has different frozen policy bytes;
copying this bundle there would fail verification. A public-checkout demo
needs its own new, explicitly unapproved current-policy candidate export and
pins. No new accuracy, calibration or readiness claim follows from the local
HTTP smoke.
