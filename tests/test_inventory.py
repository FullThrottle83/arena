#!/usr/bin/env python3
"""Regression tests for ``scripts/inventory.py`` — Python standard library only.

Covered, in five bounded areas:

1. secret redaction and the structural secret scan;
2. missing / malformed ``--observations`` input;
3. install probes staying opt-in (``--probe-install``, ``--skip-install``);
4. manifest generation and validation semantics;
5. persistence-marker semantics (one run cannot prove persistence).

What these tests never do: perform network I/O, install or execute a package,
run a real inventory, modify the committed 2026-09-26 evidence snapshot, or
write into the repository. Every collector that touches the system is replaced
by a fixed synthetic payload before ``main()`` is called, so a passing suite is
**not** capability evidence — it only pins engine behaviour.

Documented exception: ``collect_persistence()`` hardcodes ``/tmp``, so the
persistence tests write one uniquely named marker there (never the production
``arena-inventory-marker.json``) and delete it again during cleanup.

Run:  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ENGINE_PATH = REPO_ROOT / "scripts" / "inventory.py"


def _load_engine():
    """Load ``scripts/inventory.py`` by path.

    Importing it by name would be ambiguous: the repository also contains an
    ``inventory/`` data directory.
    """
    spec = importlib.util.spec_from_file_location("arena_inventory_engine", ENGINE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


inventory = _load_engine()
SCHEMA = inventory.SCHEMA

# Synthetic credential-shaped strings, constructed rather than captured; none of
# them is a real secret (docs/data-handling.md: synthetic fixtures only). The
# recognisable prefixes are assembled from parts so that this test file itself
# never contains a literal token that GitHub secret scanning / push protection
# would reject; the runtime values are exactly the shapes redact() must catch.
FAKE_GITHUB_TOKEN = "ghp" + "_" + "Synthetic0" * 4
FAKE_FINE_GRAINED_TOKEN = "github" + "_pat_" + "Synthetic0" * 4
FAKE_SLACK_TOKEN = "xox" + "b-" + "1234567890-abcdefghij"
FAKE_AWS_KEY = "AK" + "IA" + "SYNTHETIC0ABCDEF"
FAKE_JWT = "eyJ" + "a" * 20 + "." + "b" * 20 + "." + "c" * 12
FAKE_PRIVATE_KEY_HEADER = "-----BEGIN RSA " + "PRIVATE KEY-----"
FAKE_CREDENTIAL_URL = "https://synthetic-user:synthetic-password@host.invalid/path"
FAKE_AUTH_HEADER = "Authorization: Bearer syntheticbearervalue"
FAKE_ASSIGNMENT = "GITHUB" + "_TOKEN=" + "Synthetic0" * 4

SAFE_JSON = "Synthetic0" * 4  # 40-char value used only where it must be detected


@contextlib.contextmanager
def working_directory(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield pathlib.Path(path)
    finally:
        os.chdir(previous)


def read_json(path: pathlib.Path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


class TestSecretRedaction(unittest.TestCase):
    """``redact()`` / ``redact_bytes()`` strip identity and credential material."""

    def test_home_path_and_hostname_are_replaced(self):
        out = inventory.redact(f"cwd={inventory._HOME}/arena host={inventory._HOSTNAME}")
        self.assertIn("~/arena", out)
        self.assertIn("<host>", out)
        self.assertNotIn(inventory._HOME, out)
        if inventory._HOSTNAME:
            self.assertNotIn(inventory._HOSTNAME, out)

    def test_credential_shapes_are_replaced(self):
        cases = [
            (FAKE_GITHUB_TOKEN, "<REDACTED_TOKEN>"),
            (FAKE_FINE_GRAINED_TOKEN, "<REDACTED_TOKEN>"),
            (FAKE_SLACK_TOKEN, "<REDACTED_TOKEN>"),
            (FAKE_AWS_KEY, "<REDACTED_KEY>"),
            (FAKE_JWT, "<REDACTED_JWT>"),
            (FAKE_PRIVATE_KEY_HEADER, "-----<REDACTED PRIVATE KEY>-----"),
            (FAKE_CREDENTIAL_URL, "<scheme>://<redacted>@"),
        ]
        for secret, marker in cases:
            with self.subTest(marker=marker):
                out = inventory.redact(f"prefix {secret} suffix")
                self.assertIn(marker, out)
                self.assertNotIn(secret, out)

    def test_url_userinfo_credentials_do_not_survive(self):
        out = inventory.redact(FAKE_CREDENTIAL_URL)
        self.assertNotIn("synthetic-password", out)
        self.assertNotIn("synthetic-user", out)
        self.assertTrue(out.endswith("@host.invalid/path"))

    def test_authorization_header_value_is_fully_redacted(self):
        out = inventory.redact(FAKE_AUTH_HEADER)
        self.assertEqual(out, "authorization: <REDACTED>")
        self.assertNotIn("syntheticbearervalue", out)
        self.assertEqual(inventory.find_secrets_in_text(FAKE_AUTH_HEADER), ["AUTH_HEADER"])
        for scheme in ("Bearer", "Basic", "Token"):
            with self.subTest(scheme=scheme):
                original = f"prefix\\nAuthorization: {scheme} syntheticvalue\\nnext line"
                redacted = inventory.redact(original)
                self.assertNotIn("syntheticvalue", redacted)
                self.assertIn("authorization: <REDACTED>", redacted)
                self.assertIn("next line", redacted)

    def test_authorization_header_is_redacted_in_command_output(self):
        runner = inventory.Runner()
        result = runner.run(
            [sys.executable, "-c", "print('Authorization: Bearer syntheticbearervalue')"],
            label="synthetic authorization header", timeout=5,
        )
        self.assertEqual(result["exit_code"], 0)
        self.assertNotIn("syntheticbearervalue", json.dumps(result))
        self.assertIn("authorization: <REDACTED>", result["stdout"])

    def test_structural_credential_assignment_is_redacted(self):
        out = inventory.redact(FAKE_ASSIGNMENT)
        self.assertEqual(out, 'GITHUB' + '_TOKEN: "<REDACTED>"')
        self.assertNotIn(SAFE_JSON, out)

    def test_benign_output_is_left_alone(self):
        for text in (
            "git version 2.39.5",
            '"token_values_stored": false',
            '"credential_values_stored": false',
            "note: no credential values are stored",
            "Python 3.11.2 (main, Apr  8 2026, 01:58:00) [GCC 12.2.0]",
        ):
            with self.subTest(text=text):
                self.assertEqual(inventory.redact(text), text)

    def test_empty_input_is_returned_unchanged(self):
        self.assertEqual(inventory.redact(""), "")

    def test_redact_bytes_decodes_and_tolerates_invalid_utf8(self):
        self.assertEqual(inventory.redact_bytes(("token " + FAKE_GITHUB_TOKEN).encode()), "token <REDACTED_TOKEN>")
        self.assertNotIn(FAKE_GITHUB_TOKEN, inventory.redact_bytes(FAKE_GITHUB_TOKEN.encode()))
        inventory.redact_bytes(b"\xff\xfe not utf-8 " + FAKE_AWS_KEY.encode())  # must not raise


class TestStructuralSecretScan(unittest.TestCase):
    """``find_secret_lines()`` / ``scan_secrets()`` report locations, never values."""

    def test_credential_assignment_is_reported_by_line_number_only(self):
        text = '\n'.join(['{', f'  "github_token": "{SAFE_JSON}",', '}'])
        hits = inventory.find_secret_lines(text)
        self.assertEqual(hits, [{"pattern": "CREDENTIAL_ASSIGNMENT", "line": 2}])
        self.assertNotIn(SAFE_JSON, json.dumps(hits))

    def test_inventory_boolean_flags_are_not_false_positives(self):
        safe_lines = [
            '"environment_values_stored": false',
            '"token_values_stored": false',
            '"credential_values_stored": false',
            '"machine_hostname_stored": false',
            '"secrets_read": false',
            '"api_key_count": 0',
            '"password_check": "not_attempted"',
            '"tls_verification_disabled": false',
            '"note": "no credential values are stored"',
            '"secret_scan": {"clean": true, "findings": []}',
        ]
        for line in safe_lines:
            with self.subTest(line=line):
                self.assertEqual(inventory.find_secret_lines(line), [])
        # negative control: the same shape with a real-looking value is caught
        self.assertEqual(inventory.find_secrets_in_text(f'"github_token": "{SAFE_JSON}"'), ["CREDENTIAL_ASSIGNMENT"])

    def test_token_shapes_are_reported_with_their_pattern_name(self):
        text = f"line one\nline two {FAKE_GITHUB_TOKEN} and {FAKE_AWS_KEY}\nline three"
        hits = inventory.find_secret_lines(text)
        self.assertEqual(sorted(h["pattern"] for h in hits), ["AWS_ACCESS_KEY", "GITHUB_TOKEN"])
        self.assertEqual([h["line"] for h in hits], [2, 2])
        self.assertEqual(inventory.find_secrets_in_text(text), ["AWS_ACCESS_KEY", "GITHUB_TOKEN"])

    def test_scan_secrets_reports_files_without_storing_snippets(self):
        with tempfile.TemporaryDirectory(prefix="arena-scan-") as tmp:
            session = pathlib.Path(tmp)
            (session / "clean.json").write_text(json.dumps({"schema": SCHEMA, "ok": True}, indent=1), encoding="utf-8")
            (session / "dirty.json").write_text(f'{{"leak": "{FAKE_GITHUB_TOKEN}"}}\n', encoding="utf-8")
            findings = inventory.scan_secrets(session)
        reported = [f for f in findings if f["file"].endswith("dirty.json")]
        self.assertEqual(len(reported), 1)
        self.assertEqual(reported[0]["pattern"], "GITHUB_TOKEN")
        self.assertEqual(reported[0]["line"], 1)
        self.assertIs(reported[0]["snippet_stored"], False)
        self.assertEqual([f for f in findings if f["file"].endswith("clean.json")], [])
        self.assertNotIn(FAKE_GITHUB_TOKEN, json.dumps(findings))

    def test_engine_self_scan_stays_clean(self):
        # scan_secrets() always appends scripts/inventory.py, and production
        # asserts validation.json -> secret_scan.clean; a hit here would make
        # every real run report a dirty session directory.
        with tempfile.TemporaryDirectory(prefix="arena-scan-empty-") as tmp:
            self.assertEqual(inventory.scan_secrets(pathlib.Path(tmp)), [])


class TestObservationHandling(unittest.TestCase):
    """Native-tool input is operator-declared; absence must stay visible."""

    def test_default_observations_declare_no_tools(self):
        defaults = inventory.default_observations()
        self.assertEqual(
            sorted(defaults),
            ["agent_tools", "native_fetch_tests", "notes", "practical_tests", "ui_items"],
        )
        for key in ("agent_tools", "native_fetch_tests", "practical_tests", "ui_items"):
            self.assertEqual(defaults[key], [])
        self.assertIn("cannot be introspected", defaults["notes"])

    def test_native_tools_survive_missing_and_null_observations(self):
        for observations in ({}, {"agent_tools": None, "native_fetch_tests": None, "ui_items": None}):
            with self.subTest(observations=sorted(observations)):
                payload = inventory.build_native_tools(observations, inventory.Runner())
                self.assertEqual(payload["schema"], SCHEMA)
                self.assertEqual(payload["tool_count"], 0)
                self.assertEqual(payload["tools"], [])
                self.assertEqual(payload["native_fetch_tests"], [])
                self.assertIs(payload["hidden_prompt_or_policy_text_reproduced"], False)
                self.assertTrue(payload["model_identity"].startswith("UNKNOWN"))

    def test_declared_tools_are_exposed_until_they_are_executed(self):
        payload = inventory.build_native_tools(
            {"agent_tools": [{"name": "synthetic_tool"}, {"name": "synthetic_tool_2", "executed_this_session": True, "execution_result": "ok"}]},
            inventory.Runner(),
        )
        self.assertEqual(payload["tool_count"], 2)
        self.assertEqual([t["status"] for t in payload["tools"]], ["EXPOSED", "EXECUTED_NOW"])
        self.assertIs(payload["tools"][0]["executed_this_session"], False)

    def test_ui_checklist_keeps_the_not_tested_caveat_without_observations(self):
        text = inventory.build_ui_checklist({})
        self.assertIn("NOT_TESTED", text)
        self.assertIn("**not** absent", text)
        self.assertIn("Terms §5", text)
        self.assertEqual([ln for ln in text.splitlines() if ln.startswith("| ")][1:], [])  # header row only

    def test_shell_and_native_network_paths_are_never_merged(self):
        network = {"hosts": {"allowed.invalid": {"tcp_tls_http_egress": "ALLOWED"}, "blocked.invalid": {"tcp_tls_http_egress": "BLOCKED"}}}
        observations = {
            "native_fetch_tests": [
                {"host": "allowed.invalid", "result": "ok: 1 chunk"},
                {"host": "blocked.invalid", "result": "ok: fetched natively"},
                {"host": "unprobed.invalid", "result": "failed"},
            ]
        }
        rows = {r["host"]: r for r in inventory._path_divergence(network, observations)}
        self.assertIs(rows["allowed.invalid"]["divergent"], False)
        self.assertIs(rows["blocked.invalid"]["divergent"], True)  # shell blocked, native ok
        self.assertEqual(rows["unprobed.invalid"]["shell_https"], "NOT_PROBED")
        self.assertIsNone(rows["unprobed.invalid"]["divergent"])

    def test_path_divergence_tolerates_missing_native_tests(self):
        network = {"hosts": {"allowed.invalid": {"tcp_tls_http_egress": "ALLOWED"}}}
        self.assertEqual(inventory._path_divergence(network, {}), [])
        self.assertEqual(inventory._path_divergence(network, {"native_fetch_tests": None}), [])
        self.assertEqual(inventory._path_divergence({}, {"native_fetch_tests": [{"host": "x.invalid", "result": "ok"}]})[0]["shell_https"], "NOT_PROBED")


class TestManifestGeneration(unittest.TestCase):
    """Fingerprints, canonical JSON and validation of a complete manifest set."""

    SYSTEM = {"os": {"id": "linux", "pretty_name": "Synthetic Test OS"}, "kernel": {"release": "6.1.0", "machine": "x86_64"},
              "cpu": {"logical": 2}, "memory_kb": {"MemTotal": 2048000}, "rlimits": {}, "disk": {}}
    PACKAGES = {"packages": [{"package": "synthetic", "version": "1.0"}]}
    PYTHON = {"active_interpreter": {"version": "3.11.2", "implementation": "CPython"}, "installed_distributions": {"items": []}}
    NODE = {"runtime": {"version": "20.0.0"}, "global_packages": []}
    EXECUTABLES = {"executables": ["python3"], "executable_count": 1,
                   "version_probes": {"python3": {"present_on_path": True, "version_parsed": "3.11.2"}}}

    def build(self, **overrides):
        args = {"system": self.SYSTEM, "os_packages": self.PACKAGES, "python": self.PYTHON, "node": self.NODE, "executables": self.EXECUTABLES}
        args.update(overrides)
        return inventory.build_fingerprints(args["system"], args["os_packages"], args["python"], args["node"], args["executables"])

    def test_fingerprints_are_deterministic_and_well_formed(self):
        first, second = self.build(), self.build()
        self.assertEqual(first["fingerprints"], second["fingerprints"])
        self.assertEqual(sorted(first["fingerprints"]), ["COMBINED", "EXECUTABLES", "NODE", "PYTHON", "SYSTEM"])
        for name, digest in first["fingerprints"].items():
            with self.subTest(fingerprint=name):
                self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(sorted(first["field_documentation"]), sorted(first["fingerprints"]))
        self.assertIn("sha256", first["algorithm"])
        self.assertTrue(first["excluded_from_fingerprints"])

    def test_fingerprints_ignore_volatile_fields_but_track_real_drift(self):
        baseline = self.build()["fingerprints"]
        volatile = self.build(system={**self.SYSTEM, "collected_utc": "2099-12-31T23:59:59+00:00", "session_id": "session-other"})
        self.assertEqual(volatile["fingerprints"], baseline, "timestamps/session ids must not change a fingerprint")
        drifted = self.build(system={**self.SYSTEM, "kernel": {"release": "6.2.0", "machine": "x86_64"}})["fingerprints"]
        self.assertNotEqual(drifted["SYSTEM"], baseline["SYSTEM"])
        self.assertNotEqual(drifted["COMBINED"], baseline["COMBINED"])
        self.assertEqual(drifted["NODE"], baseline["NODE"], "an unrelated section must stay stable")

    def test_fingerprints_survive_empty_collector_output(self):
        payload = inventory.build_fingerprints({}, {}, {}, {}, {})
        self.assertEqual(sorted(payload["fingerprints"]), ["COMBINED", "EXECUTABLES", "NODE", "PYTHON", "SYSTEM"])

    def test_canonical_json_is_key_order_insensitive(self):
        self.assertEqual(inventory.canonical({"b": 2, "a": 1}), inventory.canonical({"a": 1, "b": 2}))
        self.assertEqual(inventory.canonical({"a": 1}), b'{"a":1}')

    def write_session(self, directory: pathlib.Path, names=None):
        directory.mkdir(parents=True, exist_ok=True)
        for name in names if names is not None else inventory.REQUIRED_FILES:
            (directory / name).write_text(json.dumps({"schema": SCHEMA, "file": name}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return directory

    def test_complete_manifest_set_validates(self):
        with tempfile.TemporaryDirectory(prefix="arena-manifests-") as tmp:
            session = self.write_session(pathlib.Path(tmp) / "session-test")
            validation = inventory.build_validation(session, list(inventory.REQUIRED_FILES), inventory.Runner(), [], None, None)
        self.assertTrue(validation["all_expected_files_present_and_valid"])
        self.assertEqual(validation["missing_or_invalid"], [])
        self.assertEqual(validation["expected_files"], inventory.REQUIRED_FILES)
        self.assertEqual(len(validation["file_checks"]), len(inventory.REQUIRED_FILES))
        self.assertTrue(all(c["ok"] and c["json_valid"] and c["bytes"] > 0 for c in validation["file_checks"]))

    def test_missing_corrupt_and_extra_files_are_reported(self):
        with tempfile.TemporaryDirectory(prefix="arena-manifests-") as tmp:
            session = self.write_session(pathlib.Path(tmp) / "session-test")
            runner = inventory.Runner()

            os.remove(session / "capabilities.json")
            validation = inventory.build_validation(session, list(inventory.REQUIRED_FILES), runner, [], None, None)
            self.assertFalse(validation["all_expected_files_present_and_valid"])
            self.assertEqual(validation["missing_or_invalid"], ["capabilities.json"])
            self.write_session(session, ["capabilities.json"])

            (session / "network.json").write_text("{not json", encoding="utf-8")
            validation = inventory.build_validation(session, list(inventory.REQUIRED_FILES), runner, [], None, None)
            self.assertFalse(validation["all_expected_files_present_and_valid"])
            self.assertEqual(validation["missing_or_invalid"], ["network.json"])
            check = next(c for c in validation["file_checks"] if c["file"] == "network.json")
            self.assertIs(check["json_valid"], False)
            self.assertIn("JSONDecodeError", check["json_error"])
            self.write_session(session, ["network.json"])

            (session / "SUMMARY.md").write_text("# synthetic summary\n", encoding="utf-8")
            validation = inventory.build_validation(session, list(inventory.REQUIRED_FILES), runner, [], None, None)
            self.assertTrue(validation["all_expected_files_present_and_valid"], "a human-facing extra document must not fail validation")
            self.assertIn("SUMMARY.md", validation["extra_files_beyond_required"])

            (session / "broken-extra.json").write_text("{oops", encoding="utf-8")
            validation = inventory.build_validation(session, list(inventory.REQUIRED_FILES), runner, [], None, None)
            self.assertFalse(validation["all_expected_files_present_and_valid"], "an invalid extra JSON file must fail validation")
            self.assertIn("broken-extra.json", validation["extra_files_beyond_required"])

    def test_validation_records_the_safety_envelope(self):
        runner = inventory.Runner()
        runner.run([sys.executable, "-c", "raise SystemExit(3)"], label="synthetic failing probe", timeout=3)
        with tempfile.TemporaryDirectory(prefix="arena-manifests-") as tmp:
            session = self.write_session(pathlib.Path(tmp) / "session-test")
            validation = inventory.build_validation(session, list(inventory.REQUIRED_FILES), runner, [], None, None)
        self.assertIs(validation["environment_values_stored"], False)
        self.assertIs(validation["network_safety"]["tls_verification_disabled"], False)
        self.assertIs(validation["network_safety"]["arena_platform_automated_access"], False)
        self.assertIs(validation["privacy"]["machine_hostname_stored"], False)
        self.assertIs(validation["privacy"]["credential_values_stored"], False)
        self.assertTrue(validation["subprocess_timeouts"]["all_calls_bounded"])
        self.assertEqual(validation["subprocess_timeouts"]["max_timeout_seconds_used"], 3)
        self.assertEqual(validation["secret_scan"]["patterns"], sorted({name for _, name in inventory._SECRET_PATTERNS}))
        self.assertTrue(validation["secret_scan"]["clean"])
        self.assertEqual(validation["delivery"]["status"], "NOT_YET_DELIVERED")
        # failures are retained rather than silently dropped (inventory/README.md)
        self.assertEqual(validation["failed_commands"]["count"], 1)
        self.assertEqual(validation["failed_commands"]["items"][0]["label"], "synthetic failing probe")
        self.assertEqual(validation["failed_commands"]["items"][0]["exit_code"], 3)

    def test_secret_findings_make_the_manifest_set_unclean(self):
        findings = [{"file": "dirty.json", "pattern": "GITHUB_TOKEN", "line": 1, "snippet_stored": False}]
        with tempfile.TemporaryDirectory(prefix="arena-manifests-") as tmp:
            session = self.write_session(pathlib.Path(tmp) / "session-test")
            validation = inventory.build_validation(session, list(inventory.REQUIRED_FILES), inventory.Runner(), findings, None, None)
        self.assertIs(validation["secret_scan"]["clean"], False)
        self.assertEqual(validation["secret_scan"]["findings"], findings)

    def test_required_manifests_are_documented(self):
        readme = (REPO_ROOT / "inventory" / "README.md").read_text(encoding="utf-8")
        for name in inventory.REQUIRED_FILES:
            with self.subTest(manifest=name):
                self.assertIn(f"`{name}`", readme)


class TestPersistenceMarkerSemantics(unittest.TestCase):
    """Marker comparison must never claim persistence from a single run."""

    FINGERPRINTS = {"SYSTEM": "a" * 64, "PYTHON": "b" * 64, "NODE": "c" * 64, "EXECUTABLES": "d" * 64, "COMBINED": "e" * 64}

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="arena-persistence-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # Not named "home": redact() strips a literal "/home/" path segment.
        self.home = self.tmp / "homedir"
        self.home.mkdir()
        self.repo = self.tmp / "repo"
        (self.repo / "inventory").mkdir(parents=True)
        self.marker_tmp_name = f"arena-inventory-marker-TEST-{uuid.uuid4().hex}.json"
        self.marker_tmp_path = pathlib.Path(tempfile.gettempdir()) / self.marker_tmp_name
        self.addCleanup(self.marker_tmp_path.unlink, True)
        self.assertNotEqual(self.marker_tmp_name, inventory.MARKER_TMP)  # never touch the production marker

    def payload(self, session_id: str, fingerprints: dict | None = None):
        """Shape produced by main(): build_fingerprints() output plus session_id."""
        base = inventory.build_fingerprints({}, {}, {}, {}, {})
        base["fingerprints"] = fingerprints if fingerprints is not None else dict(self.FINGERPRINTS)
        base["session_id"] = session_id
        return base

    def collect(self, session_dir_name: str, fingerprints: dict):
        with mock.patch.object(pathlib.Path, "home", return_value=self.home), \
                mock.patch.object(inventory, "MARKER_TMP", self.marker_tmp_name), \
                working_directory(self.repo):
            return inventory.collect_persistence(self.tmp / session_dir_name, fingerprints)

    def test_first_run_defers_the_conclusion_and_writes_all_three_markers(self):
        result = self.collect("session-one", self.payload("session-one"))
        self.assertEqual(result["schema"], SCHEMA)
        self.assertTrue(result["cross_session_persistence_conclusion"].startswith("DEFERRED"))
        self.assertIn("cannot demonstrate persistence", result["cross_session_persistence_conclusion"])
        self.assertEqual(sorted(result["previous_markers"]), ["home", "repo", "tmp"])
        for label, entry in result["previous_markers"].items():
            with self.subTest(marker=label):
                self.assertIs(entry["exists"], False)
                self.assertIsNone(entry["previous_session_id"])
                self.assertIsNone(entry["environment_changed_since_previous"])
                self.assertIn("no readable marker", entry["note"])
        for label, entry in result["new_markers_written"].items():
            with self.subTest(marker=label):
                self.assertIs(entry["written"], True)
                self.assertGreater(entry["bytes"], 0)
        self.assertTrue((self.home / inventory.MARKER_HOME).is_file())
        self.assertTrue(self.marker_tmp_path.is_file())
        self.assertTrue((self.repo / inventory.MARKER_REPO).is_file())
        marker = read_json(self.tmp / "session-one" / "persistence-marker.json")
        self.assertEqual(marker["session_id"], "session-one")

    def test_marker_written_where_the_repo_directory_is_absent_is_recorded_as_failed(self):
        empty_repo = self.tmp / "repo-without-inventory"
        empty_repo.mkdir()
        with mock.patch.object(pathlib.Path, "home", return_value=self.home), \
                mock.patch.object(inventory, "MARKER_TMP", self.marker_tmp_name), \
                working_directory(empty_repo):
            result = inventory.collect_persistence(self.tmp / "session-x", self.payload("session-x"))
        self.assertIs(result["new_markers_written"]["repo"]["written"], False)
        self.assertEqual(result["new_markers_written"]["repo"]["error"], "FileNotFoundError")
        self.assertIs(result["new_markers_written"]["home"]["written"], True)

    def test_marker_payload_is_credential_free_and_hashes_the_hostname(self):
        self.collect("session-one", self.payload("session-one"))
        text = (self.tmp / "session-one" / "persistence-marker.json").read_text(encoding="utf-8")
        marker = json.loads(text)
        self.assertEqual(marker["marker"], "arena-inventory")
        self.assertIn("credential-free", marker["purpose"])
        self.assertIn("Do NOT conclude persistence from a single run", marker["note"])
        self.assertEqual(marker["engine"], inventory.ENGINE)
        self.assertEqual(marker["fingerprints"], self.FINGERPRINTS)
        self.assertEqual(marker["host_hash"], inventory.short_hash(inventory._HOSTNAME))
        self.assertRegex(marker["host_hash"], r"^[0-9a-f]{12}$")
        if inventory._HOSTNAME:
            self.assertNotIn(inventory._HOSTNAME, text)
        self.assertEqual(inventory.find_secrets_in_text(text), [])

    def test_marker_from_an_earlier_session_becomes_usable_evidence(self):
        self.collect("session-one", self.payload("session-one"))
        changed = {**self.FINGERPRINTS, "SYSTEM": "0" * 64}
        result = self.collect("session-two", self.payload("session-two", changed))
        for label, entry in result["previous_markers"].items():
            with self.subTest(marker=label):
                self.assertIs(entry["exists"], True)
                self.assertEqual(entry["previous_session_id"], "session-one")
                self.assertIs(entry["same_session_self_reference"], False)
                self.assertIs(entry["usable_for_cross_session_comparison"], True)
                self.assertEqual(entry["previous_fingerprints"], self.FINGERPRINTS)
                self.assertIs(entry["fingerprint_match"]["SYSTEM"], False)
                self.assertIs(entry["environment_changed_since_previous"], True)
                self.assertIsNotNone(entry["age_hours"])
                self.assertRegex(entry["previous_collected_utc"], r"^\d{4}-\d{2}-\d{2}T")

    def test_same_session_marker_is_not_cross_session_evidence(self):
        # The point of the untracked repository marker: a file this very session
        # (or a Git checkout) produced cannot prove sandbox persistence.
        self.collect("session-one", self.payload("session-same"))
        result = self.collect("session-two", self.payload("session-same"))
        for label, entry in result["previous_markers"].items():
            with self.subTest(marker=label):
                self.assertIs(entry["same_session_self_reference"], True)
                self.assertIs(entry["usable_for_cross_session_comparison"], False)
                self.assertIsNone(entry["environment_changed_since_previous"])
        self.assertTrue(result["cross_session_persistence_conclusion"].startswith("DEFERRED"))

    def test_unreadable_marker_is_reported_and_replaced(self):
        (self.home / inventory.MARKER_HOME).write_text("{ not json at all", encoding="utf-8")
        result = self.collect("session-one", self.payload("session-one"))
        entry = result["previous_markers"]["home"]
        self.assertIs(entry["exists"], True)
        self.assertEqual(entry["read_error"], "JSONDecodeError")
        self.assertIsNone(entry["previous_session_id"])
        self.assertIsNone(entry.get("usable_for_cross_session_comparison"))
        self.assertIn("no readable marker", entry["note"])
        self.assertEqual(read_json(self.home / inventory.MARKER_HOME)["session_id"], "session-one")

    def test_unchanged_fingerprints_do_not_report_environment_drift(self):
        unchanged = dict(self.FINGERPRINTS)
        self.collect("session-one", self.payload("session-one", unchanged))
        entry = self.collect("session-two", self.payload("session-two", unchanged))["previous_markers"]["home"]
        self.assertIs(entry["usable_for_cross_session_comparison"], True)
        self.assertEqual(entry["fingerprint_match"], {key: True for key in unchanged})
        self.assertIs(entry["environment_changed_since_previous"], False)
        self.assertNotIn("session_id", entry["fingerprint_match"])

    def test_missing_or_changed_fingerprint_reports_environment_drift(self):
        missing = dict(self.FINGERPRINTS)
        missing.pop("NODE")
        self.collect("session-one", self.payload("session-one", missing))
        changed = {**self.FINGERPRINTS, "SYSTEM": "0" * 64}
        entry = self.collect("session-two", self.payload("session-two", changed))["previous_markers"]["home"]
        self.assertEqual(entry["fingerprint_match"]["SYSTEM"], False)
        self.assertEqual(entry["fingerprint_match"]["NODE"], False)
        self.assertTrue(all(entry["fingerprint_match"][key] for key in ("PYTHON", "EXECUTABLES", "COMBINED")))
        self.assertIs(entry["environment_changed_since_previous"], True)

    @unittest.skipUnless((REPO_ROOT / ".git").is_dir(), "requires a git checkout")
    def test_repository_marker_is_deliberately_untracked(self):
        # inventory/README.md: a marker inherited from a Git checkout would not
        # prove sandbox persistence, so it stays ignored while the 2026-09-26
        # snapshot stays committed.
        self.assertIn(inventory.MARKER_REPO, (REPO_ROOT / ".gitignore").read_text(encoding="utf-8"))
        tracked = subprocess.run(["git", "ls-files", "--", "inventory"], cwd=REPO_ROOT,
                                 capture_output=True, text=True, timeout=60)
        self.assertEqual(tracked.returncode, 0, tracked.stderr)
        paths = tracked.stdout.split()
        marker_name = inventory.MARKER_REPO.rsplit("/", 1)[-1]
        self.assertEqual([p for p in paths if p.endswith(marker_name)], [])
        self.assertTrue(paths, "the historical snapshot is expected to be tracked")
        self.assertTrue(any(p.startswith("inventory/2026-09-26/") for p in paths))


class TestEngineOrchestration(unittest.TestCase):
    """``main()`` with every system-touching collector replaced by a fixture.

    No network, no installs, no real probing, no writes outside ``self.tmp``.
    """

    STUBS = {
        "collect_system": {"schema": SCHEMA, "os": {"id": "linux", "pretty_name": "Synthetic Test OS"},
                           "kernel": {"release": "0.0.0-test", "machine": "x86_64"}, "cpu": {"logical": 2},
                           "memory_kb": {"MemTotal": 2048000}, "rlimits": {}, "disk": {},
                           "user_privilege": {"category": "unprivileged"}, "apt_state": {"index_populated": False}},
        "collect_executables": {"schema": SCHEMA, "executables": ["python3"], "executable_count": 1,
                                "version_probes": {"python3": {"present_on_path": True, "version_parsed": "3.11.2"}}},
        "collect_python": {"schema": SCHEMA, "active_interpreter": {"version": "3.11.2", "implementation": "CPython"},
                           "standard_library": {"count": 1}, "installed_distributions": {"count": 0, "items": []},
                           "distributions_found_on_path": {"python3": "/usr/bin/python3"}},
        "collect_node": {"schema": SCHEMA, "node_present": False, "runtime": {"version": None},
                         "package_managers": {"npm": {"version": None}}, "global_packages": [],
                         "global_package_count": 0, "builtin_module_count": 0},
        "collect_os_packages": {"schema": SCHEMA, "packages": [], "installed_count": 0},
        "collect_libraries": {"schema": SCHEMA, "shared_objects": [], "count": 0},
        "collect_fonts": {"schema": SCHEMA, "files": [], "font_file_count": 0, "family_count_estimate": 0},
        "collect_browsers": {"schema": SCHEMA, "executables": {}, "caches_and_config": {}},
        "detect_repo": "synthetic/test-repo",
        "collect_practical_tests": {"schema": SCHEMA, "tests": [], "counts": {}},
        # Would otherwise write markers to the real $HOME, /tmp and cwd.
        "collect_persistence": {"schema": SCHEMA, "previous_markers": {}, "new_markers_written": {},
                                "cross_session_persistence_conclusion": "DEFERRED"},
    }

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="arena-engine-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo_inventory_before = self.repo_inventory_state()
        self.out = self.tmp / "inventory" / "2099-01-01" / "session-test"
        self.install_probe = mock.MagicMock(return_value={
            "schema": SCHEMA, "authorization": "synthetic stub — no package was installed",
            "results": {"pypi_pip_six": {"status": "INSTALLATION_TESTED"}},
        })
        self.stubs = {name: mock.MagicMock(return_value=value) for name, value in self.STUBS.items()}

    def tearDown(self):
        # The committed 2026-09-26 snapshot is historical evidence: a stubbed
        # engine run must leave the tracked inventory tree byte-identical.
        self.assertEqual(self.repo_inventory_state(), self.repo_inventory_before,
                         "the stubbed run changed the tracked inventory tree")

    @staticmethod
    def repo_inventory_state():
        root = REPO_ROOT / "inventory"
        return sorted((str(path.relative_to(root)), path.stat().st_mtime_ns if path.is_file() else 0)
                      for path in root.rglob("*"))

    def observations_path(self, payload) -> pathlib.Path:
        path = self.tmp / "observations.json"
        path.write_text(payload if isinstance(payload, str) else json.dumps(payload, indent=1), encoding="utf-8")
        return path

    VALID_OBSERVATIONS = {
        "agent_tools": [
            {"name": "synthetic_tool", "purpose": "fixture", "executed_this_session": True, "execution_result": "ok"},
            {"name": "synthetic_tool_2", "purpose": "fixture"},
        ],
        "native_fetch_tests": [{"host": "example.invalid", "result": "ok: fixture"}],
        "practical_tests": [{"id": "synthetic_practical_test", "status": "EXECUTED_NOW"}],
        "ui_items": [{"item": "Synthetic UI row", "status": "NOT_TESTED", "how": "fixture"}],
        "notes": "synthetic fixture — no real tool surface is described here",
    }

    def run_engine(self, extra_args=(), observations=None):
        argv = ["--out", str(self.out), "--skip-network", "--skip-registry", "--skip-github", "--quiet"]
        argv += list(extra_args)
        if observations is not None:
            argv += ["--observations", str(observations)]
        with mock.patch.multiple(inventory, **self.stubs), \
                mock.patch.object(inventory, "collect_install_probes", self.install_probe), \
                working_directory(self.tmp):
            return inventory.main(argv)

    def session_file(self, name: str) -> pathlib.Path:
        return self.out / name

    # -- install probes stay opt-in --------------------------------------

    def test_install_probes_are_skipped_by_default(self):
        observations = self.observations_path(self.VALID_OBSERVATIONS)
        self.assertEqual(self.run_engine(observations=observations), 0)  # no install flag at all
        self.assertEqual(self.install_probe.call_count, 0)
        for name in ("network.json", "registries.json"):
            probes = read_json(self.session_file(name))["install_probes"]
            with self.subTest(manifest=name):
                self.assertIs(probes["skipped"], True)
                self.assertEqual(probes["results"], {})
                self.assertEqual(probes["note"], "install probes require explicit --probe-install")
        self.assertEqual(read_json(self.session_file("capabilities.json"))["package_installation"]["pypi"]["installation"], "NOT_TESTED")
        self.assertTrue(read_json(self.session_file("provenance.json"))["skips"]["install"])

    def test_skip_install_alone_and_as_an_override_of_probe_install(self):
        observations = self.observations_path(self.VALID_OBSERVATIONS)
        self.run_engine(["--skip-install"], observations=observations)
        self.assertEqual(self.install_probe.call_count, 0)
        self.run_engine(["--probe-install", "--skip-install"], observations=observations)
        self.assertEqual(self.install_probe.call_count, 0, "--skip-install must win over --probe-install")
        self.assertIs(read_json(self.session_file("registries.json"))["install_probes"]["skipped"], True)
        self.assertTrue(read_json(self.session_file("provenance.json"))["skips"]["install"])

    def test_probe_install_opts_in_to_the_isolated_probe(self):
        self.assertEqual(self.run_engine(["--probe-install"], observations=self.observations_path(self.VALID_OBSERVATIONS)), 0)
        self.assertEqual(self.install_probe.call_count, 1)
        args = self.install_probe.call_args
        self.assertEqual(args.args[1], tempfile.gettempdir())  # isolated directory, never the repo or system site-packages
        self.assertEqual(args.kwargs, {"do_pip": True, "do_npm": True})
        self.assertFalse(read_json(self.session_file("provenance.json"))["skips"]["install"])
        self.assertEqual(
            read_json(self.session_file("registries.json"))["install_probes"]["results"]["pypi_pip_six"]["status"],
            "INSTALLATION_TESTED",
        )

    def test_cli_documents_install_probes_as_opt_in(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(SystemExit) as raised:
                inventory.main(["--help"])  # argparse exits before any collection
        self.assertEqual(raised.exception.code, 0)
        help_text = " ".join(buffer.getvalue().split())  # argparse wraps lines
        self.assertIn("opt in to isolated pip/npm install probes", help_text)
        self.assertIn("requires operator approval", help_text)
        self.assertIn("skip install probes even if --probe-install", help_text)
        self.assertEqual(self.install_probe.call_count, 0)

    # -- observations handling -------------------------------------------

    def test_valid_observations_produce_a_complete_valid_manifest_set(self):
        self.assertEqual(self.run_engine(observations=self.observations_path(self.VALID_OBSERVATIONS)), 0)
        validation = read_json(self.session_file("validation.json"))
        self.assertTrue(validation["all_expected_files_present_and_valid"])
        self.assertEqual(validation["missing_or_invalid"], [])
        self.assertTrue(validation["secret_scan"]["clean"])
        for name in inventory.REQUIRED_FILES:
            with self.subTest(manifest=name):
                self.assertEqual(read_json(self.session_file(name))["schema"], SCHEMA)
        provenance = read_json(self.session_file("provenance.json"))
        self.assertEqual(provenance["engine"], inventory.ENGINE)
        self.assertEqual(provenance["collector_errors"], {})
        self.assertEqual(provenance["skips"], {"network": True, "registry": True, "install": True, "github": True})
        self.assertRegex(provenance["engine_sha256_12"], r"^[0-9a-f]{12}$")
        tools = read_json(self.session_file("native-tools.json"))["tools"]
        self.assertEqual([(t["name"], t["status"]) for t in tools],
                         [("synthetic_tool", "EXECUTED_NOW"), ("synthetic_tool_2", "EXPOSED")])
        capabilities = read_json(self.session_file("capabilities.json"))
        self.assertEqual(capabilities["agent_tools"]["declared_count"], 2)
        self.assertEqual(capabilities["agent_tools"]["executed_count"], 1)
        self.assertIn("| Synthetic UI row | `NOT_TESTED` | fixture |", self.session_file("UI-CHECKLIST.md").read_text(encoding="utf-8"))
        # the mirrored human-facing documents stay inside the temporary tree
        for doc in ("SUMMARY.md", "UI-CHECKLIST.md"):
            mirrored = self.tmp / "inventory" / doc
            with self.subTest(document=doc):
                self.assertTrue(mirrored.is_file())
                self.assertEqual(mirrored.read_bytes(), self.session_file(doc).read_bytes())

    def test_omitted_observations_fall_back_to_the_declared_default(self):
        self.assertEqual(self.run_engine(), 0)
        self.assertEqual(read_json(self.session_file("provenance.json"))["collector_errors"], {})
        self.assertIsNone(read_json(self.session_file("provenance.json"))["observations_file"])
        tools = read_json(self.session_file("native-tools.json"))
        self.assertEqual(tools["tool_count"], 0)
        self.assertEqual(tools["tools"], [])
        self.assertIn("cannot be introspected", tools["observations_notes"])

    def test_missing_observations_file_is_reported_not_silently_ignored(self):
        missing = self.tmp / "no-such-observations.json"
        self.assertEqual(self.run_engine(observations=missing), 1)
        provenance = read_json(self.session_file("provenance.json"))
        self.assertEqual(provenance["collector_errors"], {"observations": "explicit observations file not found"})
        tools = read_json(self.session_file("native-tools.json"))
        self.assertEqual(tools["tool_count"], 0)
        self.assertIn("cannot be introspected", tools["observations_notes"])
        self.assertTrue(read_json(self.session_file("validation.json"))["all_expected_files_present_and_valid"])

    def test_malformed_observations_file_is_reported_and_the_run_degrades_safely(self):
        malformed = self.observations_path('{"agent_tools": [this is not json]}')
        self.assertEqual(self.run_engine(observations=malformed), 1)
        error = read_json(self.session_file("provenance.json"))["collector_errors"]["observations"]
        self.assertTrue(error.startswith("JSONDecodeError"), error)
        tools = read_json(self.session_file("native-tools.json"))
        self.assertEqual(tools["tool_count"], 0)  # never treated as a complete tool inventory
        self.assertEqual(tools["tools"], [])
        self.assertIn("cannot be introspected", tools["observations_notes"])
        self.assertEqual(read_json(self.session_file("capabilities.json"))["agent_tools"]["declared_count"], 0)
        self.assertTrue(read_json(self.session_file("validation.json"))["all_expected_files_present_and_valid"])
        self.assertTrue(read_json(self.session_file("validation.json"))["secret_scan"]["clean"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
