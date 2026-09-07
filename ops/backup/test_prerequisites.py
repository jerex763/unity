"""Offline regression checks: fake configuration and isolated command stubs only."""

from pathlib import Path
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CONFIG = {
    "DATABASE_URL": "fictional-database-value",
    "BACKUP_AGE_RECIPIENT": "fictional-recipient-value",
    "BACKUP_DESTINATION": "s3://fictional-backup-bucket",
    "AWS_ACCESS_KEY_ID": "fictional-access-key-value",
    "AWS_SECRET_ACCESS_KEY": "fictional-secret-key-value",
    "AWS_DEFAULT_REGION": "fictional-region-value",
    "BACKUP_ALERT_WEBHOOK_URL": "https://fictional.invalid/webhook",
}


class PrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bin = Path(self.temp.name)
        self.log = self.bin / "calls"
        self.env = {"PATH": str(self.bin), "CALL_LOG": str(self.log), **CONFIG}
        for tool in ("age", "pg_dump", "curl"):
            self.stub(tool)
        self.stub("aws", "printf 'aws-cli/2.0.0 fictional\n'\n")
        self.stub("sudo")

    def stub(self, name, body=""):
        script = self.bin / name
        script.write_text(
            '#!/bin/sh\nprintf "%s\\n" "' + name + ' $*" >> "$CALL_LOG"\n' + body
        )
        script.chmod(0o755)

    def run_script(self, name, env=None):
        return subprocess.run(
            ["/bin/bash", str(HERE / name)],
            env=self.env if env is None else env,
            capture_output=True,
            text=True,
            check=False,
        )

    def calls(self):
        return self.log.read_text() if self.log.exists() else ""

    def assert_no_values(self, output):
        for value in CONFIG.values():
            self.assertNotIn(value, output)

    def test_missing_each_configuration_stops_before_external_commands(self):
        for name in CONFIG:
            with self.subTest(name=name):
                env = dict(self.env)
                del env[name]
                result = self.run_script("check_production_config.sh", env)
                self.assertEqual(result.returncode, 2)
                self.assertIn(name, result.stderr)
                self.assert_no_values(result.stdout + result.stderr)
        self.assertEqual(self.calls(), "")

    def test_missing_all_reports_all_names_and_rejects_whitespace(self):
        for value in ("", " \t\n"):
            result = self.run_script(
                "check_production_config.sh",
                {**self.env, **dict.fromkeys(CONFIG, value)},
            )
            self.assertEqual(result.returncode, 2)
            for name in CONFIG:
                self.assertIn(name, result.stderr)
        self.assertEqual(self.calls(), "")

    def test_complete_configuration_is_offline_and_names_only(self):
        result = self.run_script("check_production_config.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_no_values(result.stdout + result.stderr)
        self.assertEqual(self.calls(), "")

    def test_production_destination_rejected_without_exposing_value(self):
        for destination in ("file:///fictional", "s3://", "https://fictional.invalid"):
            result = self.run_script(
                "check_production_config.sh",
                {**self.env, "BACKUP_DESTINATION": destination},
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("BACKUP_DESTINATION", result.stderr)
            self.assertNotIn(destination, result.stderr)
        self.assertEqual(self.calls(), "")

    def test_aws_missing_or_broken_stops_before_installation(self):
        (self.bin / "aws").unlink()
        result = self.run_script("install_tools.sh")
        self.assertEqual(result.returncode, 2)
        self.assertIn("AWS CLI v2", result.stderr)
        for body in ("exit 1\n", "printf 'aws-cli/1.0.0\\n'\n"):
            self.stub("aws", body)
            result = self.run_script("install_tools.sh")
            self.assertEqual(result.returncode, 2)
            self.assertIn("AWS CLI v2", result.stderr)
        self.assertNotIn("sudo", self.calls())
        self.assertNotIn("pg_dump", self.calls())

    def test_package_update_and_install_failure_stop_verification(self):
        for failing in ("update", "install"):
            with self.subTest(failing=failing):
                self.stub("sudo", f'[ "$2" != "{failing}" ] || exit 42\n')
                result = self.run_script("install_tools.sh")
                self.assertEqual(result.returncode, 42)
                self.assertNotIn("pg_dump", self.calls())

    def test_missing_or_broken_required_tool_stops(self):
        for tool in ("age", "pg_dump", "curl"):
            with self.subTest(tool=tool):
                (self.bin / tool).unlink()
                result = self.run_script("install_tools.sh")
                self.assertEqual(result.returncode, 2)
                self.assertIn(tool, result.stderr)
                self.stub(tool, "exit 1\n")
                result = self.run_script("install_tools.sh")
                self.assertEqual(result.returncode, 2)
                self.assertIn(tool, result.stderr)
                self.stub(tool)

    def test_install_success_verifies_without_database_or_network_access(self):
        result = self.run_script("install_tools.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.calls().splitlines(),
            [
                "aws --version",
                "sudo apt-get update",
                "sudo apt-get install --yes age postgresql-client",
                "age --version",
                "pg_dump --version",
                "curl --version",
            ],
        )

    def test_workflow_gates_and_alert_scope(self):
        workflow = (ROOT / ".github/workflows/backup.yml").read_text()
        self.assertIn("runs-on: ubuntu-24.04", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("cron:", workflow)
        steps = workflow.split("    steps:\n", 1)[1]
        config, install, backup, alert = [
            steps.index(text)
            for text in (
                "run: ops/backup/check_production_config.sh",
                "run: ops/backup/install_tools.sh",
                "run: ops/backup/backup.sh",
                "- name: Alert on failure",
            )
        ]
        self.assertLess(config, install)
        self.assertLess(install, backup)
        self.assertLess(backup, alert)
        self.assertNotIn("if:", steps[:alert])  # prerequisite failures skip later steps
        self.assertIn("if: failure()", steps[alert:])
        self.assertNotIn("BACKUP_ALERT_WEBHOOK_URL", workflow.split("    steps:\n")[0])
        self.assertNotIn("BACKUP_ALERT_WEBHOOK_URL", steps[config:alert])
        self.assertEqual(workflow.count("secrets.BACKUP_ALERT_WEBHOOK_URL"), 2)
        self.assertIn("file://*)", (HERE / "backup.sh").read_text())
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("python3 -m unittest discover -s ops/backup", ci)


if __name__ == "__main__":
    unittest.main()
