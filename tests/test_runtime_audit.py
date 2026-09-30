import pytest
from scripts.audit_runtime import advisory_requirements


def test_cpu_variant_uses_upstream_advisory_without_installing_variant():
    assert advisory_requirements("--index-url https://pypi.org/simple\ntorch==2.14.0+cpu \\\n    --hash=sha256:abc\nnumpy==2.5.3") == ["torch==2.14.0", "numpy==2.5.3"]
    with pytest.raises(ValueError, match="Unreviewed"):
        advisory_requirements("other==1.0+custom")
