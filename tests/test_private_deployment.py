"""Synthetic, offline checks for private-pilot deployment configuration."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts.check_private_deployment import DEFAULT_COMPOSE, validate_compose


@pytest.fixture
def compose():
    """Load the checked-in config only; the test uses no secrets or model files."""
    return yaml.safe_load(Path(DEFAULT_COMPOSE).read_text(encoding="utf-8"))


def test_reference_compose_satisfies_private_pilot_contract(compose):
    assert validate_compose(compose) == []


@pytest.mark.parametrize("change", [
    lambda service: service.update(ports=["8000:8000"]),
    lambda service: service.update(network_mode="host"),
    lambda service: service.update(read_only=False),
    lambda service: service.update(user="0:0"),
    lambda service: service.update(user="10001:0"),
    lambda service: service.update(user="10001"),
    lambda service: service.update(cap_drop=[]),
    lambda service: service.update(cap_add=["SYS_ADMIN"]),
    lambda service: service.update(devices=["/dev/sda:/dev/sda:rwm"]),
    lambda service: service.update(security_opt=[]),
    lambda service: service.update(mem_limit=None),
    lambda service: service.update(cpus=0),
    lambda service: service.update(pids_limit=0),
    lambda service: service.update(tmpfs=[]),
    lambda service: service.update(tmpfs=["/tmp/ats-analysis:rw,noexec,nosuid,nodev,size=0"]),
    lambda service: service["tmpfs"].append("/other:rw,size=1m"),
    lambda service: service.update(mem_limit=float("inf")),
    lambda service: service.update(cpus=float("nan")),
    lambda service: service.update(networks=[]),
    lambda service: service["environment"].update(ATS_DEPLOYMENT_MODE="demo"),
    lambda service: service["environment"].update(ATS_ALLOWED_HOSTS="*"),
    lambda service: service["environment"].update(ATS_CANDIDATE_MANIFEST_SHA256=""),
    lambda service: service["volumes"][0].update(read_only=False),
    lambda service: service["volumes"][0].update(source="/arbitrary/models"),
    lambda service: service["volumes"].append({"type": "bind", "source": "/var/run/docker.sock", "target": "/var/run/docker.sock"}),
    lambda service: service["volumes"].append({"type": "bind", "source": "/host/data", "target": "/data", "read_only": False}),
])
def test_security_regression_is_rejected(compose, change):
    mutated = deepcopy(compose)
    change(mutated["services"]["ats-review"])
    assert validate_compose(mutated)


def test_missing_gateway_token_secret_is_rejected(compose):
    mutated = deepcopy(compose)
    mutated["secrets"].pop("ats_api_token")
    assert any("ats_api_token" in error for error in validate_compose(mutated))


def test_gateway_token_secret_must_use_expected_mount_path(compose):
    mutated = deepcopy(compose)
    mutated["services"]["ats-review"]["secrets"] = [
        {"source": "ats_api_token", "target": "/tmp/token"}
    ]
    assert any("mounted at /run/secrets/ats_api_token" in error for error in validate_compose(mutated))


def test_external_network_without_internal_flag_is_rejected(compose):
    mutated = deepcopy(compose)
    mutated["networks"]["pilot-private"]["internal"] = False
    assert any("internal: true" in error for error in validate_compose(mutated))


def test_second_external_network_is_rejected(compose):
    mutated = deepcopy(compose)
    mutated["networks"]["outside"] = {"internal": False}
    mutated["services"]["ats-review"]["networks"].append("outside")
    assert any("outside" in error and "internal: true" in error for error in validate_compose(mutated))


def test_gateway_template_disables_default_access_logging():
    gateway = Path(DEFAULT_COMPOSE).parent / "gateway.example.conf"
    content = gateway.read_text(encoding="utf-8")
    assert "access_log off;" in content
    assert "include /etc/nginx/private/ats-api-token.conf;" in content
    assert "auth_request /_customer_sso_authorize;" in content
