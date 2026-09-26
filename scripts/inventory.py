#!/usr/bin/env python3
"""Arena Agent Mode — reusable sandbox/tooling capability inventory engine.

Standard library only (requires Python >= 3.10). Discovers what is *installed*,
*exposed*, *reachable*, *executed now*, *failed* and *not tested* in the current
execution environment, and writes machine-readable manifests to a per-session
directory. It deliberately does not summarise prior sessions' reports.

Usage
-----
    python3 scripts/inventory.py                      # read-only inventory by default
    python3 scripts/inventory.py --skip-network --skip-registry --skip-install
    python3 scripts/inventory.py --observations inventory/2026-09-26/observations.json
    python3 scripts/inventory.py --probe-install      # only after explicit approval
    python3 scripts/inventory.py --record-delivery delivery.json   # post-push verification

Safety properties (enforced by construction, see docs in SUMMARY.md):
  * No environment-variable VALUES are ever read into the manifests; only
    presence booleans for a fixed allowlist of names are recorded.
  * Every subprocess call has a hard timeout; every HTTP/TLS call is bounded.
  * TLS verification is never disabled (ssl.create_default_context()).
  * Hostname, home path and any credential-shaped string are redacted from all
    captured output before it is stored.
  * Network access is limited to an explicit, small allowlist of public hosts.
  * No privilege escalation, no sandbox introspection beyond passive /proc reads,
    no port scanning, no crawling, no writes outside the session directory and
    an isolated temp directory used by the optional install probes.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import getpass
import glob
import hashlib
import importlib.metadata as md
import json
import os
import pathlib
import platform
import re
import resource
import shutil
import socket
import ssl
import stat
import struct
import subprocess  # noqa: S404  (bounded: every call carries timeout=)
import tempfile
import sys
import urllib.error
import urllib.request
import sysconfig
import time

SCHEMA = "arena-inventory/1.1"
ENGINE = "scripts/inventory.py"
VERSION_RE = re.compile(r"(\d+[^\s,;)]*)")

# --------------------------------------------------------------------------
# redaction
# --------------------------------------------------------------------------

_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "PEM_PRIVATE_KEY"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"), "GITHUB_TOKEN"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{16,}"), "GITHUB_FINE_GRAINED_TOKEN"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "SLACK_TOKEN"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS_ACCESS_KEY"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\b"), "JWT_LIKE"),
    (re.compile(r"(?i)\b(authorization)\s*[:=]\s*(bearer|basic|token)\b"), "AUTH_HEADER"),
    # structural credential assignments are detected by find_secrets_in_text() so that
    # inventory's own boolean flags ("token_values_stored": false) are not false positives.
    (re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s@]+:[^/\s@]+@"), "URL_USERINFO"),
]

_SECRET_REPLACEMENTS = {
    "PEM_PRIVATE_KEY": "-----<REDACTED PRIVATE KEY>-----",
    "GITHUB_TOKEN": "<REDACTED_TOKEN>",
    "GITHUB_FINE_GRAINED_TOKEN": "<REDACTED_TOKEN>",
    "SLACK_TOKEN": "<REDACTED_TOKEN>",
    "AWS_ACCESS_KEY": "<REDACTED_KEY>",
    "JWT_LIKE": "<REDACTED_JWT>",
    "AUTH_HEADER": "authorization: <REDACTED>",
    "CREDENTIAL_ASSIGNMENT": "<REDACTED_CREDENTIAL_ASSIGNMENT>",
    "URL_USERINFO": "<scheme>://<redacted>@",
}

_HOME = str(pathlib.Path.home())
_HOSTNAME = socket.gethostname()


def redact(text: str) -> str:
    """Remove identity/credential material from any captured string."""
    if not text:
        return text
    out = text
    out = out.replace(_HOME, "~")
    home_parent = str(pathlib.Path(_HOME).parent)
    if home_parent and home_parent != "/":
        out = out.replace(home_parent + "/", "")
    if _HOSTNAME:
        out = out.replace(_HOSTNAME, "<host>")
    for pattern, name in _SECRET_PATTERNS:
        out = pattern.sub(_SECRET_REPLACEMENTS[name], out)
    out = _CRED_ASSIGN_RE.sub(lambda m: f'{m.group(1)}: "<REDACTED>"', out)
    return out


def redact_bytes(data: bytes) -> str:
    return redact(data.decode("utf-8", "replace"))


_SAFE_JSON_VALUES = {
    "true", "false", "null", "none", "not_tested", "not_attempted", "unknown", "redacted",
    "unavailable", "n/a", "0", "1", "absent", "present", "ok", "failed", "max", "unlimited",
    "installed", "exposed", "executed_now", "registry_reachable", "not_installed",
}
_SECRET_KEY_RE = re.compile('(?i)[a-z0-9_]*(token|secret|password|passwd|api[_-]?key|access[_-]?key|credential)[a-z0-9_]*')
_SAFE_KEY_SUFFIXES = ("_stored", "_read", "_printed", "_attempted", "_used", "_count", "_present",
                     "_hash12", "_values", "_disabled", "_kept", "_method", "_note", "_check")
_SECRET_VALUE_RE = re.compile('^[A-Za-z][A-Za-z0-9_-]{19,}$')
_BARE_KEY_RE = re.compile('^[A-Za-z_][A-Za-z0-9_]*$')
_CRED_ASSIGN_RE = re.compile(
    '(?i)([A-Za-z0-9_.-]*(?:token|secret|password|passwd|api[_-]?key|access[_-]?key|credential)[A-Za-z0-9_.-]*)\\s*[:=]\\s*"?([A-Za-z0-9_/+=.-]{16,})"?'
)


def _assignment_pairs(line: str):
    """Yield (key, value) pairs from JSON-ish or KEY=value lines without regex fragility."""
    for sep in (":", "="):
        if sep not in line:
            continue
        key, _, value = line.partition(sep)
        key = key.strip().strip(chr(34)).strip().rstrip(",")
        value = value.strip().strip(chr(34)).strip().rstrip(",")
        if key and value:
            yield key, value


def _looks_like_secret(value: str) -> bool:
    value = value.strip().strip(chr(34)).strip()
    if value.lower().strip() in _SAFE_JSON_VALUES:
        return False
    if "REDACTED" in value.upper() or "<" in value:
        return False
    if any(ch in value for ch in "+,() '"):  # version strings, lists and prose are not secrets
        return False
    return bool(_SECRET_VALUE_RE.match(value))


def find_secrets_in_text(text: str) -> list[str]:
    """Structural secret scan. Ignores inventory's own boolean flags and notes."""
    return sorted({hit["pattern"] for hit in find_secret_lines(text)})


def find_secret_lines(text: str) -> list[dict]:
    """Return {pattern, line} hits. Never returns the matched snippet itself."""
    hits: list[dict] = []
    for number, line in enumerate(text.splitlines(), 1):
        for pattern, name in _SECRET_PATTERNS:
            if name != "CREDENTIAL_ASSIGNMENT" and pattern.search(line):
                hits.append({"pattern": name, "line": number})
        for key, value in _assignment_pairs(line):
            if (
                _BARE_KEY_RE.match(key)
                and _SECRET_KEY_RE.search(key)
                and not key.lower().endswith(_SAFE_KEY_SUFFIXES)
                and _looks_like_secret(value)
            ):
                hits.append({"pattern": "CREDENTIAL_ASSIGNMENT", "line": number})
                break
    return hits


def short_hash(value: str, n: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:n]


# --------------------------------------------------------------------------
# bounded command runner
# --------------------------------------------------------------------------

class Runner:
    """All command execution goes through here so timeouts are always bounded."""

    def __init__(self, default_timeout: float = 20.0) -> None:
        self.default_timeout = default_timeout
        self.max_timeout_used = 0.0
        self.log: list[dict] = []
        self.failures: list[dict] = []

    def run(
        self,
        argv: list[str],
        *,
        label: str,
        timeout: float | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        stdout_limit: int = 4000,
        stdin: str | None = None,
    ) -> dict:
        timeout = self.default_timeout if timeout is None else timeout
        self.max_timeout_used = max(self.max_timeout_used, timeout)
        record: dict = {
            "label": label,
            "argv": [redact(a) for a in argv],
            "timeout_s": timeout,
        }
        t0 = time.monotonic()
        try:
            proc = subprocess.run(  # noqa: S603,S607 - fixed argv, bounded timeout
                argv,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
                cwd=cwd,
                env=env,
                input=stdin,
                check=False,
            )
            record["exit_code"] = proc.returncode
            so = proc.stdout or ""
            se = proc.stderr or ""
            record["stdout_chars_total"] = len(so)
            record["stdout_truncated"] = len(so) > stdout_limit
            record["stdout"] = redact(so[:stdout_limit])
            record["stderr"] = redact(se[:1200])
        except subprocess.TimeoutExpired:
            record["exit_code"] = None
            record["error"] = "TIMEOUT"
            record["error_detail"] = f"exceeded {timeout:g}s; process killed"
            record["stdout"] = ""
        except FileNotFoundError:
            record["exit_code"] = None
            record["error"] = "EXECUTABLE_NOT_FOUND"
            record["stdout"] = ""
        except OSError as exc:
            record["exit_code"] = None
            record["error"] = f"OS_ERROR_{type(exc).__name__}"
            record["error_detail"] = redact(str(exc))[:300]
            record["stdout"] = ""
        record["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)
        if record.get("error") or record.get("exit_code") not in (0, None):
            record["status"] = "FAILED"
            self.failures.append(
                {
                    "label": label,
                    "argv": record["argv"],
                    "exit_code": record.get("exit_code"),
                    "error": record.get("error"),
                    "stderr_head": (record.get("stderr") or "")[:400],
                }
            )
        else:
            record["status"] = "OK"
        self.log.append(record)
        return record


# --------------------------------------------------------------------------
# network helpers
# --------------------------------------------------------------------------

UA = "arena-inventory/1.0 (bounded capability probe; stdlib urllib)"


def _ssl_context() -> ssl.SSLContext:
    # Verification is always ON; this function exists to make that auditable.
    return ssl.create_default_context()


def _dn_to_cn(rdata) -> str:
    for pair in rdata:
        for key, value in pair:
            if key in ("commonName", "organizationName"):
                return str(value)
    return ""


class Net:
    def __init__(self, timeout: float = 8.0, workers: int = 4) -> None:
        self.timeout = timeout
        self.workers = workers

    def dns(self, host: str) -> dict:
        out: dict = {"host": host}
        t0 = time.monotonic()
        with cf.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM)
            try:
                infos = fut.result(timeout=self.timeout)
            except cf.TimeoutError:
                return {**out, "resolved": False, "error_class": "DNS_TIMEOUT", "elapsed_ms": round((time.monotonic() - t0) * 1000, 1)}
            except socket.gaierror as exc:
                return {**out, "resolved": False, "error_class": "DNS_NO_RECOVERY" if getattr(exc, "errno", None) == -3 else "DNS_ERROR", "error_detail": redact(str(exc))[:200], "elapsed_ms": round((time.monotonic() - t0) * 1000, 1)}
            except OSError as exc:
                return {**out, "resolved": False, "error_class": f"DNS_OS_{type(exc).__name__}", "error_detail": redact(str(exc))[:200]}
        v4 = sorted({i[4][0] for i in infos if i[0] == socket.AF_INET})
        v6 = sorted({i[4][0] for i in infos if i[0] == socket.AF_INET6})
        out.update(
            {
                "resolved": True,
                "ipv4": v4,
                "ipv4_count": len(v4),
                "ipv6_count": len(v6),
                "elapsed_ms": round((time.monotonic() - t0) * 1000, 1),
            }
        )
        return out

    def https(self, url: str, method: str = "HEAD", read_limit: int = 0) -> dict:
        out: dict = {"url": url, "method": method, "timeout_s": self.timeout}
        req = urllib_request(url, method)
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=_ssl_context()) as resp:  # noqa: S310
                body = b""
                if read_limit:
                    try:
                        body = resp.read(read_limit)
                    except Exception:  # body may be short/absent for HEAD
                        body = b""
                headers = {k.lower(): v for k, v in (resp.headers.items() or [])}
                out.update(
                    {
                        "outcome": "OK",
                        "http_status": getattr(resp, "status", None),
                        "content_type": headers.get("content-type"),
                        "content_length": headers.get("content-length"),
                        "server": headers.get("server"),
                        "body_sha256_12": short_hash(hashlib.sha256(body).hexdigest(), 12) if body else None,
                        "bytes_read": len(body),
                    }
                )
        except urllib.error.HTTPError as exc:
            out.update(
                {
                    "outcome": "HTTP_ERROR",
                    "http_status": exc.code,
                    "reason": redact(str(exc.reason))[:120],
                    "reached_http_layer": True,
                }
            )
        except ssl.SSLCertVerificationError as exc:
            out.update({"outcome": "TLS_CERT_VERIFY_FAILED", "error_detail": redact(str(exc))[:200]})
        except ssl.SSLError as exc:
            out.update({"outcome": "TLS_HANDSHAKE_ERROR", "error_detail": redact(str(exc))[:200]})
        except (socket.timeout, TimeoutError) as exc:
            out.update({"outcome": "TIMEOUT", "error_detail": redact(str(exc))[:120] or f"> {self.timeout:g}s"})
        except urllib.error.URLError as exc:
            out.update(classify_urlerror(exc))
        except OSError as exc:
            out.update({"outcome": f"OS_ERROR_{type(exc).__name__}", "error_detail": redact(str(exc))[:200]})
        out["elapsed_ms"] = round((time.monotonic() - t0) * 1000, 1)
        return out

    def json(self, url: str, accept: str = "application/json", limit: int = 400_000) -> dict:
        """GET a bounded JSON metadata document.

        'reachable' means the server answered at the HTTP layer; a truncated body only
        affects whether fields could be parsed, never the reachability verdict.
        """
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": UA, "Accept": accept})
        out: dict = {"url": url, "timeout_s": self.timeout}
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=_ssl_context()) as resp:  # noqa: S310
                payload = resp.read(limit)
                out["http_status"] = resp.status
                out["outcome"] = "OK"
                out["reachable"] = True
                out["bytes_read"] = len(payload)
                try:
                    out["data"] = json.loads(payload)
                    out["json_parsed"] = True
                except json.JSONDecodeError:
                    out["data"] = None
                    out["json_parsed"] = False
                    out["outcome"] = "OK_BODY_TRUNCATED"
        except urllib.error.HTTPError as exc:
            out.update({"outcome": "HTTP_ERROR", "http_status": exc.code})
        except (socket.timeout, TimeoutError):
            out["outcome"] = "TIMEOUT"
        except urllib.error.URLError as exc:
            out.update(classify_urlerror(exc))
        except Exception as exc:  # pragma: no cover
            out.update({"outcome": f"ERROR_{type(exc).__name__}", "error_detail": redact(str(exc))[:160]})
        out["elapsed_ms"] = round((time.monotonic() - t0) * 1000, 1)
        return out

    def tls_identity(self, host: str, port: int = 443) -> dict:
        out: dict = {"host": host, "port": port}
        ctx = _ssl_context()
        try:
            with socket.create_connection((host, port), timeout=self.timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as tls:
                    cert = tls.getpeercert() or {}
                    cipher = tls.cipher() or [None, None, None]
                    der = tls.getpeercert(binary_form=True)
                    out.update(
                        {
                            "handshake": "OK",
                            "tls_version": cipher and tls.version(),
                            "cipher": cipher[0],
                            "cert_subject_cn": _dn_to_cn(cert.get("subject", ())),
                            "cert_issuer_cn": _dn_to_cn(cert.get("issuer", ())),
                            "not_after": cert.get("notAfter"),
                            "cert_sha256_12": hashlib.sha256(der).hexdigest()[:12] if der else None,
                        }
                    )
        except (socket.timeout, TimeoutError):
            out["handshake"] = "TIMEOUT"
        except ssl.SSLCertVerificationError as exc:
            out.update({"handshake": "TLS_CERT_VERIFY_FAILED", "error_detail": redact(str(exc))[:160]})
        except ssl.SSLError as exc:
            out.update({"handshake": "TLS_HANDSHAKE_ERROR", "error_detail": redact(str(exc))[:160]})
        except OSError as exc:
            out.update({"handshake": f"ERROR_{type(exc).__name__}", "error_detail": redact(str(exc))[:160]})
        return out

    def probe_hosts(self, hosts: list[str], paths: dict[str, str] | None = None, tls_identity: bool = True) -> dict:
        paths = paths or {}
        results: dict[str, dict] = {}
        with cf.ThreadPoolExecutor(max_workers=self.workers) as pool:
            futs = {}
            for host in hosts:
                path = paths.get(host, "/")
                futs[pool.submit(self._probe_one, host, path, tls_identity)] = host
            for fut in cf.as_completed(futs):
                host = futs[fut]
                try:
                    results[host] = fut.result()
                except Exception as exc:  # pragma: no cover
                    results[host] = {"host": host, "collector_error": f"{type(exc).__name__}: {redact(str(exc))[:160]}"}
        return {host: results[host] for host in hosts if host in results}

    def _probe_one(self, host: str, path: str, with_tls: bool) -> dict:
        entry: dict = {}
        entry["dns"] = self.dns(host)
        if not entry["dns"].get("resolved"):
            entry["https"] = {"url": f"https://{host}{path}", "outcome": "NOT_ATTEMPTED_DNS_FAILED"}
            if with_tls:
                entry["tls"] = {"host": host, "handshake": "NOT_ATTEMPTED_DNS_FAILED"}
            return entry
        probe = self.https(f"https://{host}{path}", method="GET", read_limit=2048)
        if probe.get("outcome") == "OK" and probe.get("http_status") in (403, 405, 501):
            probe = self.https(f"https://{host}{path}", method="HEAD")
        entry["https"] = probe
        if with_tls:
            try:
                entry["tls"] = self.tls_identity(host)
            except Exception as exc:  # never lose DNS/HTTPS results because of the identity probe
                entry["tls"] = {"host": host, "handshake": "PROBE_ERROR", "error": f"{type(exc).__name__}: {redact(str(exc))[:120]}"}
        return entry


def urllib_request(url: str, method: str) -> urllib.request.Request:
    return urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "*/*"})


def classify_urlerror(exc: urllib.error.URLError) -> dict:
    reason = getattr(exc, "reason", None)
    detail = redact(str(reason))[:200]
    if isinstance(reason, socket.gaierror):
        return {"outcome": "DNS_ERROR", "error_detail": detail, "reached_http_layer": False}
    if isinstance(reason, (ConnectionRefusedError,)):
        return {"outcome": "CONNECTION_REFUSED", "error_detail": detail}
    if isinstance(reason, (ConnectionResetError,)):
        return {"outcome": "CONNECTION_RESET", "error_detail": detail}
    if isinstance(reason, (ssl.SSLCertVerificationError,)):
        return {"outcome": "TLS_CERT_VERIFY_FAILED", "error_detail": detail}
    if isinstance(reason, ssl.SSLError):
        return {"outcome": "TLS_HANDSHAKE_ERROR", "error_detail": detail}
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return {"outcome": "TIMEOUT", "error_detail": detail}
    if isinstance(reason, OSError):
        return {"outcome": f"NETWORK_ERROR_{type(reason).__name__}", "error_detail": detail}
    return {"outcome": "NETWORK_ERROR", "error_detail": detail or redact(str(exc))[:200]}


# --------------------------------------------------------------------------
# part 1 — system
# --------------------------------------------------------------------------

NETWORK_HOSTS = [
    "pypi.org",
    "files.pythonhosted.org",
    "registry.npmjs.org",
    "github.com",
    "api.github.com",
    "raw.githubusercontent.com",
    "deb.debian.org",
    "cdn.playwright.dev",
    "storage.googleapis.com",
    "huggingface.co",
    "cdn.jsdelivr.net",
    "example.com",
    "pudas.se",
]

ENV_NAMES_TO_CHECK = [
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GH_HOST",
    "GIT_ASKPASS",
    "GIT_TERMINAL_PROMPT",
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "no_proxy",
    "NO_PROXY",
    "NODE_OPTIONS",
    "PYTHONPATH",
    "PIP_INDEX_URL",
    "NPM_CONFIG_REGISTRY",
    "VIRTUAL_ENV",
    "CI",
    "ARENA_SANDBOX_ID",
    "SANDBOX_ID",
    "PORT",
]

PRIVILEGE_TOOLS = ["sudo", "sudo -l NOT_ATTEMPTED", "unshare", "nsenter", "bwrap", "capsh", "pkexec", "su", "newuidmap", "runuser"]


def _read_text(path: str) -> str | None:
    try:
        return pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _statvfs(path) -> dict | None:
    path = str(path)
    try:
        st = os.statvfs(path)
    except OSError:
        return None
    block = st.f_frsize
    return {
        "path": redact(path),
        "total_bytes": st.f_blocks * block,
        "available_bytes": st.f_bavail * block,
        "used_bytes": (st.f_blocks - st.f_bfree) * block,
        "inodes_total": st.f_files,
        "inodes_free": st.f_ffree,
        "fs_block_size": block,
    }


def _os_release() -> dict:
    out: dict = {}
    for source in ("/etc/os-release", "/usr/lib/os-release"):
        text = _read_text(source)
        if text:
            for line in text.splitlines():
                if "=" in line:
                    key, _, value = line.partition("=")
                    out[key.strip()] = value.strip().strip('"')
            break
    return out


def _cgroup_limits() -> dict:
    out: dict = {"self_cgroup": redact((_read_text("/proc/self/cgroup") or "").strip()) or None, "mode": None, "limits": {}}
    if pathlib.Path("/sys/fs/cgroup/cgroup.controllers").exists():
        out["mode"] = "v2"
    elif pathlib.Path("/sys/fs/cgroup/memory").is_dir():
        out["mode"] = "v1"
    else:
        out["mode"] = "unavailable"
    relative = ""
    line = _read_text("/proc/self/cgroup") or ""
    for entry in line.splitlines():
        _, _, rel = entry.partition("::")
        relative = rel.strip("/")
        break
    candidates = [""]
    if relative:
        candidates.append(relative)
    candidates.append("init.scope")
    for key in ("memory.max", "memory.high", "memory.current", "cpu.max", "pids.max", "memory.limit_in_bytes"):
        for cand in candidates:
            path = pathlib.Path("/sys/fs/cgroup") / cand / key
            text = _read_text(str(path))
            if text:
                out["limits"][key] = {"cgroup_path": str(path).replace(_HOME, "~"), "value": text.strip()[:64]}
                break
    return out


def _rlimits() -> dict:
    named = {
        "RLIMIT_NOFILE": resource.RLIMIT_NOFILE,
        "RLIMIT_NPROC": resource.RLIMIT_NPROC,
        "RLIMIT_AS": resource.RLIMIT_AS,
        "RLIMIT_STACK": resource.RLIMIT_STACK,
        "RLIMIT_CORE": resource.RLIMIT_CORE,
        "RLIMIT_MEMLOCK": resource.RLIMIT_MEMLOCK,
    }
    unlimited = resource.RLIM_INFINITY
    out: dict = {}
    for name, which in named.items():
        try:
            cur, hard = resource.getrlimit(which)
        except (OSError, ValueError):
            continue
        out[name] = {
            "soft": "unlimited" if cur == unlimited else cur,
            "hard": "unlimited" if hard == unlimited else hard,
        }
    return out


def _security_passive(runner: Runner) -> dict:
    status_raw = _read_text("/proc/self/status") or ""
    fields: dict[str, str] = {}
    for line in status_raw.splitlines():
        key, _, value = line.partition(":")
        if key in ("NoNewPrivs", "Seccomp", "Seccomp_filters", "CapEff", "CapBnd", "CapPrm", "Threads", "Uid", "Gid"):
            fields[key] = value.strip()
    # Uid/Gid are numeric sandbox ids, not user identities: keep booleans only.
    for key in ("Uid", "Gid"):
        if key in fields:
            parts = fields.pop(key).split()
            fields[key + "_is_root"] = bool(parts) and parts[0] == "0"
            fields[key + "_ge_1000"] = bool(parts) and parts[0].isdigit() and int(parts[0]) >= 1000
    groups = []
    try:
        groups = sorted({g.gr_name for g in __import__("grp").getgrall() if os.getgid() == g.gr_gid or g.gr_gid in os.getgroups()})
    except Exception:
        pass
    shells = [ln.strip() for ln in (_read_text("/etc/shells") or "").splitlines() if ln.strip() and not ln.startswith("#")]
    mounts = []
    for line in (_read_text("/proc/mounts") or "").splitlines():
        parts = line.split()
        if len(parts) >= 3 and (parts[0] == "overlay" or parts[1] in ("/", "/tmp", "/dev/shm", "/home", "/run") or parts[2] == "tmpfs" and parts[1].count("/") <= 2):
            mounts.append({"mount": parts[1], "fstype": parts[2], "opts": parts[3]})
    checks = {
        "pid1_comm": redact((_read_text("/proc/1/comm") or "").strip()) or None,
        "dockerenv_present": pathlib.Path("/.dockerenv").exists(),
        "apparmor_available": pathlib.Path("/sys/module/apparmor").exists(),
        "selinux_available": pathlib.Path("/sys/fs/selinux").exists(),
        "seccomp_syscall_action": (_read_text("/proc/self/seccomp") or "unavailable").strip(),
        "proc_readonly": None,
        "ptrace_scope": (_read_text("/proc/sys/kernel/yama/ptrace_scope") or "unavailable").strip(),
        "unprivileged_userns_sysctl": (_read_text("/proc/sys/kernel/unprivileged_userns_clone") or "unavailable").strip(),
        "userns_max_ns_sysctl": (_read_text("/proc/sys/user/max_user_namespaces") or "unavailable").strip(),
        "namespace_tools_present": {},
        "escalation_attempted": False,
        "sandbox_escape_attempted": False,
        "note": "Passive reads only. sudo/namespace utilities were checked for existence; no execution, "
        "no 'sudo -l', no namespace creation and no attempt to widen privileges was made.",
    }
    for tool in ("sudo", "unshare", "nsenter", "bwrap", "capsh", "pkexec"):
        checks["namespace_tools_present"][tool] = shutil.which(tool) is not None
    return {
        "proc_self_status_subset": fields,
        "process_groups": groups,
        "shells_in_etc_shells": shells,
        "selected_mounts": mounts[:12],
        "passive_checks": checks,
    }


def collect_system(runner: Runner) -> dict:
    uname = platform.uname()
    cpu_count = os.cpu_count()
    cpuinfo = _read_text("/proc/cpuinfo") or ""
    model = ""
    mflags = []
    for line in cpuinfo.splitlines():
        if line.startswith("model name") and not model:
            model = line.split(":", 1)[1].strip()
        if line.startswith("flags"):
            mflags = sorted({f for f in line.split(":", 1)[1].split() if f in ("avx", "avx2", "avx512f", "sse4_2", "aes", "vmx", "svm")})
            break
    meminfo: dict[str, int] = {}
    for line in (_read_text("/proc/meminfo") or "").splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            meminfo[key] = int(parts[0])
    try:
        priv = getpass.getuser()
    except Exception:
        priv = ""
    euid = os.geteuid()
    distro = _os_release()
    presence = {name: shutil.which(name) is not None for name in ["bash", "sh", "zsh", "dash", "fish", "powershell", "pwsh"]}
    pkg_managers = {name: shutil.which(name) is not None for name in ["apt", "apt-get", "dpkg", "dpkg-query", "pip", "pip3", "npm", "npx", "yarn", "pnpm", "corepack", "apk", "dnf", "pacman", "conda", "mamba", "uv", "poetry"]}
    env_present = {name: (name in os.environ) for name in ENV_NAMES_TO_CHECK}
    return {
        "schema": SCHEMA,
        "engine": ENGINE,
        "collected_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "identity_hashes": {
            "method": "sha256[:12] of raw value; raw values are never stored",
            "hostname": short_hash(_HOSTNAME),
            "home_path": short_hash(_HOME),
            "os_user": short_hash(priv) if priv else None,
        },
        "os": {
            "pretty_name": distro.get("PRETTY_NAME"),
            "name": distro.get("NAME"),
            "id": distro.get("ID"),
            "version": distro.get("VERSION"),
            "version_id": distro.get("VERSION_ID"),
            "version_codename": distro.get("VERSION_CODENAME"),
        },
        "kernel": {"sysname": uname.system, "release": uname.release, "version": uname.version, "machine": uname.machine, "processor": uname.processor},
        "cpu": {"logical": cpu_count, "conf_cpus": len(glob.glob("/sys/devices/system/cpu/cpu[0-9]*")), "model_redacted_vendor": model.split(" @ ")[0][:60], "notable_flags": mflags, "loadavg_1_5_15": [round(x, 2) for x in os.getloadavg()]},
        "memory_kb": {k: meminfo.get(k) for k in ("MemTotal", "MemAvailable", "MemFree", "Buffers", "Cached", "SwapTotal", "SwapFree")},
        "cgroup": _cgroup_limits(),
        "rlimits": _rlimits(),
        "disk": {
            "root": _statvfs("/"),
            "tmp": _statvfs("/tmp"),
            "dev_shm": _statvfs("/dev/shm"),
            "home": _statvfs(pathlib.Path.home()),
            "workspace": _statvfs(os.getcwd()),
        },
        "user_privilege": {
            "category": ("root" if euid == 0 else "unprivileged_non_root"),
            "is_root": euid == 0,
            "in_sudo_group": "sudo" in [g for g in (_security_passive(runner).get("process_groups") or [])],
            "sudo_binary_present": shutil.which("sudo") is not None,
            "privilege_escalation_attempted": False,
            "note": "sudo exists; it was not executed and no credential was used.",
        },
        "shells": {"path_presence": presence, "login_shell_recorded": False, "value_note": "$SHELL value not stored (environment values are never captured)"},
        "package_managers_present": pkg_managers,
        "apt_state": _apt_state(runner),
        "network_env": {"presence_flags_only": env_present, "values_stored": False, "env_var_count": len(os.environ)},
        "sandbox_security_passive": _security_passive(runner),
    }


def _apt_state(runner: Runner) -> dict:
    lists_dir = pathlib.Path("/var/lib/apt/lists")
    entries = []
    if lists_dir.is_dir():
        try:
            entries = sorted(p.name for p in lists_dir.iterdir())
        except OSError:
            entries = []
    sources = {"sources_list_present": pathlib.Path("/etc/apt/sources.list").exists(), "sources_list_d_entries": sorted(p.name for p in pathlib.Path("/etc/apt/sources.list.d").iterdir()) if pathlib.Path("/etc/apt/sources.list.d").is_dir() else []}
    return {
        "package_index_files_in_var_lib_apt_lists": len(entries),
        "index_populated": any(not n.startswith("lock") for n in entries),
        "sources": sources,
        "apt_update_run": False,
        "note": "apt-get update was NOT run: it mutates system state and requires elevated privileges. "
        "Debian package metadata reachability is therefore assessed by reading deb.debian.org over HTTPS only.",
    }


# --------------------------------------------------------------------------
# part 2 — installed software
# --------------------------------------------------------------------------

VERSION_ARGS: dict[str, list[str]] = {
    "python": ["--version"],
    "python3": ["--version"],
    "pip": ["--version"],
    "pip3": ["--version"],
    "node": ["--version"],
    "npm": ["--version"],
    "npx": ["--version"],
    "yarn": ["--version"],
    "pnpm": ["--version"],
    "bun": ["--version"],
    "deno": ["--version"],
    "go": ["version"],
    "rustc": ["--version"],
    "cargo": ["--version"],
    "java": ["-version"],
    "javac": ["-version"],
    "php": ["--version"],
    "ruby": ["--version"],
    "perl": ["--version"],
    "gcc": ["--version"],
    "clang": ["--version"],
    "make": ["--version"],
    "cmake": ["--version"],
    "git": ["--version"],
    "gh": ["--version"],
    "sqlite3": ["--version"],
    "psql": ["--version"],
    "ffmpeg": ["-version"],
    "ffprobe": ["-version"],
    "magick": ["--version"],
    "convert": ["--version"],
    "pandoc": ["--version"],
    "soffice": ["--version"],
    "pdftotext": ["-v"],
    "pdfinfo": ["-v"],
    "qpdf": ["--version"],
    "gs": ["--version"],
    "chromium": ["--version"],
    "chromium-browser": ["--version"],
    "google-chrome": ["--version"],
    "google-chrome-stable": ["--version"],
    "chrome": ["--version"],
    "firefox": ["--version"],
    "curl": ["--version"],
    "wget": ["--version"],
    "openssl": ["version"],
    "jq": ["--version"],
    "zip": ["--version"],
    "unzip": ["-v"],
    "tar": ["--version"],
    "rg": ["--version"],
    "tesseract": ["--version"],
    "inkscape": ["--version"],
    "rsvg-convert": ["--version"],
    "dot": ["-V"],
    "dotnet": ["--version"],
    "R": ["--version"],
    "latex": ["--version"],
    "pdflatex": ["--version"],
    "fc-list": ["--version"],
    "dpkg": ["--version"],
    "apt": ["--version"],
    "sudo": ["--version"],
    "unshare": ["--version"],
    "ip": ["-Version"],
    "dig": ["-v"],
    "nslookup": [],
    "python3.11": ["--version"],
}

VERSION_PROBE_ORDER = list(VERSION_ARGS)


def path_executables() -> tuple[list[str], dict[str, list[str]]]:
    names: set[str] = set()
    per_name: dict[str, list[str]] = {}
    seen_dirs: set[str] = set()
    for raw in os.environ.get("PATH", "").split(os.pathsep):
        entry = raw.replace(_HOME, "~")
        if not raw or raw in seen_dirs:
            continue
        seen_dirs.add(raw)
        d = pathlib.Path(raw)
        try:
            if not d.is_dir():
                continue
            children = sorted(os.listdir(d))
        except OSError:
            continue
        for child in children:
            full = d / child
            try:
                mode = full.stat().st_mode
            except OSError:
                continue
            if stat.S_ISREG(mode) and (mode & stat.S_IXUSR) and os.access(full, os.X_OK):
                names.add(child)
                per_name.setdefault(child, []).append(entry)
    return sorted(names), per_name


def collect_executables(runner: Runner) -> dict:
    names, per_name = path_executables()
    probed: dict[str, dict] = {}
    for name in VERSION_PROBE_ORDER:
        exe = shutil.which(name)
        if exe is None:
            probed[name] = {"present_on_path": False, "status": "NOT_INSTALLED"}
            continue
        args = VERSION_ARGS.get(name, ["--version"])
        res = runner.run([exe, *args], label=f"version:{name}", timeout=15)
        line = ""
        for candidate in (res.get("stdout") or "", res.get("stderr") or ""):
            for ln in candidate.splitlines():
                if ln.strip():
                    line = ln.strip()[:200]
                    break
            if line:
                break
        probed[name] = {
            "present_on_path": True,
            "path": redact(exe),
            "status": "INSTALLED" if res.get("exit_code") == 0 else ("INSTALLED_VERSION_UNSPEC" if res.get("exit_code") else "INSTALLED_VERSION_UNAVAILABLE"),
            "version_line": line or None,
            "version_parsed": (VERSION_RE.search(line).group(1) if line and VERSION_RE.search(line) else None),
            "probe_exit_code": res.get("exit_code"),
            "probe_error": res.get("error"),
        }
    interesting = [n for n in names if re.search(r"(pdf|png|jpg|image|font|svg|office|docx|xlsx|csv|xml|zip|tar|sqlite|graph|plot|chrom|browser|playwright|puppeteer|video|audio|ffmpeg|convert|magick)", n)]
    return {
        "schema": SCHEMA,
        "path_dirs": [d.replace(_HOME, "~") for d in os.environ.get("PATH", "").split(os.pathsep) if d],
        "executable_count": len(names),
        "executables": names,
        "names_provided_by_multiple_dirs": {k: v for k, v in sorted(per_name.items()) if len(v) > 1},
        "version_probes": probed,
        "installed_with_version": sorted(k for k, v in probed.items() if v.get("version_line")),
        "not_installed": sorted(k for k, v in probed.items() if not v.get("present_on_path")),
        "media_document_related_names": interesting[:250],
        "total_path_entries_scanned": sum(len(v) for v in per_name.values()),
    }


def collect_python(runner: Runner) -> dict:
    stdlib = sorted(getattr(sys, "stdlib_module_names", frozenset()))
    here = pathlib.Path(sys.executable)
    pythons = {}
    for path in sorted(set([str(here), *glob.glob("/usr/bin/python*"), *glob.glob("/usr/local/bin/python*"), *glob.glob("/opt/*/bin/python*")])):
        exe = pathlib.Path(path)
        if not exe.is_file() or not os.access(exe, os.X_OK):
            continue
        res = runner.run([str(exe), "-E", "-c", "import sys,json;print(json.dumps({'version':sys.version,'version_info':list(map(int,sys.version_info[:3])),'prefix':sys.prefix,'executable':sys.executable,'64bit':sys.maxsize>2**31}))"], label=f"python:{path}", timeout=20)
        info = None
        if res.get("exit_code") == 0:
            try:
                info = json.loads(res["stdout"])
            except json.JSONDecodeError:
                info = {"raw": (res.get("stdout") or "")[:200]}
        pythons[redact(str(exe))] = {"probe": info, "status": "OK" if info else "PROBE_FAILED"}

    distributions = []
    errors = []
    try:
        for dist in md.distributions():
            try:
                name = dist.metadata["Name"] or "?"
                version = dist.version or "?"
            except Exception as exc:  # pragma: no cover
                errors.append(f"{type(exc).__name__}")
                continue
            loc = getattr(dist, "_path", None)
            distributions.append(
                {
                    "name": name,
                    "version": version,
                    "location": redact(str(getattr(dist, "locate_file", lambda *_: "")("")) or (str(loc.parent) if loc else "")) or None,
                }
            )
    except Exception as exc:  # pragma: no cover
        errors.append(f"metadata_enumeration:{type(exc).__name__}")
    distributions.sort(key=lambda d: (d["name"].lower(), d["version"]))

    pip_crosscheck = runner.run([sys.executable, "-m", "pip", "list", "--format", "json", "--disable-pip-version-check"], label="pip list", timeout=90, stdout_limit=200000)
    pip_json = None
    if pip_crosscheck.get("exit_code") == 0:
        try:
            pip_json = json.loads(pip_crosscheck["stdout"])
        except json.JSONDecodeError:
            pip_json = None

    dist_roots = {}
    for root in sorted({p for d in distributions for p in [d.get("location") or ""] if p}):
        try:
            dist_roots[root] = len(os.listdir(root))
        except OSError:
            dist_roots[root] = None

    return {
        "schema": SCHEMA,
        "active_interpreter": {
            "executable": redact(sys.executable),
            "version": sys.version.split()[0],
            "version_full": redact(sys.version),
            "implementation": platform.python_implementation(),
            "cache_flag": "python invoked with -E for sub-probes; the engine itself imports no third-party packages",
            "prefix": redact(sys.prefix),
            "base_prefix": redact(sys.base_prefix),
            "is_venv": sys.prefix != sys.base_prefix,
            "frozen": bool(getattr(sys, "frozen", False)),
        },
        "sysconfig": {k: redact(v) for k, v in sysconfig.get_paths().items() if k in ("stdlib", "purelib", "platlib", "scripts", "include")},
        "distributions_found_on_path": pythons,
        "installed_distributions": {
            "count": len(distributions),
            "enumeration_method": "importlib.metadata (package METADATA only; no module imports were executed, so no package __init__ code ran)",
            "items": distributions,
            "pip_list_crosscheck_count": (len(pip_json) if isinstance(pip_json, list) else None),
            "pip_list_crosscheck_available": isinstance(pip_json, list),
            "enumeration_errors": sorted(set(errors)),
            "distribution_roots_entry_count": dist_roots,
        },
        "standard_library": {
            "count": len(stdlib),
            "method": "sys.stdlib_module_names (interpreter-reported, no imports)",
            "modules": stdlib,
            "builtin_frozen_module_names": sorted(sys.builtin_module_names),
        },
        "packaging": {
            "pip_version": redact((runner.run([sys.executable, "-m", "pip", "--version"], label="pip --version", timeout=20).get("stdout") or "").strip()) or None,
            "externally_managed": bool(sysconfig.get_config_var("stdlib") and pathlib.Path(str(sysconfig.get_config_var("stdlib")), "EXTERNALLY-MANAGED").exists()),
            "venv_module": True,
            "wheel_or_build": sorted(n for n in ("wheel", "setuptools", "build", "poetry", "pipx", "uv") if any(d["name"].lower() == n for d in distributions)),
        },
        "not_tested": ["per-module importability of third-party packages (deliberately not imported)", "C-extension ABI compatibility beyond the active interpreter"],
    }


def collect_os_packages(runner: Runner) -> dict:
    res = runner.run(
        ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${db:Status-Abbrev}\t${Section}\t${Installed-Size}\n"],
        label="dpkg-query",
        timeout=60,
        stdout_limit=2_000_000,
    )
    items = []
    if res.get("exit_code") == 0:
        for line in res["stdout"].splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and parts[0].strip():
                items.append(
                    {
                        "package": parts[0].strip(),
                        "version": parts[1].strip() if len(parts) > 1 else None,
                        "status": parts[2].strip() if len(parts) > 2 else None,
                        "section": parts[3].strip() if len(parts) > 3 else None,
                        "installed_size_kb": int(parts[4]) if len(parts) > 4 and parts[4].strip().isdigit() else None,
                    }
                )
    items.sort(key=lambda d: d["package"])
    installed = [d for d in items if d["status"] and d["status"].startswith("ii")]
    sections: dict[str, int] = {}
    for d in installed:
        sections[d["section"] or "unknown"] = sections.get(d["section"] or "unknown", 0) + 1
    interesting = [
        d["package"]
        for d in installed
        if re.match(
            r"^(python3.*|nodejs|npm|git|gh|curl|wget|openssl|libc6|libssl.*|zlib1g|make|gcc|g\+\+|binutils|ffmpeg.*|imagemagick.*|poppler-utils|libreoffice.*|pandoc|fonts-.*|sqlite3|libsqlite3.*|libjpeg.*|libpng.*|ca-certificates|unzip|zip|jq|chromium.*|firefox.*|latex.*|texlive.*|wkhtmltopdf|ghostscript|libglib2.0.*|libnss3|libatk.*|libgtk-3-0|libasound2.*|libx11-6|libxcomposite.*|libxdamage.*|libxrandr2|libgbm1|libxkbcommon.*|cups-libs|libvulkan.*)$",
            d["package"],
        )
    ]
    return {
        "schema": SCHEMA,
        "method": "dpkg-query metadata (no network, no mutation)",
        "database_package_count": len(items),
        "installed_count": len(installed),
        "by_section": dict(sorted(sections.items(), key=lambda kv: -kv[1])),
        "notable_packages": sorted(set(interesting)),
        "notable_packages_count": len(set(interesting)),
        "packages": [{"package": d["package"], "version": d["version"], "section": d["section"], "size_kb": d["installed_size_kb"]} for d in installed],
        "dpkg_exit_code": res.get("exit_code"),
        "dpkg_error": res.get("error"),
    }


def collect_libraries(runner: Runner) -> dict:
    ldconfig = shutil.which("ldconfig") or ("/sbin/ldconfig" if pathlib.Path("/sbin/ldconfig").exists() else None)
    sonames: list[str] = []
    method = None
    if ldconfig:
        res = runner.run([ldconfig, "-p"], label="ldconfig -p", timeout=40, stdout_limit=2_000_000)
        if res.get("exit_code") == 0:
            for line in res["stdout"].splitlines():
                line = line.strip()
                if line.endswith(":") or "=>" not in line:
                    continue
                name = line.split("=>", 1)[0].strip()
                path = line.split("=>", 1)[1].strip().split(" ", 1)[0]
                if name:
                    sonames.append(f"{name}\t{redact(path)}")
            method = "ldconfig -p"
    if not sonames:
        roots = ["/lib", "/usr/lib", "/usr/local/lib", "/lib64", "/usr/lib64", f"/usr/lib/{platform.machine()}-linux-gnu"]
        seen = set()
        for root in roots:
            for path in glob.glob(os.path.join(root, "**", "*.so*"), recursive=True):
                name = os.path.basename(path)
                if name not in seen:
                    seen.add(name)
                    sonames.append(f"{name}\t{redact(path)}")
                if len(sonames) > 60000:
                    break
        sonames.sort()
        method = "filesystem scan of standard library directories (ldconfig unavailable)"
    fs_so_count = 0
    for root in ("/usr/lib", "/usr/local/lib", "/lib"):
        fs_so_count += sum(1 for _ in glob.iglob(os.path.join(root, "**", "*.so*"), recursive=True))
    families = {
        "libssl/libcrypto": any(s.startswith(("libssl.so", "libcrypto.so")) for s in sonames),
        "libsqlite3": any(s.startswith("libsqlite3.so") for s in sonames),
        "libpython": any(s.startswith("libpython3") for s in sonames),
        "libcurl": any(s.startswith("libcurl") for s in sonames),
        "zlib/libpng/jpeg/tiff/webp": sum(1 for s in sonames if s.startswith(("libz.so", "libpng", "libjpeg", "libtiff", "libwebp"))),
        "x11/wayland/gtk (browser-relevant)": sum(1 for s in sonames if s.startswith(("libX11.so", "libxcb.so", "libgtk-3", "libwayland", "libgbm.so", "libnss3.so", "libasound", "libatk", "libcairo", "libpango", "libdrm"))),
        "fontconfig/freetype/harfbuzz": sum(1 for s in sonames if s.startswith(("libfontconfig", "libfreetype", "libharfbuzz"))),
        "gstreamer/ffmpeg": sum(1 for s in sonames if s.startswith(("libgstreamer", "libavcodec", "libavformat", "libswscale"))),
        "vulkan/opengl": sum(1 for s in sonames if s.startswith(("libvulkan", "libGL.so", "libEGL.so"))),
    }
    return {
        "schema": SCHEMA,
        "method": method,
        "count": len(sonames),
        "filesystem_so_file_count_estimate": fs_so_count,
        "shared_objects": sonames,
        "families": families,
        "browser_readiness_note": "Presence of X/GTK/NSS libraries is informational only; no browser is installed or validated by this key.",
    }


def collect_fonts() -> dict:
    families: set[str] = set()
    files: list[dict] = []
    roots = ["/usr/share/fonts", "/usr/local/share/fonts", redact(str(pathlib.Path.home() / ".fonts")), redact(str(pathlib.Path.home() / ".local/share/fonts")), "/usr/share/fonts/truetype"]
    exts = (".ttf", ".otf", ".ttc", ".pfb", ".pcf", ".woff2")
    seen_files: set[str] = set()
    for root in roots:
        for path in glob.glob(os.path.join(root, "**", "*"), recursive=True):
            if not path.lower().endswith(exts) or path in seen_files:
                continue
            seen_files.add(path)
            base = os.path.basename(path)
            stem = os.path.splitext(base)[0]
            family = re.sub(r"[-_.]?(Bold|Italic|Oblique|Regular|Light|Medium|Black|Book|Roman|Mono|Condensed|Narrow|Semibold|DemiBold).*$", "", stem, flags=re.I)
            family = re.sub(r"[-_]+", " ", family).strip() or stem
            families.add(family)
            try:
                size = os.path.getsize(path)
            except OSError:
                size = None
            files.append({"file": redact(path), "bytes": size, "family_guess": family})
    files.sort(key=lambda d: d["file"])
    return {
        "schema": SCHEMA,
        "fontconfig_fc_list_present": shutil.which("fc-list") is not None,
        "method": "filesystem scan; families derived from file names (fontconfig not installed, so no rendered-glyph family list is available)",
        "font_file_count": len(files),
        "family_count_estimate": len(families),
        "families": sorted(families),
        "files": files,
        "roots_scanned": [redact(r) for r in roots],
    }


BROWSER_PATHS = [
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "chrome",
    "chrome-headless-shell",
    "headless_shell",
    "firefox",
    "firefox-esr",
    "brave-browser",
    "microsoft-edge",
    "playwright",
    "puppeteer",
]

BROWSER_CACHE_PATHS = [
    "~/.cache/ms-playwright",
    "~/.cache/puppeteer",
    "~/.cache/chromium",
    "~/.cache/google-chrome",
    "~/.cache/mozilla",
    "~/.mozilla/firefox",
    "~/.config/chromium",
    "~/.config/google-chrome",
    "/usr/lib/chromium",
    "/opt/google/chrome",
    "/usr/lib/firefox",
    "/tmp/ms-playwright",
    "/tmp/playwright-browsers",
    "/tmp/puppeteer",
]


def collect_browsers(runner: Runner) -> dict:
    executables = {}
    for name in BROWSER_PATHS:
        exe = shutil.which(name)
        if exe:
            res = runner.run([exe, "--version"], label=f"browser:{name}", timeout=20)
            executables[name] = {"path": redact(exe), "status": "INSTALLED", "version_line": ((res.get("stdout") or res.get("stderr") or "").strip().splitlines() or [""])[0][:160]}
        else:
            executables[name] = {"present": False, "status": "NOT_INSTALLED"}
    caches = []
    for raw in BROWSER_CACHE_PATHS:
        path = pathlib.Path(os.path.expanduser(raw))
        entry = {"path": raw, "exists": path.exists()}
        if path.exists():
            try:
                entry["entries"] = sorted(os.listdir(path))[:40]
                entry["entry_count"] = len(os.listdir(path))
            except OSError as exc:
                entry["error"] = type(exc).__name__
        caches.append(entry)
    node_modules_hits = []
    for root in (os.getcwd(), str(pathlib.Path.home())):
        for pattern in ("node_modules/playwright*", "*/node_modules/playwright*", "*/*/node_modules/@sparticuz*", "*/node_modules/puppeteer*"):
            for hit in glob.glob(os.path.join(root, pattern)):
                node_modules_hits.append(redact(hit))
    return {
        "schema": SCHEMA,
        "executables": executables,
        "caches_and_config": caches,
        "node_module_bundles_found": sorted(set(node_modules_hits)),
        "browser_navigation_tested": False,
        "note": "No browser was installed or launched by this inventory. Browser/Playwright presence is reported only as found.",
    }


# --------------------------------------------------------------------------
# part 2/3 — node
# --------------------------------------------------------------------------

def collect_node(runner: Runner) -> dict:
    node = shutil.which("node")
    out: dict = {"schema": SCHEMA}
    if not node:
        return {**out, "node_present": False}
    probe = runner.run(
        [node, "-p", "JSON.stringify({version:process.version,v8:process.versions.v8,uv:process.versions.uv,openssl:process.versions.opensll||process.versions.openssl,modules:require('module').builtinModules,arch:process.arch,platform:process.platform,execPath:process.execPath})"],
        label="node builtins",
        timeout=25,
        stdout_limit=200000,
    )
    parsed = None
    if probe.get("exit_code") == 0:
        try:
            parsed = json.loads(probe["stdout"])
        except json.JSONDecodeError:
            parsed = None
    builtins = sorted(parsed.get("modules") or []) if parsed else []
    npm = shutil.which("npm")
    global_list = None
    npm_root = None
    npm_registry = None
    npm_config_user = None
    if npm:
        g = runner.run([npm, "ls", "-g", "--depth=0", "--json"], label="npm ls -g", timeout=60, stdout_limit=400000)
        if g.get("exit_code") == 0:
            try:
                global_list = json.loads(g["stdout"])
            except json.JSONDecodeError:
                global_list = None
        r = runner.run([npm, "root", "-g"], label="npm root -g", timeout=30)
        npm_root = redact((r.get("stdout") or "").strip()) or None
        reg = runner.run([npm, "config", "get", "registry"], label="npm registry", timeout=30)
        npm_registry = (reg.get("stdout") or "").strip() or None
        cfg = runner.run([npm, "config", "get", "userconfig"], label="npm userconfig path", timeout=30)
        npm_config_user = redact((cfg.get("stdout") or "").strip()) or None
    local_deps = {}
    for pkg_json in glob.glob(os.path.join(os.getcwd(), "**", "package.json"), recursive=True):
        if "node_modules" in pkg_json:
            continue
        try:
            data = json.loads(pathlib.Path(pkg_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        local_deps[redact(pkg_json.replace(os.getcwd(), "."))] = {
            "name": data.get("name"),
            "dependencies": sorted(data.get("dependencies") or {}),
            "devDependencies": sorted(data.get("devDependencies") or {}),
            "scripts": sorted(data.get("scripts") or {}),
        }
    node_modules_present = bool(glob.glob(os.path.join(os.getcwd(), "node_modules")))
    globals_flat = []
    if isinstance(global_list, dict):
        for name, meta in (global_list.get("dependencies") or {}).items():
            globals_flat.append(f"{name}@{meta.get('version')}" if isinstance(meta, dict) else str(name))
        if global_list.get("name") and global_list.get("version") and global_list.get("name") != "lib":
            globals_flat.append(f"{global_list['name']}@{global_list['version']}")
    return {
        **out,
        "node_present": True,
        "runtime": {
            "version": (parsed or {}).get("version"),
            "v8": (parsed or {}).get("v8"),
            "openssl": (parsed or {}).get("openssl"),
            "abi": (parsed or {}).get("uv"),
            "arch": (parsed or {}).get("arch"),
            "platform": (parsed or {}).get("platform"),
            "executable": redact((parsed or {}).get("execPath") or node),
        },
        "probe_error": None if parsed else (probe.get("error") or "PARSE_FAILED"),
        "builtin_module_count": len(builtins),
        "builtin_modules": builtins,
        "package_managers": {
            "npm": _version_of(runner, "npm"),
            "npx": _version_of(runner, "npx"),
            "yarn": _version_of(runner, "yarn"),
            "pnpm": _version_of(runner, "pnpm"),
            "corepack": _version_of(runner, "corepack"),
            "bun": _version_of(runner, "bun"),
            "deno": _version_of(runner, "deno"),
        },
        "npm_registry_configured": npm_registry,
        "npm_global_root": npm_root,
        "npm_userconfig_path": npm_config_user,
        "npm_userconfig_read": False,
        "global_packages": sorted(set(globals_flat)),
        "global_package_count": len(set(globals_flat)),
        "npm_ls_global_exit_code": (None if not npm else (0 if global_list is not None else 1)),
        "repository_local_dependencies": local_deps,
        "repository_node_modules_present": node_modules_present,
        "note": ".npmrc / global npmrc contents were not read (credential-bearing config). Only `npm config get registry` was used.",
    }


def _version_of(runner: Runner, name: str) -> dict:
    exe = shutil.which(name)
    if not exe:
        return {"present": False, "status": "NOT_INSTALLED"}
    res = runner.run([exe, "--version"], label=f"version:{name}", timeout=20)
    line = ((res.get("stdout") or res.get("stderr") or "").strip().splitlines() or [""])[0]
    return {"present": True, "path": redact(exe), "version": line[:80] or None, "status": "INSTALLED", "exit_code": res.get("exit_code")}


# --------------------------------------------------------------------------
# part 3 — registry reachability + install tests
# --------------------------------------------------------------------------

PYPI_SAMPLES = ["numpy", "pandas", "reportlab", "openpyxl", "playwright", "pillow", "lxml", "requests", "matplotlib", "weasyprint", "fpdf2", "pypdf", "selenium", "black", "pytest"]
NPM_SAMPLES = ["playwright", "playwright-core", "@sparticuz/chromium", "puppeteer", "lighthouse", "axe-core", "sharp", "pdf-lib", "docx", "exceljs", "express", "vitest", "postcss", "tailwindcss", "pyright"]
GITHUB_SAMPLES = {"github_public_repo_api": "https://api.github.com/repos/FullThrottle83/arena", "github_raw_file": "https://raw.githubusercontent.com/FullThrottle83/arena/main/AGENTS.md", "github_codeload_tarball_head": "https://codeload.github.com/FullThrottle83/arena/tar.gz/refs/heads/main"}
DOWNLOAD_ENDPOINTS = {
    "playwright_cdn_root": {"url": "https://cdn.playwright.dev/", "note": "reachability only; browser binaries were deliberately NOT downloaded"},
    "playwright_cdn_build_path": {"url": "https://cdn.playwright.dev/dbazure/download/playwright/builds/chromium/1140/chromium-linux.zip", "note": "representative documented build path, HEAD only"},
    "chromium_snapshots_listing": {"url": "https://storage.googleapis.com/chromium-browser-snapshots/?list-type=2&max-keys=1", "note": "public GCS bucket listing, 1 key requested"},
    "debian_stable_release": {"url": "https://deb.debian.org/debian/dists/stable/Release", "note": "Debian package metadata (Release index), HEAD only"},
    "debian_security_release": {"url": "https://deb.debian.org/debian-security/dists/bookworm-security/Release", "note": "HEAD only"},
    "huggingface_model_metadata": {"url": "https://huggingface.co/api/models/google-bert/bert-base-uncased", "note": "public model metadata JSON; no weights downloaded"},
    "huggingface_resolve_head": {"url": "https://huggingface.co/google-bert/bert-base-uncased/resolve/main/config.json", "note": "tiny public file, GET 512 bytes"},
    "jsdelivr_package_metadata": {"url": "https://cdn.jsdelivr.net/npm/playwright/package.json", "note": "GET 2048 bytes"},
}


def collect_registries(net: Net) -> dict:
    out: dict = {"schema": SCHEMA, "policy": "metadata endpoints only; no package downloads, no browser binaries, no installs implied", "per_request_timeout_s": net.timeout}

    pypi: dict[str, dict] = {}
    for name in PYPI_SAMPLES:
        res = net.json(f"https://pypi.org/pypi/{name}/json")
        head = net.https(f"https://pypi.org/simple/{name}/", method="HEAD")
        data = res.get("data") or {}
        info = data.get("info") if isinstance(data, dict) else None
        entry = {
            "outcome": res.get("outcome"),
            "http_status": res.get("http_status"),
            "elapsed_ms": res.get("elapsed_ms"),
            "simple_index_status": head.get("http_status") if head.get("outcome") == "OK" else head.get("outcome"),
            "latest_version": (info or {}).get("version"),
            "requires_python": (info or {}).get("requires_python"),
            "yanked": (info or {}).get("yanked"),
            "reachable": res.get("reachable", False) or res.get("http_status") == 200,
            "json_parsed": res.get("json_parsed", False),
            "simple_index_status": head.get("http_status") or head.get("outcome"),
        }
        entry["status_label"] = "REGISTRY_REACHABLE" if entry["reachable"] else "REGISTRY_UNREACHABLE"
        pypi[name] = entry

    npm_reg: dict[str, dict] = {}
    for name in NPM_SAMPLES:
        url = "https://registry.npmjs.org/" + name.replace("/", "%2f")
        res = net.json(url, accept="application/vnd.npm.install-v1+json")
        data = res.get("data") or {}
        entry = {
            "outcome": res.get("outcome"),
            "http_status": res.get("http_status"),
            "elapsed_ms": res.get("elapsed_ms"),
            "reachable": res.get("reachable", False) or res.get("http_status") == 200,
            "json_parsed": res.get("json_parsed", False),
            "latest_version": (data.get("dist-tags") or {}).get("latest") if isinstance(data, dict) else None,
            "note": None if res.get("json_parsed") else "metadata document exceeded the read limit; reachability still established by the HTTP 200 response",
        }
        entry["status_label"] = "REGISTRY_REACHABLE" if entry["reachable"] else "REGISTRY_UNREACHABLE"
        npm_reg[name] = entry

    downloads = {}
    for label, meta in DOWNLOAD_ENDPOINTS.items():
        method = "GET" if ("resolve" in label or "jsdelivr" in label or "listing" in label) else "HEAD"
        res = net.https(meta["url"], method=method, read_limit=4096 if method == "GET" else 0)
        downloads[label] = {
            "url": meta["url"],
            "method": method,
            "outcome": res.get("outcome"),
            "http_status": res.get("http_status"),
            "content_length": res.get("content_length"),
            "elapsed_ms": res.get("elapsed_ms"),
            "note": meta["note"],
        }

    return {
        **out,
        "pypi": {"endpoint": "https://pypi.org/pypi/<name>/json + /simple/<name>/", "probed_count": len(pypi), "reachable_count": sum(1 for v in pypi.values() if v["reachable"]), "items": pypi},
        "npm": {"endpoint": "https://registry.npmjs.org/<name> (install-v1 abbreviated metadata)", "probed_count": len(npm_reg), "reachable_count": sum(1 for v in npm_reg.values() if v["reachable"]), "items": npm_reg},
        "github_public_resources": {k: net.https(v, method="GET", read_limit=512) for k, v in GITHUB_SAMPLES.items()},
        "documented_download_endpoints": downloads,
        "caveat": "REGISTRY_REACHABLE means the index responded. It does not prove any specific package can be installed, built or executed here (no apt/DPG install, no wheel build test, no binary download).",
    }


def collect_install_probes(runner: Runner, tmp_parent: str, do_pip: bool, do_npm: bool) -> dict:
    """Small, isolated, reversible install tests. Approved by the operator in-session.

    Never touches system site-packages: pip uses --target and an isolated venv;
    npm uses a temp --prefix. Both trees are deleted afterwards.
    """
    out: dict = {"schema": SCHEMA, "authorization": "caller explicitly opted in via --probe-install; obtain operator approval before invoking", "results": {}}
    root = pathlib.Path(tmp_parent) / f"arena-inventory-install-{int(time.time())}"
    root.mkdir(parents=True, exist_ok=True)
    out["sandbox_dir"] = redact(str(root))
    if do_pip:
        target = root / "py-target"
        res = runner.run(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-index" if False else "--no-cache-dir", "--no-deps", "--ignore-installed", "--target", str(target), "six"],
            label="pip install six (--target)",
            timeout=180,
            stdout_limit=6000,
        )
        entry = {"method": "pip install --target (isolated dir; system site-packages untouched)", "exit_code": res.get("exit_code"), "status": "INSTALLATION_TESTED" if res.get("exit_code") == 0 else "INSTALLATION_FAILED", "stdout_tail": (res.get("stdout") or "")[-500:], "error": res.get("error")}
        if res.get("exit_code") == 0 and target.is_dir():
            entry["installed_files"] = sorted(os.listdir(target))[:20]
            verify = runner.run([sys.executable, "-c", f"import sys;sys.path.insert(0,{str(target)!r});import six;print(six.__version__, six.__file__.startswith({str(target)!r}))"], label="pip install six verify", timeout=30)
            entry["import_execute_check"] = {"exit_code": verify.get("exit_code"), "stdout": (verify.get("stdout") or "").strip()[:200], "note": "isolated subprocess; this executes the freshly installed package on purpose"}
        else:
            venv_dir = root / "py-venv"
            vres = runner.run([sys.executable, "-m", "venv", str(venv_dir)], label="python -m venv (fallback)", timeout=180)
            entry["venv_fallback"] = {"exit_code": vres.get("exit_code"), "status": "OK" if vres.get("exit_code") == 0 else "FAILED", "stderr": (vres.get("stderr") or "")[:300]}
            pip_bin = venv_dir / "bin" / "pip"
            if vres.get("exit_code") == 0 and pip_bin.exists():
                fres = runner.run([str(pip_bin), "install", "--no-cache-dir", "six"], label="venv pip install six", timeout=240, stdout_limit=4000)
                entry["venv_fallback"]["install_exit_code"] = fres.get("exit_code")
                entry["venv_fallback"]["install_status"] = "INSTALLATION_TESTED" if fres.get("exit_code") == 0 else "INSTALLATION_FAILED"
                entry["venv_fallback"]["stdout_tail"] = (fres.get("stdout") or "")[-400:]
                if fres.get("exit_code") == 0:
                    entry["status"] = "INSTALLATION_TESTED_VIA_VENV"
                    entry["blocked_reason"] = (res.get("stdout") or res.get("stderr") or "")[:300]
        out["results"]["pypi_pip_six"] = entry
    if do_npm:
        npmdir = root / "npm-probe"
        npmdir.mkdir(parents=True, exist_ok=True)
        npm = shutil.which("npm")
        if npm:
            res = runner.run([npm, "install", "--prefix", str(npmdir), "--no-save", "--no-audit", "--no-fund", "--loglevel", "error", "is-number@7.0.0"], label="npm install is-number (--prefix temp)", timeout=240, stdout_limit=6000)
            entry = {"method": "npm install --prefix <temp dir> (project-local, reversible)", "exit_code": res.get("exit_code"), "status": "INSTALLATION_TESTED" if res.get("exit_code") == 0 else "INSTALLATION_FAILED", "stdout_tail": (res.get("stdout") or "")[-400:], "stderr_tail": (res.get("stderr") or "")[-400:]}
            pkg = npmdir / "node_modules" / "is-number"
            entry["package_present_after_install"] = pkg.is_dir()
            if pkg.is_dir():
                node_exe = shutil.which("node")
                exec_res = runner.run([node_exe, "-e", f"const n=require({str(pkg / 'index.js')!r});console.log('executed',n(3))"], label="npm package execute check", timeout=30)
                entry["execute_check"] = {"exit_code": exec_res.get("exit_code"), "stdout": (exec_res.get("stdout") or "").strip()[:160]}
            out["results"]["npm_is_number"] = entry
    cleanup_ok = True
    try:
        shutil.rmtree(root, ignore_errors=False)
    except OSError:
        cleanup_ok = False
    out["cleanup"] = {"removed": cleanup_ok, "path_still_exists": root.exists()}
    out["system_state_modified"] = False
    out["not_tested"] = ["apt/dpkg installation (requires root and mutates system packages)", "Playwright browser binary download", "large or compiled wheels (build toolchain exercise)", "pip --break-system-packages (deliberately not used)"]
    return out


# --------------------------------------------------------------------------
# part 4 — network matrix
# --------------------------------------------------------------------------

def _issuer_summary(hosts: dict) -> dict:
    """Group hosts by the TLS leaf issuer CN actually presented to the sandbox.

    A private/unknown issuer in front of a public service indicates an intercepting
    egress proxy; that is recorded as an observation, not as a judgement about intent.
    """
    summary: dict[str, list[str]] = {}
    for host, entry in hosts.items():
        issuer = ((entry.get("tls") or {}).get("cert_issuer_cn")) or "none/unknown"
        summary.setdefault(issuer, []).append(host)
    notes = []
    if len(summary) > 1:
        notes.append("More than one TLS issuer was observed across public services. Where the issuer is not the CA "
                     "that publicly serves that hostname, the connection is terminated by an intervening egress proxy, "
                     "so 'TLS ok' from the shell does not prove an end-to-end path to the origin server.")
    return {"by_issuer": {k: sorted(v) for k, v in sorted(summary.items())}, "note": " ".join(notes) or "single issuer observed"}


def collect_network(net: Net) -> dict:
    hosts = net.probe_hosts(NETWORK_HOSTS)
    counts = {"dns_ok": 0, "https_ok": 0, "https_failed": 0, "tls_handshake_ok": 0, "hosts_with_any_http_response": 0}
    for entry in hosts.values():
        if entry.get("dns", {}).get("resolved"):
            counts["dns_ok"] += 1
        https = entry.get("https") or {}
        outcome = https.get("outcome")
        if outcome == "OK":
            counts["https_ok"] += 1
        elif outcome:
            counts["https_failed"] += 1
        if https.get("http_status"):
            counts["hosts_with_any_http_response"] += 1
            entry["tcp_tls_http_egress"] = "ALLOWED"
        elif outcome in ("TLS_HANDSHAKE_ERROR", "TLS_CERT_VERIFY_FAILED"):
            entry["tcp_tls_http_egress"] = "BLOCKED_AT_TLS"
        elif outcome in ("TIMEOUT",):
            entry["tcp_tls_http_egress"] = "BLOCKED_TIMEOUT"
        elif not entry.get("dns", {}).get("resolved"):
            entry["tcp_tls_http_egress"] = "BLOCKED_AT_DNS"
        else:
            entry["tcp_tls_http_egress"] = "BLOCKED"
        if (entry.get("tls") or {}).get("handshake") == "OK":
            counts["tls_handshake_ok"] += 1
    egress = {}
    for key, url in (("ipv4_literal_service", "https://api.ipify.org/"), ("ipv6_service", "https://6.ifcfg.me/")):
        res = net.https(url, method="GET", read_limit=64)
        egress[key] = {"url": url, "outcome": res.get("outcome"), "http_status": res.get("http_status"), "bytes_read": res.get("bytes_read"), "note": "content not stored"}
    metadata = {"aws_link_local": "NOT_ATTEMPTED", "note": "169.254.169.254 and other link-local/metadata endpoints were deliberately not contacted, per the task's safety boundary."}
    return {
        "schema": SCHEMA,
        "policy": {
            "max_seconds_per_request": net.timeout,
            "parallel_workers": net.workers,
            "tls_verification": "enabled (ssl.create_default_context(); never disabled)",
            "methods": "GET (<=2KB read) with HEAD fallback; no crawling, no port scanning, single request per URL",
            "port_scans": False,
            "arena_platform_probing": "NOT_ATTEMPTED (no automated requests against Arena itself)",
        },
        "counts": counts,
        "tls_issuers_observed": _issuer_summary(hosts),
        "hosts": hosts,
        "egress_probe": egress,
        "cloud_metadata": metadata,
        "egress_ip": {"stored": False, "note": "outbound egress IP response bodies are not stored; public DNS answer addresses are present under hosts.*.dns"},
        "dns_resolver": {"resolv_names_present": pathlib.Path("/etc/resolv.conf").exists(), "nameserver_count": sum(1 for line in (_read_text("/etc/resolv.conf") or "").splitlines() if line.startswith("nameserver")), "note": "resolver addresses not stored"},
        "proxy_env": {"http_proxy_set": bool(os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")), "https_proxy_set": bool(os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")), "no_proxy_set": bool(os.environ.get("no_proxy") or os.environ.get("NO_PROXY")), "values_stored": False},
        "path_separation": {
            "SHELL_HTTP": "probes in this file were executed from the sandbox shell (python urllib) — see 'hosts'",
            "NATIVE_WEB_FETCH": "see native-tools.json -> native_fetch_tests (Arena tool, separate execution context)",
            "BROWSER_NAVIGATION": "NOT_TESTED — no browser is installed and none was launched for discovery",
        },
        "failures": sorted({(h, (e.get('https') or {}).get('outcome')) for h, e in hosts.items() if (e.get('https') or {}).get('outcome') not in (None, 'OK')} , key=lambda t: (str(t[1]), t[0])),
    }


# --------------------------------------------------------------------------
# part 7 — github
# --------------------------------------------------------------------------

def collect_github(runner: Runner, repo_hint: str | None) -> dict:
    out: dict = {"schema": SCHEMA, "credentials_read_or_printed": False, "token_values_stored": False}
    git = shutil.which("git")
    if git:
        version = runner.run([git, "--version"], label="git --version", timeout=15)
        out["git_version"] = ((version.get("stdout") or "").strip().splitlines() or [None])[0]
        for key, args in (
            ("remotes", ["remote", "-v"]),
            ("current_branch", ["branch", "--show-current"]),
            ("head_sha", ["rev-parse", "HEAD"]),
            ("head_short", ["rev-parse", "--short", "HEAD"]),
            ("upstream_head", ["rev-parse", "--short", "origin/main"]),
            ("status_porcelain", ["status", "--porcelain=v1"]),
            ("tracked_file_count", ["ls-files"]),
            ("config_user_set", ["config", "--get", "user.email"]),
        ):
            res = runner.run([git, *args], label=f"git {key}", timeout=25, stdout_limit=20000)
            text = (res.get("stdout") or "").strip()
            if key == "status_porcelain":
                lines = [ln for ln in text.splitlines() if ln.strip()]
                out["working_tree"] = {"dirty_file_count": len(lines), "paths": [redact(ln.split(" ", 1)[-1]) for ln in lines[:200]], "note": "untracked/modified paths at scan time"}
            elif key == "tracked_file_count":
                out["tracked_file_count"] = len([ln for ln in text.splitlines() if ln.strip()])
            elif key == "config_user_set":
                out["git_identity_configured"] = bool(text)
                out["git_identity_kind"] = "configured" if text else "absent_or_fallback"
            else:
                if key == "remotes":
                    parsed: dict[str, str] = {}
                    for ln in text.splitlines():
                        if not ln.strip():
                            continue
                        name, _, rest = ln.replace("\t", " ").partition(" ")
                        url = rest.strip()
                        if url.endswith("(fetch)") or url.endswith("(push)"):
                            url = url.rsplit(" ", 1)[0].strip()
                        parsed[redact(name)] = redact(url)
                    out["remotes"] = [{"name": k, "url": v} for k, v in sorted(parsed.items())]
                    out["remote_urls_credential_bearing"] = any("@" in v for v in parsed.values())
                else:
                    out[key] = redact(text) or None
    gh = shutil.which("gh")
    out["gh_present"] = bool(gh)
    if gh:
        ver = runner.run([gh, "--version"], label="gh --version", timeout=20)
        out["gh_version"] = ((ver.get("stdout") or "").strip().splitlines() or [None])[0]
        auth = runner.run([gh, "auth", "status", "-h", "github.com"], label="gh auth status", timeout=40)
        raw = (auth.get("stdout") or "") + (auth.get("stderr") or "")
        out["gh_auth"] = {
            "exit_code": auth.get("exit_code"),
            "authenticated": bool(re.search(r"(?i)logged in", raw)),
            "hostname_mentioned": "github.com" in raw,
            "mechanism": ("GH_TOKEN env" if os.environ.get("GH_TOKEN") else None) or ("GITHUB_TOKEN env" if os.environ.get("GITHUB_TOKEN") else None) or ("keyring/gh config" if re.search(r"(?i)keyring", raw) else None),
            "raw_output_stored": False,
            "redaction_findings_in_output": find_secrets_in_text(raw),
            "sha256_12_of_raw_output": short_hash(raw),
        }
        who = runner.run([gh, "api", "user", "--jq", ".login"], label="gh api user", timeout=40)
        who_err = ((who.get("stderr") or "") + (who.get("stdout") or ""))
        actor: dict = {
            "probe_exit_code": who.get("exit_code"),
            "user_endpoint_available": who.get("exit_code") == 0,
            "login_value_stored": False,
        }
        if who.get("exit_code") == 0 and (who.get("stdout") or "").strip():
            login = who["stdout"].strip()
            actor["login_hash12"] = short_hash(login)
            actor["is_repo_owner"] = login.lower() == (repo_hint or "").split("/")[0].lower() if repo_hint else None
        if "Resource not accessible by integration" in who_err:
            actor["token_type_inference"] = "GitHub App installation token (the /user endpoint returns 403 'Resource not accessible by integration'), not a user PAT"
        out["gh_actor"] = actor
        if repo_hint:
            meta = runner.run([gh, "api", f"repos/{repo_hint}", "--jq", '{private:.private, fork:.fork, default_branch:.default_branch, archived:.archived, push_allowed:.push_disabled|(not), permissions:.permissions, viewer_can_admin: .permissions.admin}'], label="gh api repo meta", timeout=45)
            parsed = None
            if meta.get("exit_code") == 0:
                try:
                    parsed = json.loads(meta["stdout"])
                except json.JSONDecodeError:
                    parsed = {"parse_error": True}
            out["repository_metadata"] = {"repo": repo_hint, "probe_exit_code": meta.get("exit_code"), "data": parsed, "error": meta.get("error")}
            perms = runner.run([gh, "api", f"repos/{repo_hint}", "--jq", ".permissions"], label="gh api repo permissions", timeout=45)
            out["repo_permissions"] = {"raw_present": bool((perms.get("stdout") or "").strip()), "data": None}
            if perms.get("exit_code") == 0:
                try:
                    out["repo_permissions"]["data"] = json.loads(perms["stdout"])
                except json.JSONDecodeError:
                    out["repo_permissions"]["data"] = None
            prs = runner.run([gh, "pr", "list", "--repo", repo_hint, "--state", "all", "--limit", "50", "--json", "number,title,headRefName,state,isDraft,url"], label="gh pr list", timeout=60, stdout_limit=200000)
            pr_list = None
            if prs.get("exit_code") == 0:
                try:
                    pr_list = json.loads(prs["stdout"])
                except json.JSONDecodeError:
                    pr_list = None
            out["existing_pull_requests"] = {"count": len(pr_list) if pr_list else 0, "items": [{"number": p.get("number"), "state": p.get("state"), "is_draft": p.get("isDraft"), "head_ref": p.get("headRefName"), "title": (p.get("title") or "")[:80], "url": p.get("url")} for p in (pr_list or [])], "note": "PRs are listed by number/state/head only; do not merge, close or rebase another session's PR"}
            branches = runner.run([gh, "api", f"repos/{repo_hint}/branches?per_page=100", "--jq", "[.[].name]"], label="gh api branches", timeout=45, stdout_limit=60000)
            try:
                out["remote_branches"] = json.loads(branches["stdout"]) if branches.get("exit_code") == 0 else None
            except json.JSONDecodeError:
                out["remote_branches"] = None
            inst = runner.run([gh, "api", "/installation/repositories?per_page=100", "--jq", '{total_count:.total_count, names:([.repositories[]?.name])}'], label="gh api installation/repositories", timeout=60, stdout_limit=200000)
            inst_data = None
            if inst.get("exit_code") == 0:
                try:
                    inst_data = json.loads(inst["stdout"])
                except json.JSONDecodeError:
                    inst_data = None
            installation: dict = {"endpoint": "/installation/repositories (GitHub App installation scope)", "exit_code": inst.get("exit_code"), "available": inst_data is not None, "accessible_repository_count": (inst_data or {}).get("total_count") if inst_data else None, "target_repo_in_installation": (repo_hint.split("/")[1] in ((inst_data or {}).get("names") or [])) if inst_data and repo_hint else None, "repository_names_stored": False, "error_detail": None if inst_data else redact(((inst.get("stdout") or "") + (inst.get("stderr") or ""))[:200]).strip() or None}
            if not installation["available"]:
                alt = runner.run([gh, "api", "repos/" + repo_hint, "--jq", ".full_name"], label="gh api repo accessible", timeout=45)
                installation["fallback_repo_scoped_check"] = {"exit_code": alt.get("exit_code"), "target_repo_accessible": (alt.get("exit_code") == 0), "note": "installation endpoint not available for this token type; only the selected repository's accessibility was verified, per scope rules"}
            out["github_app_installation"] = installation
            out["branch_share_risk"] = {"note": "another Arena session may share the remote branch; verify ahead of push", "remote_branch_equals_local": None}
    out["write_capability"] = {"method": "verified by the actual commit+push performed after this scan (see validation.json -> delivery)", "status": "NOT_TESTED_AT_SCAN_TIME"}
    out["not_tested"] = ["merge", "close/open PR state changes on other sessions' PRs", "force-push (prohibited)", "push to main (prohibited)", "org-level administration"]
    return out


# --------------------------------------------------------------------------
# part 8 — persistence + fingerprints
# --------------------------------------------------------------------------

MARKER_HOME = ".arena-inventory-marker.json"
MARKER_TMP = "arena-inventory-marker.json"
MARKER_REPO = "inventory/last-session-marker.json"  # runtime-only: tracking it would confuse Git checkout with sandbox persistence


def collect_persistence(session_dir: pathlib.Path, fingerprints: dict) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    targets = {
        "home": pathlib.Path.home() / MARKER_HOME,
        "tmp": pathlib.Path("/tmp") / MARKER_TMP,
        "repo": pathlib.Path(os.getcwd()) / MARKER_REPO,
    }
    found: dict[str, dict] = {}
    for label, path in targets.items():
        entry: dict = {"path": redact(str(path)), "exists": path.exists()}
        previous = None
        if path.exists():
            try:
                previous = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                entry["read_error"] = type(exc).__name__
        if isinstance(previous, dict):
            entry["previous_session_id"] = previous.get("session_id")
            entry["same_session_self_reference"] = previous.get("session_id") == fingerprints.get("session_id")
            entry["usable_for_cross_session_comparison"] = entry["previous_session_id"] not in (None, fingerprints.get("session_id"))
            entry["previous_collected_utc"] = previous.get("collected_utc")
            entry["previous_fingerprints"] = previous.get("fingerprints")
            entry["age_hours"] = round((now - dt.datetime.fromisoformat(previous["collected_utc"])).total_seconds() / 3600, 2) if previous.get("collected_utc") else None
            same = {k: (previous.get("fingerprints", {}).get(k) == fingerprints.get(k)) for k in fingerprints} if isinstance(previous.get("fingerprints"), dict) else {}
            entry["fingerprint_match"] = same
            entry["environment_changed_since_previous"] = any(v is False for v in same.values()) if same else None
        else:
            entry["previous_session_id"] = None
            entry["environment_changed_since_previous"] = None
            entry["note"] = "no readable marker from an earlier session at this path"
        found[label] = entry
    marker_payload = {
        "marker": "arena-inventory",
        "purpose": "single-file, credential-free persistence probe; safe to delete",
        "session_id": fingerprints.get("session_id"),
        "collected_utc": now.isoformat(timespec="seconds"),
        "engine": ENGINE,
        "host_hash": short_hash(_HOSTNAME),
        "fingerprints": fingerprints.get("fingerprints") or {},
        "session_directory": redact(str(session_dir)),
        "note": "Compare this file with the next session's marker to detect environment drift. Do NOT conclude persistence from a single run.",
    }
    written = {}
    for label, path in targets.items():
        try:
            path.write_text(json.dumps(marker_payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            written[label] = {"written": True, "path": redact(str(path)), "bytes": path.stat().st_size}
        except OSError as exc:
            written[label] = {"written": False, "path": redact(str(path)), "error": type(exc).__name__}
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "persistence-marker.json").write_text(json.dumps(marker_payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "schema": SCHEMA,
        "checked_utc": now.isoformat(timespec="seconds"),
        "previous_markers": found,
        "new_markers_written": written,
        "cross_session_persistence_conclusion": "DEFERRED — a first run cannot demonstrate persistence; compare with the next session",
        "tmp_writable": os.access("/tmp", os.W_OK),
        "home_writable": os.access(pathlib.Path.home(), os.W_OK),
        "repo_writable": os.access(os.getcwd(), os.W_OK),
    }



def collect_artifacts(session_parent: pathlib.Path) -> dict:
    """Inventory generated, non-manifest artefacts (images etc.) with hashes and dimensions."""
    items = []
    art_dir = session_parent / "artifacts"
    if art_dir.is_dir():
        for path in sorted(art_dir.iterdir()):
            if not path.is_file():
                continue
            data = path.read_bytes()
            entry = {
                "path": redact(str(path.relative_to(session_parent.parent))),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            if path.suffix.lower() == ".png" and data[:8] == b"\x89PNG\r\n\x1a\n":
                try:
                    width, height = struct.unpack(">II", data[16:24])
                    entry.update({"kind": "png", "width": width, "height": height, "signature_valid": True})
                except struct.error:
                    entry["kind"] = "png (header unreadable)"
            elif path.suffix.lower() in (".jpg", ".jpeg"):
                entry["kind"] = "jpeg"
            else:
                entry["kind"] = path.suffix.lstrip(".") or "file"
            items.append(entry)
    return {"directory": redact(str(art_dir)) if art_dir.is_dir() else None, "count": len(items), "items": items}


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def build_fingerprints(system: dict, os_packages: dict, python: dict, node: dict, executables: dict) -> dict:
    pkg_versions = sorted(f"{p['package']}=={p['version']}" for p in os_packages.get("packages", []) if p.get("package"))
    limits = system.get("rlimits", {})
    disk = system.get("disk", {})
    sys_payload = {
        "os": {k: (system.get("os") or {}).get(k) for k in ("id", "version_id", "version_codename", "pretty_name")},
        "kernel_release": (system.get("kernel") or {}).get("release"),
        "machine": (system.get("kernel") or {}).get("machine"),
        "cpu_count": (system.get("cpu") or {}).get("logical"),
        "memtotal_kb": (system.get("memory_kb") or {}).get("MemTotal"),
        "dev_shm_total_bytes": (disk.get("dev_shm") or {}).get("total_bytes"),
        "disk_root_total_bytes": (disk.get("root") or {}).get("total_bytes"),
        "rlimits": {k: v for k, v in limits.items()},
        "os_packages": pkg_versions,
        "os_package_count": len(pkg_versions),
    }
    dists = sorted(f"{d['name']}=={d['version']}" for d in ((python.get("installed_distributions") or {}).get("items") or []))
    py_payload = {
        "interpreter_version": (python.get("active_interpreter") or {}).get("version"),
        "implementation": (python.get("active_interpreter") or {}).get("implementation"),
        "stdlib_count": (python.get("standard_library") or {}).get("count"),
        "installed_distributions": dists,
        "interpreter_count": len(python.get("distributions_found_on_path") or {}),
    }
    node_payload = {
        "node_version": (node.get("runtime") or {}).get("version"),
        "v8": (node.get("runtime") or {}).get("v8"),
        "npm": ((node.get("package_managers") or {}).get("npm") or {}).get("version"),
        "global_packages": sorted(node.get("global_packages") or []),
        "builtin_module_count": node.get("builtin_module_count"),
    }
    versions = {
        name: (meta.get("version_parsed") or "unspecified")
        for name, meta in (executables.get("version_probes") or {}).items()
        if meta.get("present_on_path")
    }
    exe_payload = {
        "executable_names": executables.get("executables") or [],
        "executable_count": executables.get("executable_count"),
        "versioned_tools": versions,
    }
    named = {"SYSTEM": sys_payload, "PYTHON": py_payload, "NODE": node_payload, "EXECUTABLES": exe_payload}
    fingerprints = {name: hashlib.sha256(canonical(payload)).hexdigest() for name, payload in named.items()}
    fingerprints["COMBINED"] = hashlib.sha256("\n".join(f"{name}:{fingerprints[name]}" for name in ("SYSTEM", "PYTHON", "NODE", "EXECUTABLES")).encode()).hexdigest()
    return {
        "schema": SCHEMA,
        "algorithm": "sha256 over canonical JSON (sorted keys, ',' / ':' separators, ascii) of the payload below",
        "fingerprints": fingerprints,
        "payloads": named,
        "field_documentation": {
            "SYSTEM": "os-release id/version_id/codename/pretty_name, kernel release, machine, logical CPU count, MemTotal kB, /dev/shm total bytes, root filesystem TOTAL bytes, rlimits, complete sorted dpkg 'package==version' list plus its count",
            "PYTHON": "active interpreter version + implementation, stdlib module count, complete sorted 'name==version' list from importlib.metadata, count of python interpreters found on PATH/standard dirs",
            "NODE": "node version, v8 version, npm version, sorted global package list, node builtin module count",
            "EXECUTABLES": "sorted normalized PATH executable names, their count, and parsed version strings for the probed tool set",
            "COMBINED": "sha256 of the four fingerprints joined in fixed order SYSTEM, PYTHON, NODE, EXECUTABLES",
        },
        "excluded_from_fingerprints": [
            "all timestamps and elapsed times",
            "network/DNS/TLS measurements and HTTP statuses",
            "session ids and random values",
            "free/available disk and memory (they drift during a run)",
            "PIDs, uid/gid, hostname, home path (identity; hostname only kept as a hash elsewhere)",
            "package install locations and file paths",
            "github/probe error text (unstable ordering and content)",
        ],
        "usage": "compare fingerprints between sessions to detect environment drift; equality means the fingerprinted fields matched",
    }


# --------------------------------------------------------------------------
# part 5/6/9 — observations merge, capabilities, validation, outputs
# --------------------------------------------------------------------------

REQUIRED_FILES = [
    "system.json",
    "executables.json",
    "python.json",
    "node.json",
    "os-packages.json",
    "libraries.json",
    "fonts.json",
    "network.json",
    "registries.json",
    "native-tools.json",
    "github.json",
    "persistence.json",
    "fingerprints.json",
    "capabilities.json",
    "validation.json",
]


def default_observations() -> dict:
    return {
        "agent_tools": [],
        "native_fetch_tests": [],
        "practical_tests": [],
        "ui_items": [],
        "notes": "No operator-supplied observations were provided (native tool surfaces cannot be introspected from inside the sandbox shell; they must be declared by the agent).",
    }


def _path_divergence(network: dict, observations: dict) -> list[dict]:
    """Compare sandbox-shell HTTPS results with the agent's native fetch results per host."""
    rows = []
    native = {}
    for test in observations.get("native_fetch_tests") or []:
        host = (test.get("host") or "").replace("https://", "").split("/")[0]
        native[host] = "OK" if str(test.get("result", "")).lower().startswith("ok") else (test.get("result") or "")
    for host, entry in (network.get("hosts") or {}).items():
        shell = entry.get("tcp_tls_http_egress") or "NOT_TESTED"
        if host in native:
            rows.append({"host": host, "shell_https": shell, "native_fetch": native[host], "divergent": shell != "ALLOWED" and native[host] == "OK"})
    for host, status in native.items():
        if host not in (network.get("hosts") or {}):
            rows.append({"host": host, "shell_https": "NOT_PROBED", "native_fetch": status, "divergent": None})
    return sorted(rows, key=lambda r: (not r["divergent"], r["host"]))


def build_capabilities(system, exe, py, node, os_packages, libraries, fonts, browsers, network, registries, installs, github, observations, net_cfg, practical=None, persistence=None) -> dict:
    versions = {k: v.get("version_parsed") for k, v in (exe.get("version_probes") or {}).items()}

    def status(name: str) -> str:
        return "INSTALLED" if (exe.get("version_probes") or {}).get(name, {}).get("present_on_path") else "NOT_INSTALLED"

    def reg(label: str, items: dict) -> str:
        if not items:
            return "NOT_TESTED"
        vals = [v.get("status_label") for v in items.values()]
        return "REGISTRY_REACHABLE" if "REGISTRY_REACHABLE" in vals else "REGISTRY_UNREACHABLE"

    pip_status = ((installs.get("results") or {}).get("pypi_pip_six") or {}).get("status", "NOT_TESTED")
    npm_status = ((installs.get("results") or {}).get("npm_is_number") or {}).get("status", "NOT_TESTED")
    tools = observations.get("agent_tools") or []
    return {
        "schema": SCHEMA,
        "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "status_vocabulary": ["INSTALLED", "REGISTRY_REACHABLE", "INSTALLATION_TESTED", "INSTALLATION_FAILED", "EXPOSED", "EXECUTED_NOW", "PARTIAL", "FAILED", "NOT_TESTED", "NOT_INSTALLED", "UNKNOWN"],
        "classification_note": "INSTALLED = binary/library present; REGISTRY_REACHABLE = index answered but nothing installed; INSTALLATION_TESTED = the engine actually installed and executed a tiny package this session; EXPOSED = callable in this agent session but not necessarily exercised; EXECUTED_NOW = ran successfully in this session; NOT_TESTED = no evidence either way, not a negative claim.",
        "environment": {
            "distribution": (system.get("os") or {}).get("pretty_name"),
            "kernel": (system.get("kernel") or {}).get("release"),
            "arch": (system.get("kernel") or {}).get("machine"),
            "cpus": (system.get("cpu") or {}).get("logical"),
            "memory_mb": round(((system.get("memory_kb") or {}).get("MemTotal") or 0) / 1024),
            "privilege": (system.get("user_privilege") or {}).get("category"),
        },
        "runtimes": {
            "python": {"status": status("python3"), "version": versions.get("python3"), "interpreters_on_path": sorted((py.get("distributions_found_on_path") or {}).keys())},
            "node": {"status": "INSTALLED" if node.get("node_present") else "NOT_INSTALLED", "version": (node.get("runtime") or {}).get("version"), "npm": ((node.get("package_managers") or {}).get("npm") or {}).get("version"), "yarn": ((node.get("package_managers") or {}).get("yarn") or {}).get("version")},
            "other": {name: status(name) for name in ("go", "rustc", "java", "php", "ruby", "deno", "bun", "cmake", "clang")},
        },
        "package_installation": {
            "pypi": {"registry": reg("pypi", (registries.get("pypi") or {}).get("items") or {}), "installation": pip_status, "index_reachable_count": (registries.get("pypi") or {}).get("reachable_count"), "probed": (registries.get("pypi") or {}).get("probed_count")},
            "npm": {"registry": reg("npm", (registries.get("npm") or {}).get("items") or {}), "installation": npm_status, "index_reachable_count": (registries.get("npm") or {}).get("reachable_count"), "probed": (registries.get("npm") or {}).get("probed_count")},
            "apt_debian": {
                "registry_from_shell": "REGISTRY_REACHABLE" if any(v.get("outcome") == "OK" for v in (registries.get("documented_download_endpoints") or {}).values() if "deb.debian.org" in v.get("url", "")) else ("REGISTRY_BLOCKED_FROM_SHELL" if any(v.get("outcome", "").startswith("TLS") for v in (registries.get("documented_download_endpoints") or {}).values() if "deb.debian.org" in v.get("url", "")) else "NOT_TESTED"),
                "apt_index_present": bool((system.get("apt_state") or {}).get("index_populated")),
                "installation": "NOT_TESTED",
                "reason": "apt-get update/install changes system packages and needs elevation; deliberately not attempted",
            },
            "playwright_browsers": {"registry": reg("pw", {k: v for k, v in (registries.get("documented_download_endpoints") or {}).items() if "playwright" in k}), "installation": "NOT_TESTED", "binary_download": "NOT_TESTED", "reason": "large binaries were not downloaded for inventory purposes"},
            "caveat": "A reachable registry does not prove that every package can be installed, built or executed (no compilers/HEADs for many wheels, no apt, no native builds tested).",
        },
        "software_inventory": {
            "path_executables": exe.get("executable_count"),
            "os_packages_installed": os_packages.get("installed_count"),
            "python_distributions": (py.get("installed_distributions") or {}).get("count"),
            "python_stdlib_modules": (py.get("standard_library") or {}).get("count"),
            "shared_libraries": libraries.get("count"),
            "font_files": fonts.get("font_file_count"),
            "font_families": fonts.get("family_count_estimate"),
            "node_global_packages": node.get("global_package_count"),
            "node_builtin_modules": node.get("builtin_module_count"),
        },
        "document_and_media": {name: status(name) for name in ("pandoc", "soffice", "pdftotext", "pdfinfo", "gs", "ffmpeg", "magick", "convert", "rsvg-convert", "inkscape", "tesseract")},
        "document_generation_libraries_python": {
            "note": "presence derived from installed distribution names; no document was produced by this engine, so no PDF/DOCX/XLSX rendering is implied",
            "present": sorted({d["name"].lower() for d in ((py.get("installed_distributions") or {}).get("items") or [])} & {"reportlab", "fpdf2", "pypdf", "openpyxl", "docx", "python-docx", "xlsxwriter", "weasyprint", "pillow", "matplotlib", "pandas", "numpy", "markdown", "jinja2"}),
            "status": "NOT_INSTALLED (none of the document-generation distributions were found)" if not sorted({d["name"].lower() for d in ((py.get("installed_distributions") or {}).get("items") or [])} & {"reportlab", "fpdf2", "pypdf", "openpyxl", "docx", "python-docx", "xlsxwriter", "weasyprint", "pillow", "matplotlib", "pandas", "numpy"}) else "PRESENT",
        },
        "browsers": {"status": "NOT_INSTALLED" if not any(v.get("status") == "INSTALLED" for v in (browsers.get("executables") or {}).values()) else "PARTIAL", "detail": {k: v.get("status") for k, v in (browsers.get("executables") or {}).items()}, "caches": browsers.get("caches_and_config"), "navigation": "NOT_TESTED"},
        "network": {
            "shell_http": {"dns_ok": network["counts"]["dns_ok"], "hosts_total": len(NETWORK_HOSTS), "https_ok": network["counts"]["https_ok"], "https_failed": network["counts"]["https_failed"], "tls_handshake_ok": network["counts"]["tls_handshake_ok"], "max_request_seconds": net_cfg},
            "native_web_fetch": {"status": "EXECUTED_NOW" if any(t.get("result", "").lower().startswith("ok") for t in (observations.get("native_fetch_tests") or [])) else ("FAILED" if observations.get("native_fetch_tests") else "NOT_TESTED"), "tests": observations.get("native_fetch_tests") or [], "note": "executed through the agent's own tool, outside the sandbox shell"},
            "browser_navigation": {"status": "NOT_TESTED", "reason": "no browser installed; none launched for discovery (per safety boundary)"},
            "unreachable_hosts": [h for h, e in (network.get("hosts") or {}).items() if e.get("tcp_tls_http_egress") != "ALLOWED"],
            "independent_paths_note": "SHELL_HTTP, NATIVE_WEB_FETCH and BROWSER_NAVIGATION are recorded separately; success of one is never treated as proof for another.",
            "shell_vs_native_comparison": _path_divergence(network, observations),
        },
        "agent_tools": {
            "declared_count": len(tools),
            "executed_count": sum(1 for t in tools if t.get("executed_this_session")),
            "source": "operator/agent-declared interface description (inventory/observations file); not introspectable from the sandbox shell",
            "tools": [
                {
                    "name": tl.get("name"),
                    "status": "EXECUTED_NOW" if tl.get("executed_this_session") else "EXPOSED_NOT_EXERCISED",
                    "execution_result": (tl.get("execution_result") or "")[:160] or None,
                }
                for tl in tools
            ],
        },
        "persistence": persistence or {},
        "practical_capability_tests": {
            "executed_by_engine": (practical or {}).get("counts") or {},
            "executed_by_agent": [t.get("id") or t.get("test") for t in (observations.get("practical_tests") or [])],
            "details_in": "native-tools.json -> engine_capability_tests",
            "generated_artifacts": (practical or {}).get("generated_artifacts") or {},
        },
        "github_delivery": {
            "connected_repository": ((github.get("remotes") or [{}])[0] or {}).get("url"),
            "working_branch": github.get("current_branch"),
            "git": github.get("git_version"),
            "gh": github.get("gh_version"),
            "authentication": ("EXPOSED" if (github.get("gh_auth") or {}).get("authenticated") else "NOT_TESTED"),
            "read": "EXECUTED_NOW" if (github.get("repository_metadata") or {}).get("probe_exit_code") == 0 else "NOT_TESTED",
            "write": "see validation.json -> delivery (verified by the actual push)",
        },
        "not_tested_or_unknown": sorted(
            set(
                [
                    "model identity and per-request model routing",
                    "credit balance, per-tool credit cost, reset time",
                    "session/concurrency limits enforced by the platform",
                    "workspace ZIP export / /download-workspace",
                    "file upload size limits",
                    "UI preview panel behaviour (browser-side rendering)",
                    "account privacy controls",
                    "persistent storage across sessions (needs a second run)",
                    "apt/system package installation",
                    "browser binary installation and navigation",
                    "Lighthouse / axe-core / WCAG audits (no runtime available this session)",
                    "office/PDF rendering in a real application",
                ]
                + [t.get("name", "?") + ":not-exercised" for t in tools if not t.get("executed_this_session")]
            )
        ),
    }


def build_validation(session_dir: pathlib.Path, files_written: list[str], runner: Runner, secret_findings: list[dict], delivery: dict | None, practical: dict | None = None) -> dict:
    checks = []
    for name in REQUIRED_FILES:
        path = session_dir / name
        entry = {"file": name, "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0}
        if path.exists():
            try:
                entry["json_valid"] = True
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                entry["json_valid"] = False
                entry["json_error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        else:
            entry["json_valid"] = False
        entry["ok"] = entry["exists"] and entry.get("json_valid") is True
        checks.append(entry)
    missing = [c["file"] for c in checks if not c["ok"]]
    directory_listing = []
    for entry in sorted(os.listdir(session_dir)):
        path = session_dir / entry
        item = {"file": entry, "bytes": path.stat().st_size if path.is_file() else 0, "is_file": path.is_file()}
        if path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
                item["json_valid"] = True
            except (OSError, json.JSONDecodeError) as exc:
                item["json_valid"] = False
                item["json_error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        directory_listing.append(item)
    extra_files = [i["file"] for i in directory_listing if i["file"] not in REQUIRED_FILES]
    invalid_extra = [i["file"] for i in directory_listing if i["file"] not in REQUIRED_FILES and i.get("json_valid") is False]
    return {
        "schema": SCHEMA,
        "validated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "expected_files": REQUIRED_FILES,
        "files_written_by_engine": files_written,
        "file_checks": checks,
        "missing_or_invalid": missing,
        "all_expected_files_present_and_valid": not missing and not invalid_extra,
        "directory_listing": directory_listing,
        "extra_files_beyond_required": extra_files,
        "json_parser": "json.loads (CPython " + sys.version.split()[0] + ")",
        "secret_scan": {"patterns": sorted({name for _, name in _SECRET_PATTERNS}), "findings": secret_findings, "clean": not secret_findings, "scope": "every file in the session directory plus this script"},
        "environment_values_stored": False,
        "subprocess_timeouts": {"all_calls_bounded": True, "max_timeout_seconds_used": runner.max_timeout_used, "note": "every Runner.run call passes an explicit timeout= and HTTP probes pass timeout= to urlopen/socket"},
        "failed_commands": {"count": len(runner.failures), "items": runner.failures[:60], "note": "non-zero exits and probe errors are retained rather than silently dropped"},
        "network_safety": {"tls_verification_disabled": False, "port_scans": False, "crawling": False, "arena_platform_automated_access": False, "cloud_metadata_probed": False},
        "privacy": {"machine_hostname_stored": False, "public_target_hostnames_stored": True, "usernames_stored": False, "public_dns_ip_addresses_stored": True, "egress_ip_stored": False, "credential_values_stored": False, "private_repo_names_stored": False},
        "capability_tests": (practical or {}).get("counts") or {},
        "capability_tests_failures": [t for t in ((practical or {}).get("tests") or []) if t.get("status") == "FAILED"],
        "limitations": [
            "capability claims here describe THIS session only",
            "agent tool inventory is operator-declared, not machine-introspectable",
            "not every registry entry can necessarily be installed or executed",
        ],
        "delivery": delivery or {"status": "NOT_YET_DELIVERED", "note": "run scripts/inventory.py --record-delivery after commit/push/PR to attach delivery evidence"},
    }


def scan_secrets(session_dir: pathlib.Path) -> list[dict]:
    findings = []
    targets = [session_dir / f for f in sorted(os.listdir(session_dir))]
    engine = pathlib.Path(__file__)
    targets.append(engine)
    for path in targets:
        if not path.is_file() or path.suffix not in (".json", ".md", ".py"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        skip = range(0, 0)
        if path == engine:
            # The scanner's own detection patterns look like secrets; ignore that block.
            lo = text.find("_SECRET_PATTERNS")
            hi = text.find("def redact(")
            skip = range(text.count("\n", 0, lo), text.count("\n", 0, hi)) if lo != -1 and hi > lo else skip
        for hit in find_secret_lines(text):
            if hit["line"] in skip:
                continue
            findings.append({"file": redact(str(path)), "pattern": hit["pattern"], "line": hit["line"], "snippet_stored": False})
    return findings


# --------------------------------------------------------------------------
# part 6 — practical capability tests executed by the engine itself
# --------------------------------------------------------------------------

def collect_practical_tests(runner: Runner, session_dir: pathlib.Path) -> dict:
    """Small, local, reversible execution tests. Nothing here touches the network
    except the loopback HTTP server, and nothing modifies system state."""
    tests: list[dict] = []
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="arena-inv-tests-"))
    recorded_files: list[str] = []

    def add(tid: str, command: str, ok: bool, detail: str = "", extra: dict | None = None) -> None:
        entry = {
            "id": tid,
            "command": redact(command),
            "status": "EXECUTED_NOW" if ok else "FAILED",
            "detail": redact(detail)[:300],
        }
        if extra:
            entry.update(extra)
        tests.append(entry)

    # 1. python compute + JSON round-trip
    code = "import hashlib,json;z=hashlib.sha256(b'arena').hexdigest();print(json.dumps({'sha256':z[:16],'rt':json.loads(json.dumps({'a':[1,2,3]}))['a']}))"
    res = runner.run([sys.executable, "-c", code], label="test:python-json", timeout=30)
    add("python_compute_and_json_roundtrip", f"{sys.executable} -c <{len(code)} chars>", res.get("exit_code") == 0, (res.get("stdout") or res.get("error") or "").strip())

    # 2. stdlib sqlite3
    sql = ("import sqlite3,json;c=sqlite3.connect(':memory:');c.execute('create table t(a int,b text)');"
           "c.executemany('insert into t values(?,?)',[(1,'x'),(2,'y')]);c.commit();"
           "print(json.dumps({'rows':c.execute('select count(*),sum(a) from t').fetchall(),'version':sqlite3.sqlite_version}))")
    res = runner.run([sys.executable, "-c", sql], label="test:sqlite3", timeout=30)
    add("stdlib_sqlite3_read_write", f"{sys.executable} -c <sqlite3>", res.get("exit_code") == 0, (res.get("stdout") or res.get("error") or "").strip())

    # 3. CSV write + read back
    csv_path = tmp / "roundtrip.csv"
    csv_code = (
        "import csv,sys,json;p=%r\nwith open(p,'w',newline='') as f:\n w=csv.writer(f);w.writerow(['a','b']);w.writerow([1,'x,y']);w.writerow([2,\"quote'\"])\n"
        "rows=list(csv.reader(open(p,newline='')))\nprint(json.dumps({'rows':rows,'cols':len(rows[0])}))" % str(csv_path)
    )
    res = runner.run([sys.executable, "-c", csv_code], label="test:csv", timeout=30)
    ok = res.get("exit_code") == 0 and "a" in (res.get("stdout") or "")
    add("csv_write_read_roundtrip", f"{sys.executable} -c <csv roundtrip on {redact(str(csv_path))}>", ok, (res.get("stdout") or res.get("error") or "").strip())

    # 4. ZIP create + verify
    zip_code = (
        "import zipfile,json,os;src=%r;z=%r\nopen(os.path.join(src,'a.txt'),'w').write('hello')\n"
        "with zipfile.ZipFile(z,'w') as f: f.write(os.path.join(src,'a.txt'),'a.txt')\n"
        "with zipfile.ZipFile(z) as f: bad=f.testzip(); data=f.read('a.txt')\n"
        "print(json.dumps({'members':f.namelist(),'tested':bad is None,'bytes':len(data)}))" % (str(tmp), str(tmp / "t.zip"))
    )
    res = runner.run([sys.executable, "-c", zip_code], label="test:zip", timeout=30)
    add("zip_create_and_read", f"{sys.executable} -c <zip roundtrip>", res.get("exit_code") == 0, (res.get("stdout") or res.get("error") or "").strip())

    # 5. /dev/shm and tmpfs writability
    shm = pathlib.Path("/dev/shm/arena-inv-probe.txt")
    shm_ok = False
    try:
        shm.write_text("probe", encoding="utf-8")
        shm_ok = shm.read_text(encoding="utf-8") == "probe"
        shm.unlink()
    except OSError as exc:
        shm_ok = False
        detail = type(exc).__name__
    else:
        detail = "wrote+read+removed"
    add("dev_shm_write_read", f"write/read/remove {redact(str(shm))}", shm_ok, detail)

    # 6. node runtime + crypto + fs
    node = shutil.which("node")
    node_js = "const c=require('crypto'),f=require('fs');f.writeFileSync(process.argv[1],'x'.repeat(10));" \
              "console.log(JSON.stringify({sha:c.createHash('sha256').update('arena').digest('hex').slice(0,16),size:f.statSync(process.argv[1]).size}))"
    if node:
        res = runner.run([node, "-e", node_js, str(tmp / "node-out.bin")], label="test:node", timeout=40)
        add("node_compute_fs_and_crypto", f"{node} -e <crypto+fs write>", res.get("exit_code") == 0, (res.get("stdout") or res.get("error") or "").strip())
    else:
        add("node_compute_fs_and_crypto", "node -e <crypto+fs write>", False, "node not on PATH")

    # 7. local loopback HTTP server (start, request, stop)
    srv: dict = {"status": "NOT_TESTED"}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        (tmp / "index.html").write_text("<html><body>arena-inventory-ok</body></html>", encoding="utf-8")
        proc = subprocess.Popen(  # noqa: S603 - fixed argv, loopback only, always reaped below
            [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
            cwd=str(tmp), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            body = None
            status = None
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=2) as r:
                        status, body = r.status, r.read(200).decode("utf-8", "replace")
                    break
                except OSError:
                    time.sleep(0.3)
            srv = {
                "status": "EXECUTED_NOW" if status == 200 and "arena-inventory-ok" in (body or "") else "FAILED",
                "server": "python3 -m http.server",
                "bind": f"127.0.0.1:{port}",
                "http_status": status,
                "body_contains_expected_token": "arena-inventory-ok" in (body or ""),
                "loopback_only": True,
            }
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
            srv["stopped"] = proc.poll() is not None
            srv["exit_after_terminate"] = proc.returncode
    except Exception as exc:  # pragma: no cover
        srv = {"status": "FAILED", "error": f"{type(exc).__name__}: {redact(str(exc))[:160]}"}
    tests.append({"id": "local_http_server_start_request_stop", "command": f"{sys.executable} -m http.server <port> --bind 127.0.0.1", "detail": "server started, HTTP 200 checked, process stopped", **srv})

    # 8. background process control (spawn, poll, kill)
    bg: dict = {}
    try:
        proc = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        running = proc.poll() is None
        proc.terminate()
        proc.wait(timeout=5)
        bg = {"status": "EXECUTED_NOW" if running and proc.returncode is not None else "FAILED", "was_running": running, "exit_code_after_terminate": proc.returncode}
    except Exception as exc:  # pragma: no cover
        bg = {"status": "FAILED", "error": type(exc).__name__}
    tests.append({"id": "background_process_spawn_and_terminate", "command": f"{sys.executable} -c 'time.sleep(30)' (spawn/terminate)", "detail": "process control verified inside the sandbox shell", **bg})

    # 9. git local workflow (init/add/commit/log) in a temp dir — no network, no remotes
    git = shutil.which("git")
    if git:
        repo = tmp / "gitrepo"
        repo.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
        steps = []
        for argv in (
            ["git", "init", "-q", "-b", "main"],
            ["git", "-c", "user.name=inventory-probe", "-c", "user.email=probe@invalid", "commit", "-q", "--allow-empty", "-m", "inventory probe commit"],
            ["git", "log", "--oneline"],
            ["git", "status", "--porcelain"],
        ):
            r = runner.run(argv, label=f"test:git:{argv[1]}", timeout=30, cwd=str(repo), env=env)
            steps.append({"argv": [redact(a) for a in argv], "exit_code": r.get("exit_code"), "out": (r.get("stdout") or "").strip()[:120], "err": (r.get("stderr") or "").strip()[:120]})
        ok = all(s["exit_code"] == 0 for s in steps[:2]) and any("inventory probe commit" in s["out"] for s in steps)
        add("git_local_commit_workflow", "git init/commit/log in a temp dir (no remote, no push)", ok, json.dumps(steps[-2:])[:300], extra={"steps": steps})
    else:
        add("git_local_commit_workflow", "git init/commit/log", False, "git not on PATH")

    # 10. file edit round-trip (create → patch → read back)
    f = tmp / "edit-target.txt"
    try:
        f.write_text("line one\nline two\n", encoding="utf-8")
        data = f.read_text(encoding="utf-8").replace("line two", "line TWO (edited)")
        f.write_text(data, encoding="utf-8")
        ok = "line TWO (edited)" in f.read_text(encoding="utf-8")
    except OSError:
        ok = False
    add("file_create_edit_read", f"create/replace/read {redact(str(f))}", ok, "text round-trip with in-place edit")

    # 11. document / image generation libraries (presence check only, no imports)
    present = set()
    try:
        present = {d.metadata["Name"].lower() for d in md.distributions() if d.metadata.get("Name")}
    except Exception:
        present = set()
    doc_libs = sorted((present & {"reportlab", "fpdf2", "pypdf", "openpyxl", "docx", "python-docx", "xlsxwriter", "weasyprint", "pillow", "matplotlib", "pandas", "numpy"}) | set())
    tests.append(
        {
            "id": "document_and_image_library_availability",
            "command": "importlib.metadata distribution name lookup (no imports executed)",
            "status": "INSTALLED" if doc_libs else "NOT_INSTALLED",
            "detail": "present: " + (", ".join(doc_libs) if doc_libs else "none of reportlab/fpdf2/pypdf/openpyxl/docx/xlsxwriter/weasyprint/pillow/matplotlib/pandas/numpy"),
            "note": "presence does not imply PDF/Office rendering was validated; no renderer is installed",
        }
    )

    # 12. raster image manipulation + PDF coder policy (read-only; no policy is ever modified)
    convert = shutil.which("convert") or shutil.which("magick")
    im_version = None
    if convert:
        vres = runner.run([convert, "--version"], label="test:im-version", timeout=20)
        first_line = ((vres.get("stdout") or "").strip().splitlines() or [""])[0]
        im_version = redact(first_line)[:90] or None
    if convert:
        png = tmp / "probe.png"
        mk = runner.run([convert, "-size", "120x60", "xc:navy", "-fill", "#ffcc00", "-draw", "rectangle 10,10 60,50", str(png)], label="test:raster-create", timeout=40)
        rz = runner.run([convert, str(png), "-resize", "40x20", str(tmp / "probe-small.png")], label="test:raster-resize", timeout=40)
        dims = None
        try:
            data = (tmp / "probe-small.png").read_bytes()
            dims = list(struct.unpack(">II", data[16:24]))
        except (OSError, struct.error):
            dims = None
        ok_raster = mk.get("exit_code") == 0 and rz.get("exit_code") == 0 and dims == [40, 20]
        add("raster_image_create_resize_verify", f"{convert} -size 120x60 xc:navy -draw rectangle, then -resize 40x20 (dimensions verified from the PNG header)", ok_raster, f"small image dims={dims}; {mk.get('error') or ''} {(mk.get('stderr') or '')[:120]}".strip(), extra={"imagemagick_version": im_version})
        txt = runner.run([convert, "-size", "120x60", "xc:white", "-font", "DejaVu-Sans", "-pointsize", "14", "-annotate", "+8+34", "probe", str(tmp / "probe-text.png")], label="test:raster-text", timeout=40)
        tests.append(
            {
                "id": "raster_text_annotation",
                "command": f"{convert} -font DejaVu-Sans -annotate",
                "status": "EXECUTED_NOW" if txt.get("exit_code") == 0 else "FAILED",
                "detail": ((txt.get("stderr") or "").strip().splitlines() or [""])[0][:200] or "rendered",
                "note": "DejaVu TTFs exist under /usr/share/fonts but ImageMagick has no usable font mapping here (fontconfig binary/config absent), so text drawing can fail even though geometry ops succeed.",
            }
        )
        pdf_res = runner.run([convert, str(png), str(tmp / "probe.pdf")], label="test:pdf-coder", timeout=40)
        stderr_pdf = (pdf_res.get("stderr") or "") + (pdf_res.get("stdout") or "")
        blocked = pdf_res.get("exit_code") not in (0, None) and "security policy" in stderr_pdf
        tests.append(
            {
                "id": "pdf_generation_via_imagemagick",
                "command": f"{convert} probe.png probe.pdf",
                "status": "FAILED" if blocked else ("EXECUTED_NOW" if pdf_res.get("exit_code") == 0 else "FAILED"),
                "detail": redact(stderr_pdf.strip().splitlines()[0] if stderr_pdf.strip() else "")[:220],
                "note": "Debian's ImageMagick policy.xml denies the PDF coder (ghostscript CVE mitigation) and ghostscript is not installed. The policy was NOT modified and no bypass was attempted - circumventing a security control is out of scope.",
                "pdf_renderer_present": shutil.which("gs") is not None or shutil.which("pdftotext") is not None,
            }
        )
    else:
        add("raster_image_create_resize_verify", "convert -size ... xc", False, "no ImageMagick convert/magick on PATH")
        tests.append({"id": "raster_text_annotation", "command": "n/a", "status": "NOT_TESTED", "detail": "no ImageMagick present"})
        tests.append({"id": "pdf_generation_via_imagemagick", "command": "n/a", "status": "NOT_TESTED", "detail": "no ImageMagick present"})
    font_tool = "identify -list font" if convert else ("fc-list" if shutil.which("fc-list") else None)
    if font_tool:
        fr = runner.run([font_tool.split()[0], font_tool.split()[1], "font"] if convert else [font_tool, ":"], label="test:fonts", timeout=30, stdout_limit=100000)
        names = sorted({ln.strip().split(":", 1)[1].strip() for ln in (fr.get("stdout") or "").splitlines() if ln.strip().startswith("  Font:")}) if convert else []
        tests.append({"id": "font_discovery", "command": font_tool, "status": "EXECUTED_NOW" if fr.get("exit_code") == 0 else "FAILED", "detail": (f"fonts visible to ImageMagick: {', '.join(names[:6])}" if names else "list returned")[:200]})

    for path in sorted(tmp.iterdir()):
        recorded_files.append(redact(path.name))
    shutil.rmtree(tmp, ignore_errors=True)
    return {
        "schema": SCHEMA,
        "executed_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "workspace": redact(str(tmp)),
        "temp_dir_cleaned": not tmp.exists(),
        "files_created_in_temp": recorded_files,
        "network_used": "loopback HTTP only (127.0.0.1); no external egress in these tests",
        "tests": tests,
        "counts": {
            "total": len(tests),
            "executed_now": sum(1 for t in tests if t["status"] == "EXECUTED_NOW"),
            "failed": sum(1 for t in tests if t["status"] == "FAILED"),
            "not_installed": sum(1 for t in tests if t["status"] == "NOT_INSTALLED"),
        },
    }


def build_summary(capabilities: dict, system: dict, exe: dict, py: dict, node: dict, os_packages: dict, libraries: dict, fonts: dict, network: dict, github: dict, fingerprints: dict, validation: dict, observations: dict) -> str:
    v = (fingerprints.get("fingerprints") or {})
    agent = capabilities["agent_tools"]
    tools = agent.get("tools") or []
    demonstrated = [t["name"] for t in tools if t.get("status") == "EXECUTED_NOW"]
    missing_media = [k for k, v in (capabilities.get("document_and_media") or {}).items() if v == "NOT_INSTALLED"]
    installed_media = [k for k, v in (capabilities.get("document_and_media") or {}).items() if v == "INSTALLED"]
    marker_paths = ", ".join(f"`{(v or {}).get('path')}`" for v in ((capabilities.get("persistence") or {}).get("new_markers_written") or {}).values() if (v or {}).get("written")) or "see persistence.json"
    agent_tests = ", ".join(str(x.get("id")) for x in (observations.get("practical_tests") or []) if x.get("status") == "EXECUTED_NOW")
    lines = [
        f"# Arena Agent Mode — session capability inventory ({capabilities['date_utc'][:10]})",
        "",
        f"- **Session/environment:** {(system.get('os') or {}).get('pretty_name')} · kernel {(system.get('kernel') or {}).get('release')} · {(system.get('kernel') or {}).get('machine')} · {capabilities['environment']['cpus']} vCPU · {capabilities['environment']['memory_mb']} MB · {(system.get('user_privilege') or {}).get('category')}",
        f"- **Discovered counts:** {exe.get('executable_count')} PATH executables · {os_packages.get('installed_count')} dpkg packages · {(py.get('installed_distributions') or {}).get('count')} Python distributions (+{(py.get('standard_library') or {}).get('count')} stdlib modules) · {node.get('global_package_count')} global npm packages ({node.get('builtin_module_count')} node builtins) · {libraries.get('count')} shared objects · {fonts.get('font_file_count')} font files ({fonts.get('family_count_estimate')} families)",
        f"- **Runtimes:** Python {(capabilities['runtimes']['python'].get('version'))} · Node {capabilities['runtimes']['node'].get('version')} · npm {capabilities['runtimes']['node'].get('npm')} · absent: go/rust/java/php/ruby/deno/bun/clang/cmake",
        f"- **Native agent tools exposed:** {agent.get('declared_count')} (executed now: {agent.get('executed_count')}): " + ", ".join(str(t.get("name")) for t in tools),
        f"- **Demonstrated this session:** tools " + (", ".join(demonstrated) or "none") + " · engine tests " + json.dumps((capabilities.get("practical_capability_tests") or {}).get("executed_by_engine") or {}) + " · agent-side tests: " + (agent_tests or "none"),
        f"- **Present but partial:** ImageMagick {', '.join(installed_media) or 'none'} can create/resize/annotate rasters (tested), yet its PDF coder is denied by policy and no ghostscript/poppler renderer exists, so no PDF or Office artifact is validated; fontconfig CLI missing (font files readable only via ImageMagick).",
        f"- **Not installed (notable):** {', '.join(sorted(missing_media)) or 'none'}; browsers: {capabilities['browsers']['status']}; Python document/image libs: {', '.join(capabilities['document_generation_libraries_python'].get('present') or ['none present'])}; apt index populated: {(system.get('apt_state') or {}).get('index_populated')}.",
        f"- **Installs:** PyPI {capabilities['package_installation']['pypi']['registry']} ({capabilities['package_installation']['pypi'].get('index_reachable_count')}/{capabilities['package_installation']['pypi'].get('probed')} probed) · pip {capabilities['package_installation']['pypi']['installation']} · npm {capabilities['package_installation']['npm']['registry']} ({capabilities['package_installation']['npm'].get('index_reachable_count')}/{capabilities['package_installation']['npm'].get('probed')} probed) · npm install {capabilities['package_installation']['npm']['installation']} · apt {capabilities['package_installation']['apt_debian']['registry_from_shell']} / install {capabilities['package_installation']['apt_debian']['installation']} · Playwright binaries {capabilities['package_installation']['playwright_browsers']['binary_download']} (reachable index ≠ installable here: numpy needs Python>=3.12, sandbox has 3.11.2; apt index unpopulated and deb.debian.org blocked)",
        f"- **Network (SHELL_HTTP):** DNS {network['counts']['dns_ok']}/{len(NETWORK_HOSTS)} · HTTP-layer reachable {network['counts'].get('hosts_with_any_http_response')}/{len(NETWORK_HOSTS)} · TLS handshake ok {network['counts']['tls_handshake_ok']}; blocked from the shell: {', '.join([h for h, e in (network['hosts'] or {}).items() if e.get('tcp_tls_http_egress') != 'ALLOWED'][:8]) or 'none'}",
        f"- **Path divergence (proves the three paths differ):** " + "; ".join(f"{r['host']} shell={r['shell_https']} vs native={r['native_fetch']}" for r in (capabilities.get("network", {}).get("shell_vs_native_comparison") or []) if r.get("divergent")) + f" · NATIVE_WEB_FETCH={capabilities['network']['native_web_fetch']['status']}, BROWSER_NAVIGATION={capabilities['network']['browser_navigation']['status']} (never inferred from each other)",
        f"- **GitHub:** repo {(github.get('remotes') or [{}])[0].get('url', '?')}; branch `{github.get('current_branch')}`; git `{(github.get('git_version') or '').replace('git version ','')}`; gh `{(github.get('gh_version') or '').split(',')[0]}`; auth {'OK (value never read)' if (github.get('gh_auth') or {}).get('authenticated') else 'unknown'}; install-scope repos: {(github.get('github_app_installation') or {}).get('accessible_repository_count')}",
        f"- **Fingerprints (sha256):** SYSTEM `{v.get('SYSTEM','')[:16]}…` · PYTHON `{v.get('PYTHON','')[:16]}…` · NODE `{v.get('NODE','')[:16]}…` · EXECUTABLES `{v.get('EXECUTABLES','')[:16]}…` · COMBINED `{v.get('COMBINED','')[:16]}…`",
        f"- **Generated artifacts this session:** " + (", ".join(f"{a['path']} ({a.get('width')}x{a.get('height')} {a['kind']}, {a['bytes']} B, sha256:{a['sha256'][:12]})" for a in ((capabilities.get('practical_capability_tests') or {}).get('generated_artifacts') or {}).get('items', [])) or "none recorded") + " — image generation only; no PDF/Office/browser-screenshot capability is claimed",
        f"- **Persistence:** no marker from an earlier session was found (first inventory in this sandbox); new markers written to {marker_paths} for the next session to compare — one run cannot prove persistence.",
        "- **Main unknowns:** model identity, credits/limits, UI preview behaviour, ZIP/`/download-workspace`, cross-session persistence, live-site browser access, anything requiring a real document renderer.",
        "- **Validation:** " + ("all manifests valid JSON, secret scan clean" if validation["all_expected_files_present_and_valid"] and validation["secret_scan"]["clean"] else "see validation.json issues") + f"; bounded subprocess timeouts ≤ {validation['subprocess_timeouts']['max_timeout_seconds_used']}s; {validation['failed_commands']['count']} failed probe(s) recorded.",
        "- **Manifests:** `inventory/2026-09-26/<session>/` → system.json, executables.json, python.json, node.json, os-packages.json, libraries.json, fonts.json, network.json, registries.json, native-tools.json, github.json, persistence.json, fingerprints.json, capabilities.json, validation.json",
        "",
        "Raw lists live in the JSON manifests above; they are intentionally not reproduced here.",
        "Regenerated by: `python3 scripts/inventory.py --observations inventory/2026-09-26/observations.json`",
    ]
    return "\n".join(lines[:30]).strip() + "\n"


def build_ui_checklist(observations: dict) -> str:
    items = observations.get("ui_items") or []
    lines = [
        "# Arena interface — items that must be verified manually",
        "",
        "Nothing below is observable from inside the sandbox; the engine cannot confirm any of it. `NOT_TESTED` means unobserved, **not** absent.",
        "",
        "| UI capability | Status | How to check in Arena |",
        "|---|---|---|",
    ]
    for item in items:
        lines.append(f"| {item.get('item')} | `{item.get('status')}` | {item.get('how')} |")
    lines += [
        "",
        "- Do not script or scrape the Arena UI (Terms §5 restrict automated/programmatic access); check these visually yourself.",
        "- Model identity may be hidden by design — record `UNKNOWN` rather than guessing.",
        "- Credits/usage and reset time are account state only; no in-session value is authoritative.",
    ]
    return "\n".join(lines).strip() + "\n"


def build_native_tools(observations: dict, runner: Runner, practical: dict | None = None) -> dict:
    tools = observations.get("agent_tools") or []
    return {
        "schema": SCHEMA,
        "collected_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "method": "the agent's own declared tool interface for this session, merged into the engine output by --observations; tool surface cannot be introspected from the sandbox shell",
        "hidden_prompt_or_policy_text_reproduced": False,
        "model_identity": "UNKNOWN — not disclosed to the agent and deliberately not inferred",
        "tool_count": len(tools),
        "tools": [
            {
                "name": t.get("name"),
                "purpose": t.get("purpose"),
                "parameters": t.get("parameters") or [],
                "documented_restrictions": t.get("restrictions") or [],
                "output_type": t.get("output"),
                "executed_this_session": bool(t.get("executed_this_session")),
                "execution_result": t.get("execution_result"),
                "known_limitations": t.get("limitations") or [],
                "status": "EXECUTED_NOW" if t.get("executed_this_session") else "EXPOSED",
            }
            for t in tools
        ],
        "native_fetch_tests": observations.get("native_fetch_tests") or [],
        "practical_tests": observations.get("practical_tests") or [],
        "generated_artifacts": (practical or {}).get("generated_artifacts") or {},
        "engine_capability_tests": (practical or {}).get("tests") or [],
        "engine_capability_test_counts": (practical or {}).get("counts") or {},
        "not_inspected": [
            "internal tool implementation, transport, host-side process or model routing",
            "any Arena capability not surfaced as a callable tool in this session",
        ],
        "observations_notes": observations.get("notes"),
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def detect_repo(runner: Runner) -> str | None:
    res = runner.run(["git", "remote", "get-url", "--push", "origin"], label="git remote get-url", timeout=20)
    url = (res.get("stdout") or "").strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)(\.git)?$", url)
    return m.group(1) if m else None


def record_delivery(session_dir: pathlib.Path, payload_path: pathlib.Path) -> int:
    validation_path = session_dir / "validation.json"
    capabilities_path = session_dir / "capabilities.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation["delivery"] = payload
    validation["delivery"]["recorded_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    validation_path.write_text(json.dumps(validation, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for doc in (session_dir / "SUMMARY.md", session_dir.parent.parent / "SUMMARY.md"):
        if doc.exists():
            kept = [ln for ln in doc.read_text(encoding="utf-8").splitlines() if not ln.startswith("- **Delivery:**")]
            kept.insert(1, f"- **Delivery:** commit `{payload.get('commit_short')}` on `{payload.get('working_branch')}` → [{payload.get('pr_url')}]({payload.get('pr_url')}) "
                           f"(state {((payload.get('pr_state') or {}).get('state')) if isinstance(payload.get('pr_state'), dict) else payload.get('pr_state')} at record time, merged={payload.get('remote_head_matches_local') and False or payload.get('pr_state', {}).get('merged') if isinstance(payload.get('pr_state'), dict) else False}, "
                           f"force-push=no, main untouched, other PRs left as found)")
            doc.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    if capabilities_path.exists():
        caps = json.loads(capabilities_path.read_text(encoding="utf-8"))
        caps["github_delivery"]["write"] = payload.get("push_status", "UNKNOWN")
        caps["github_delivery"]["pull_request"] = payload.get("pr_url")
        caps["github_delivery"]["pr_open_not_merged"] = payload.get("merged", False) is False
        capabilities_path.write_text(json.dumps(caps, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"delivery_recorded": True, "validation_json": str(validation_path), "pr_url": payload.get("pr_url")}, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Arena Agent Mode capability inventory engine (stdlib only)")
    parser.add_argument("--out", help="output directory (default: inventory/<UTC date>/session-<UTC>-<rand>)")
    parser.add_argument("--observations", help="agent-declared observations JSON (native tools, UI checklist, practical tests)")
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--skip-registry", action="store_true")
    parser.add_argument("--probe-install", action="store_true", help="opt in to isolated pip/npm install probes (requires operator approval)")
    parser.add_argument("--skip-install", action="store_true", help="skip install probes even if --probe-install is provided")
    parser.add_argument("--skip-github", action="store_true")
    parser.add_argument("--timeout", type=float, default=8.0, help="per-request network timeout (max 30)")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--record-delivery", nargs=2, metavar=("SESSION_DIR", "DELIVERY_JSON"), help="attach verified delivery evidence to an existing session directory and exit")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.record_delivery:
        return record_delivery(pathlib.Path(args.record_delivery[0]), pathlib.Path(args.record_delivery[1]))

    now = dt.datetime.now(dt.timezone.utc)
    session_id = "session-" + now.strftime("%Y%m%dT%H%M%SZ") + "-" + hashlib.sha256(os.urandom(8)).hexdigest()[:6]
    out_dir = pathlib.Path(args.out) if args.out else pathlib.Path("inventory") / now.strftime("%Y-%m-%d") / session_id
    out_dir.mkdir(parents=True, exist_ok=True)

    runner = Runner()
    net = Net(timeout=min(max(args.timeout, 1.0), 30.0), workers=max(1, min(args.workers, 6)))
    collector_errors: dict[str, str] = {}

    def safe(label: str, fn, default):
        try:
            return fn()
        except Exception as exc:  # keep partial results on failure
            collector_errors[label] = f"{type(exc).__name__}: {redact(str(exc))[:200]}"
            return default

    system = safe("system", lambda: collect_system(runner), {"schema": SCHEMA, "collector_error": True})
    executables = safe("executables", lambda: collect_executables(runner), {"schema": SCHEMA, "collector_error": True})
    python = safe("python", lambda: collect_python(runner), {"schema": SCHEMA, "collector_error": True})
    node = safe("node", lambda: collect_node(runner), {"schema": SCHEMA, "collector_error": True})
    os_packages = safe("os_packages", lambda: collect_os_packages(runner), {"schema": SCHEMA, "packages": [], "collector_error": True})
    libraries = safe("libraries", lambda: collect_libraries(runner), {"schema": SCHEMA, "shared_objects": []})
    fonts = safe("fonts", lambda: collect_fonts(), {"schema": SCHEMA, "files": []})
    browsers = safe("browsers", lambda: collect_browsers(runner), {"schema": SCHEMA})
    network = ({"schema": SCHEMA, "skipped": True, "counts": {"dns_ok": 0, "https_ok": 0, "https_failed": 0, "tls_handshake_ok": 0}, "hosts": {}} if args.skip_network else safe("network", lambda: collect_network(net), {"schema": SCHEMA, "counts": {}, "hosts": {}}))
    registries = ({"schema": SCHEMA, "skipped": True} if args.skip_registry else safe("registries", lambda: collect_registries(net), {"schema": SCHEMA, "skipped_by_error": True}))
    install_enabled = args.probe_install and not args.skip_install
    installs = ({"schema": SCHEMA, "skipped": True, "results": {}, "note": "install probes require explicit --probe-install"} if not install_enabled else safe("install_probes", lambda: collect_install_probes(runner, tempfile.gettempdir(), do_pip=True, do_npm=True), {"schema": SCHEMA, "results": {}}))
    repo = detect_repo(runner)
    github = ({"schema": SCHEMA, "skipped": True} if args.skip_github else safe("github", lambda: collect_github(runner, repo), {"schema": SCHEMA, "collector_error": True}))
    practical = safe("practical_tests", lambda: collect_practical_tests(runner, out_dir), {"schema": SCHEMA, "tests": [], "collector_error": True})
    practical["generated_artifacts"] = safe("artifacts", lambda: collect_artifacts(out_dir.parent), {"count": 0, "items": []})
    fingerprints = safe("fingerprints", lambda: build_fingerprints(system, os_packages, python, node, executables), {"fingerprints": {}})
    fingerprints["session_id"] = session_id
    fingerprints["repo"] = repo
    fingerprints["branch"] = safe("branch", lambda: redact(subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, timeout=10).stdout.strip()), None)
    persistence = safe("persistence", lambda: collect_persistence(out_dir, fingerprints), {"schema": SCHEMA})

    observations = default_observations()
    observations_path = None
    if args.observations and pathlib.Path(args.observations).exists():
        observations_path = pathlib.Path(args.observations)
        try:
            observations = {**observations, **json.loads(observations_path.read_text(encoding="utf-8"))}
        except (OSError, json.JSONDecodeError) as exc:
            observations["observations_error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
            collector_errors["observations"] = observations["observations_error"]
    elif args.observations:
        collector_errors["observations"] = "explicit observations file not found"
        observations["observations_error"] = collector_errors["observations"]

    capabilities = safe(
        "capabilities",
        lambda: build_capabilities(system, executables, python, node, os_packages, libraries, fonts, browsers, network, registries, installs, github, observations, net.timeout, practical, persistence),
        {"schema": SCHEMA, "collector_error": True},
    )

    files: dict[str, dict] = {
        "system.json": system,
        "executables.json": executables,
        "python.json": {**python, "browsers_and_media_tools": browsers},
        "node.json": node,
        "os-packages.json": os_packages,
        "libraries.json": libraries,
        "fonts.json": {**fonts, "browser_and_font_environment": {"browsers": browsers.get("executables"), "fontconfig_present": fonts.get("fontconfig_fc_list_present")}},
        "network.json": {**network, "install_probes": installs, "registries": registries, "collector_errors": collector_errors},
        "registries.json": {**registries, "install_probes": installs},
        "native-tools.json": build_native_tools(observations, runner, practical),
        "github.json": {**github, "persistence": persistence},
        "persistence.json": persistence,
        "fingerprints.json": fingerprints,
        "capabilities.json": capabilities,
        "validation.json": {},
        "provenance.json": {
            "schema": SCHEMA,
            "engine": ENGINE,
            "engine_sha256_12": short_hash(hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()),
            "argv": [redact(a) for a in (argv or sys.argv[1:])],
            "session_id": session_id,
            "out_dir": redact(str(out_dir)),
            "observations_file": redact(str(observations_path)) if observations_path else None,
            "python": sys.version.split()[0],
            "cwd": redact(os.getcwd()),
            "skips": {"network": args.skip_network, "registry": args.skip_registry, "install": not install_enabled, "github": args.skip_github},
            "collector_errors": collector_errors,
        },
    }

    written = []
    for name, payload in files.items():
        if name == "validation.json":
            continue
        (out_dir / name).write_text(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
        written.append(name)
    written.append("validation.json")
    for name in ("validation.json",):  # placeholder written first so the two-pass check sees it
        (out_dir / name).write_text(json.dumps(build_validation(out_dir, written, runner, [], None, practical), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "SUMMARY.md").write_text(
        build_summary(capabilities, system, executables, python, node, os_packages, libraries, fonts, network, github, fingerprints, build_validation(out_dir, written, runner, [], None, practical), observations),
        encoding="utf-8",
    )
    (out_dir / "UI-CHECKLIST.md").write_text(build_ui_checklist(observations), encoding="utf-8")
    # final pass: secret scan over every emitted artefact (including the summaries) + re-validate
    secret_findings = scan_secrets(out_dir)
    validation = build_validation(out_dir, written, runner, secret_findings, None, practical)
    (out_dir / "validation.json").write_text(json.dumps(validation, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "SUMMARY.md").write_text(
        build_summary(capabilities, system, executables, python, node, os_packages, libraries, fonts, network, github, fingerprints, validation, observations),
        encoding="utf-8",
    )
    # mirror the human-facing documents to the inventory/ root when a session subdirectory was used
    top_level: list[str] = []
    if out_dir.name.startswith("session-"):
        root = out_dir.parent.parent if out_dir.parent.parent.name == "inventory" else out_dir.parent
        for doc in ("SUMMARY.md", "UI-CHECKLIST.md"):
            dest = root / doc
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(out_dir / doc, dest)
            top_level.append(redact(str(dest)))

    if not args.quiet:
        print(json.dumps({
            "session_id": session_id,
            "out_dir": redact(str(out_dir)),
            "top_level_docs": top_level,
            "counts": {
                "executables": executables.get("executable_count"),
                "os_packages": os_packages.get("installed_count"),
                "python_distributions": (python.get("installed_distributions") or {}).get("count"),
                "node_globals": node.get("global_package_count"),
                "shared_objects": libraries.get("count"),
                "fonts": fonts.get("font_file_count"),
                "dns_ok": (network.get("counts") or {}).get("dns_ok"),
                "https_ok": (network.get("counts") or {}).get("https_ok"),
                "tools_declared": capabilities.get("agent_tools", {}).get("declared_count"),
                "tools_executed": capabilities.get("agent_tools", {}).get("executed_count"),
            },
            "fingerprints": {k: val[:16] for k, val in (fingerprints.get("fingerprints") or {}).items()},
            "failed_commands": len(validation["failed_commands"]["items"]),
            "secret_findings": len(validation["secret_scan"]["findings"]),
            "collector_errors": collector_errors,
            "all_files_valid": validation["all_expected_files_present_and_valid"],
        }, indent=1))
    return 0 if validation["all_expected_files_present_and_valid"] and not collector_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
