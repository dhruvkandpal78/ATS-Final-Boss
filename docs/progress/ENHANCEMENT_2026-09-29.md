# Calibration safety follow-up

Inspected the current checkout after the interrupted September 28 pass. Current base is cd6c014. Earlier unfinished API and filtering changes were absent; unrelated recording scripts and artifacts were preserved.

## Implemented

- Module A rejects zero, negative, nonfinite, boolean and missing thresholds instead of turning any positive keyword density into a maximum signal.
- Shared analysis marks invalid keyword calibration unsupported, explains the validation requirement, and suppresses combined scoring. Available PDF and semantic findings remain usable for human review.
- Read-only doctor diagnostics validate both configured detector thresholds without loading models or opening research datasets.
- Added regression coverage for invalid calibration, preserved instruction findings, suppressed classifier invocation, and malformed diagnostic configuration.

## Remaining limitation

The checked-in keyword threshold is zero. It was not replaced with an invented value. Keyword and combined percentage scores remain unavailable until source-disjoint validation calibration is completed. Existing per-detector meters remain available for valid detector outputs; they are not calibrated probabilities of cheating. No held-out data was read, no artifacts were retrained, and no improved accuracy claim is made.

The larger earlier API/filtering changes are not claimed as delivered in this follow-up. A fresh calibration and independent benchmark remain the next accuracy milestone.

## Verification

- Offline full suite: `venv/Scripts/python.exe -m pytest tests/ --basetemp=.test-tmp/sep29-final -q`: 92 passed in 71.45 seconds.
- Focused calibration/diagnostic/service suite: 37 passed.
- JavaScript syntax and `git diff --check`: passed (Git reported only line-ending conversion warnings).
- Doctor exits 1 as expected for the existing zero Module A threshold; installed dependencies, artifact presence and embedding configuration cache passed inspection.
- No new frontend layout was delivered or browser verification claimed in this resumed pass. Restart an existing server process to load the backend changes.
