"""Fail-closed controls for local demos and a single-organization private pilot."""
from dataclasses import dataclass
import hmac
import ipaddress
import os
from pathlib import Path
import re
import threading
from time import monotonic
from urllib.parse import urlsplit


def loopback(host):
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def origin(value):
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username
                or parsed.password or parsed.path or parsed.query or parsed.fragment):
            raise ValueError
        parsed.port  # Validate malformed ports.
        return f"{parsed.scheme}://{parsed.netloc.lower()}"
    except ValueError:
        raise ValueError("Origins must be exact http(s) origins without paths") from None


@dataclass(frozen=True)
class SecuritySettings:
    mode: str = "local"
    allowed_hosts: tuple = ("localhost", "127.0.0.1", "::1")
    allowed_origins: tuple = ()
    token: str = ""
    requests_per_minute: int = 20
    worker_memory_mib: int = 4096

    @classmethod
    def from_env(cls, bind_host):
        mode = os.environ.get("ATS_DEPLOYMENT_MODE", "local")
        if mode not in ("local", "private"):
            raise ValueError("ATS_DEPLOYMENT_MODE must be local or private")
        if mode == "local" and not loopback(bind_host):
            raise ValueError("Local mode requires a loopback bind address")
        host_config = os.environ.get("ATS_ALLOWED_HOSTS", "")
        hosts = tuple(item.strip().lower() for item in host_config.split(",") if item.strip())
        if not hosts and mode == "local":
            hosts = cls.allowed_hosts
        if not hosts or any("*" in item or "/" in item or "@" in item for item in hosts):
            raise ValueError("Private mode requires explicit ATS_ALLOWED_HOSTS hostnames")
        origins = tuple(origin(item.strip()) for item in os.environ.get("ATS_ALLOWED_ORIGINS", "").split(",") if item.strip())
        token = ""
        if mode == "private":
            secret_path = os.environ.get("ATS_API_TOKEN_FILE", "")
            if not secret_path or Path(secret_path).stat().st_size > 4096:
                raise ValueError("Private mode requires a bounded ATS_API_TOKEN_FILE")
            token = Path(secret_path).read_text(encoding="ascii").strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token):
                raise ValueError("API secret must contain 32-256 URL-safe random characters")
            if not origins or any(not item.startswith("https://") for item in origins):
                raise ValueError("Private mode requires exact HTTPS allowed origins")
            if not re.fullmatch(r"[a-fA-F0-9]{64}", os.environ.get("ATS_CANDIDATE_MANIFEST_SHA256", "")):
                raise ValueError("Private mode requires an independently pinned candidate manifest hash")
        rate = int(os.environ.get("ATS_REQUESTS_PER_MINUTE", "20"))
        memory = int(os.environ.get("ATS_WORKER_MEMORY_MIB", "4096"))
        if not 1 <= rate <= 120 or not 512 <= memory <= 16384:
            raise ValueError("Rate or worker memory setting is outside supported bounds")
        return cls(mode, hosts, origins, token, rate, memory)

    def authorize(self, headers, method, port, path):
        hosts = headers.get_all("Host", [])
        if len(hosts) != 1:
            return 400, "One Host header is required."
        try:
            parsed = urlsplit("http://" + hosts[0])
            if (parsed.hostname not in self.allowed_hosts or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment):
                return 403, "Request host is not allowed."
            parsed.port
        except ValueError:
            return 400, "Invalid Host header."
        supplied_origins = headers.get_all("Origin", [])
        if len(supplied_origins) > 1:
            return 400, "Only one Origin header is allowed."
        if supplied_origins:
            try:
                supplied = origin(supplied_origins[0])
            except ValueError:
                return 403, "Request origin is not allowed."
            allowed = self.allowed_origins or tuple(
                f"http://{host}:{port}" for host in ("localhost", "127.0.0.1", "[::1]"))
            if supplied not in allowed:
                return 403, "Request origin is not allowed."
        if method == "POST" and headers.get("Sec-Fetch-Site") == "cross-site":
            return 403, "Cross-site requests are not allowed."
        if self.mode == "private" and not (method == "GET" and path == "/health/live"):
            authorizations = headers.get_all("Authorization", [])
            if len(authorizations) != 1 or not authorizations[0].startswith("Bearer "):
                return 401, "Authentication is required."
            candidate = authorizations[0][7:]
            if not candidate.isascii() or not hmac.compare_digest(candidate, self.token):
                return 401, "Authentication is required."
        return None


class RequestBudget:
    """A bounded global budget: proxy identity headers are never trusted."""
    def __init__(self, limit, clock=monotonic):
        self.limit, self.clock = limit, clock
        self.lock = threading.Lock()
        self.started = clock()
        self.count = 0

    def consume(self):
        with self.lock:
            now = self.clock()
            if now - self.started >= 60:
                self.started, self.count = now, 0
            if self.count >= self.limit:
                return False
            self.count += 1
            return True
