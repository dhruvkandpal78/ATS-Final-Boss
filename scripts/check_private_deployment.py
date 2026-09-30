"""Offline fail-closed checks for the private pilot Compose security contract.

This validates configuration shape only. It does not resolve Compose variables,
read secret files, contact a Docker daemon, or prove the resulting deployment is
secure. Run with: python scripts/check_private_deployment.py
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import sys
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised on missing tool installs
    raise SystemExit("PyYAML is required to validate Compose syntax; install project dependencies first.") from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPOSE = ROOT / "deploy" / "compose.yaml"
TOKEN_PATH = "/run/secrets/ats_api_token"


def _number(value: Any) -> float | None:
    """Parse resource amounts used by the checked Compose contract."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmgt]?)\s*(?:b)?\s*", value, re.I)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2).lower()
    factors = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3, "t": 1024**4}
    return amount * factors[unit]


def _env_map(environment: Any) -> dict[str, Any]:
    if isinstance(environment, dict):
        return environment
    result: dict[str, Any] = {}
    if isinstance(environment, list):
        for item in environment:
            if isinstance(item, str) and "=" in item:
                key, value = item.split("=", 1)
                result[key] = value
    return result


def _secret_file_ref(value: Any) -> bool:
    return isinstance(value, str) and "ATS_API_TOKEN_FILE" in value and ":?" in value


def validate_compose(document: Any) -> list[str]:
    """Return actionable violations of the single-service private pilot contract."""
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["Compose document must be a YAML mapping."]

    services = document.get("services")
    service = services.get("ats-review") if isinstance(services, dict) else None
    if not isinstance(service, dict):
        return ["Compose must define the ats-review service."]

    # No published host port is permitted: the customer gateway shares the
    # private network and is the sole ingress point.
    if "ports" in service and service["ports"]:
        errors.append("ats-review must not publish host ports; route only through the private gateway network.")
    if service.get("network_mode") == "host":
        errors.append("ats-review must not use host networking.")
    if service.get("privileged") is True:
        errors.append("ats-review must not run privileged.")
    if service.get("read_only") is not True:
        errors.append("ats-review must set read_only: true.")

    user = service.get("user")
    if not isinstance(user, str) or not re.fullmatch(r"\d+:\d+", user):
        errors.append("ats-review must set an explicit numeric non-root user and group.")
    else:
        uid, gid = (int(part) for part in user.split(":", 1))
        if uid == 0 or gid == 0:
            errors.append("ats-review must not run with UID 0 or GID 0.")

    caps = service.get("cap_drop")
    if not isinstance(caps, list) or "ALL" not in [str(cap).upper() for cap in caps]:
        errors.append("ats-review must drop all Linux capabilities.")
    cap_add = service.get("cap_add", [])
    if cap_add:
        errors.append("ats-review must not add Linux capabilities after dropping all capabilities.")
    devices = service.get("devices", [])
    if devices:
        errors.append("ats-review must not mount host devices.")
    security_opts = service.get("security_opt", [])
    if not isinstance(security_opts, list) or not any(
        isinstance(option, str) and option.lower() == "no-new-privileges:true" for option in security_opts
    ):
        errors.append("ats-review must set no-new-privileges:true.")

    memory = _number(service.get("mem_limit"))
    if memory is None or memory <= 0:
        errors.append("ats-review must set a finite positive mem_limit.")
    cpu = _number(service.get("cpus"))
    if cpu is None or cpu <= 0:
        errors.append("ats-review must set a finite positive CPU limit.")
    pids = service.get("pids_limit")
    if not isinstance(pids, int) or isinstance(pids, bool) or pids <= 0:
        errors.append("ats-review must set a finite positive pids_limit.")

    tmpfs = service.get("tmpfs")
    tmpfs_items = tmpfs if isinstance(tmpfs, list) else []
    private_tmp = [item for item in tmpfs_items if isinstance(item, str) and item.startswith("/tmp/ats-analysis:")]
    if len(private_tmp) != 1 or len(tmpfs_items) != 1:
        errors.append("ats-review must provide bounded tmpfs at /tmp/ats-analysis.")
    elif private_tmp:
        entry = private_tmp[0]
        options = entry.split(":", 1)[1].split(",")
        size_value = next((option[5:] for option in options if option.startswith("size=")), None)
        tmp_size = _number(size_value) if size_value else None
        if (not all(flag in options for flag in ("noexec", "nosuid", "nodev"))
                or tmp_size is None or tmp_size <= 0):
            errors.append("/tmp/ats-analysis tmpfs must set a finite positive size, noexec, nosuid, and nodev.")

    networks = document.get("networks")
    attached = service.get("networks")
    private_networks = set(attached.keys() if isinstance(attached, dict) else attached if isinstance(attached, list) else [])
    network_defs = networks if isinstance(networks, dict) else {}
    if not private_networks:
        errors.append("ats-review must attach to an explicitly defined internal network.")
    else:
        for name in private_networks:
            if not isinstance(network_defs.get(name), dict) or network_defs[name].get("internal") is not True:
                errors.append(f"ats-review network {name!r} must be defined with internal: true.")

    env = _env_map(service.get("environment"))
    required = {
        "ATS_DEPLOYMENT_MODE": "private",
        "ATS_API_TOKEN_FILE": TOKEN_PATH,
        "ATS_MODELS_DIR": "/models",
    }
    for key, expected in required.items():
        if env.get(key) != expected:
            errors.append(f"ats-review must set {key}={expected}.")
    for key in ("ATS_ALLOWED_HOSTS", "ATS_ALLOWED_ORIGINS"):
        value = env.get(key)
        if not isinstance(value, str) or "${" not in value or ":?" not in value:
            errors.append(f"ats-review must require {key} through a non-empty Compose variable expression.")
        elif "*" in value or "0.0.0.0" in value:
            errors.append(f"ats-review must not allow wildcard values for {key}.")

    pin = env.get("ATS_CANDIDATE_MANIFEST_SHA256")
    if not isinstance(pin, str) or "${" not in pin or "ATS_CANDIDATE_MANIFEST_SHA256" not in pin or ":?" not in pin:
        errors.append("ats-review must require an externally configured ATS_CANDIDATE_MANIFEST_SHA256.")

    secrets = document.get("secrets")
    secret_definition = secrets.get("ats_api_token") if isinstance(secrets, dict) else None
    if not isinstance(secret_definition, dict) or not _secret_file_ref(secret_definition.get("file")):
        errors.append("ats_api_token must come from a required ATS_API_TOKEN_FILE Compose secret source.")
    service_secrets = service.get("secrets", [])
    token_secret_mounts = [item for item in (service_secrets if isinstance(service_secrets, list) else [])
                           if item == "ats_api_token" or isinstance(item, dict) and item.get("source") == "ats_api_token"]
    if not token_secret_mounts:
        errors.append("ats-review must mount the ats_api_token secret.")
    elif any(isinstance(item, dict) and item.get("target", TOKEN_PATH) != TOKEN_PATH for item in token_secret_mounts):
        errors.append(f"ats_api_token must be mounted at {TOKEN_PATH}.")

    volumes = service.get("volumes", [])
    model_mounts = [item for item in volumes if isinstance(item, dict) and item.get("target") == "/models"] \
        if isinstance(volumes, list) else []
    if not model_mounts or not any(
        item.get("read_only") is True and item.get("type") == "bind"
        and isinstance(item.get("source"), str) and "ATS_MODELS_PATH" in item["source"] and ":?" in item["source"]
        for item in model_mounts
    ):
        errors.append("ats-review must bind-mount provisioned ATS_MODELS_PATH at /models read-only.")
    for mount in volumes if isinstance(volumes, list) else []:
        if isinstance(mount, str):
            source = mount.split(":", 1)[0]
            target = mount.split(":", 2)[1] if ":" in mount else ""
            readonly = len(mount.split(":")) >= 3 and "ro" in mount.split(":", 2)[2].split(",")
        elif isinstance(mount, dict):
            source, target = mount.get("source", ""), mount.get("target", "")
            readonly = mount.get("read_only") is True
        else:
            errors.append("ats-review volume entries must be explicit mounts.")
            continue
        if "docker.sock" in str(source).replace("\\", "/").lower():
            errors.append("ats-review must not mount the Docker socket.")
        if target != "/models" or not readonly:
            errors.append("ats-review may mount only /models, and that mount must be read-only.")

    return errors


def check_file(path: Path = DEFAULT_COMPOSE) -> list[str]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [f"Could not parse Compose YAML at {path}: {exc}"]
    return validate_compose(document)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compose", nargs="?", type=Path, default=DEFAULT_COMPOSE,
                        help="Compose YAML file (default: deploy/compose.yaml)")
    args = parser.parse_args(argv)
    errors = check_file(args.compose)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: private pilot Compose controls present in {args.compose}")
    print("This offline shape check does not resolve variables or prove runtime isolation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
