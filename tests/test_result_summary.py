"""Check that result copy cannot promote a detector score into a verdict."""
from pathlib import Path
import shutil
import subprocess

import pytest

NODE = shutil.which("node")
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(NODE is None, reason="Node required for frontend decision tests")
@pytest.mark.parametrize("case", [
    """const s = summarize({decision:'insufficient_evidence', modules:{a:{score:1}},
      findings:[{category:'keyword_density',review_trigger:false}]},'text');
      assert.equal(s.title,'Inconclusive'); assert.match(s.reason,/density alone/);""",
    """const s = summarize({decision:'review_recommended', modules:{c:{score:0}},
      findings:[{category:'direct_instruction',review_trigger:true}]},'text');
      assert.equal(s.title,'Needs review'); assert.match(s.reason,/Instructions/);""",
    """const s = summarize({decision:'no_signals_detected', score:1,
      findings:[{category:'keyword_density',review_trigger:false}]},'pdf');
      assert.equal(s.title,'No review triggers found'); assert.match(s.action,/does not verify/);""",
    """const s = summarize({decision:'unknown',verdict:'clean',score:0},'pdf');
      assert.equal(s.title,'Inconclusive');""",
])
def test_policy_decision_is_independent_of_numeric_signal(case):
    script = "const assert=require('node:assert/strict'); const summarize=require('./src/app/assets/result-summary.js');" + case
    subprocess.run([NODE, "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
