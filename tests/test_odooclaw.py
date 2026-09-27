"""Tests for the optional OdooClaw integration (use_odooclaw)."""

import json
from pathlib import Path

import pytest
import yaml
from copier import run_copy
from plumbum import local
from plumbum.cmd import docker

# Versions where the use_odooclaw question is available (copier.yml `when`).
ODOOCLAW_ODOO_VERSIONS = (16.0, 17.0, 18.0)


def _render(cloned_template, tmp_path, **data):
    project = tmp_path / "project"
    run_copy(
        src_path=str(cloned_template),
        dst_path=str(project),
        data=data,
        vcs_ref="HEAD",
        defaults=True,
        overwrite=True,
        unsafe=True,
    )
    return project


class TestOdooclawDisabled:
    @pytest.fixture(scope="class")
    def project(self, request, tmp_path_factory):
        return _render(
            request.getfixturevalue("cloned_template"),
            tmp_path_factory.mktemp("off"),
            odoo_version=18.0,
            use_odooclaw=False,
        )

    def test_no_generated_files(self, project: Path):
        for rel in (
            ".docker/odooclaw.env",
            "odooclaw/config/config.json",
            "scripts/setup-odooclaw.sh",
            "scripts/smoke-test-odooclaw.sh",
        ):
            assert not (project / rel).exists(), f"{rel} must not be generated"
        assert not (project / "odooclaw").exists()

    def test_no_services_in_compose(self, project: Path):
        for compose in ("devel.yaml", "prod.yaml"):
            data = yaml.safe_load((project / compose).read_text())
            assert "odooclaw" not in data["services"]
            assert "redis" not in data["services"]
            assert "odooclaw_data" not in data.get("volumes", {})

    def test_no_repo_entries(self, project: Path):
        repos = (project / "odoo/custom/src/repos.yaml").read_text()
        addons = (project / "odoo/custom/src/addons.yaml").read_text()
        assert "odoo-addons" not in repos
        assert "odooclaw" not in addons


class TestOdooclawEnabled:
    @pytest.fixture(scope="class")
    def project(self, request, tmp_path_factory):
        return _render(
            request.getfixturevalue("cloned_template"),
            tmp_path_factory.mktemp("on"),
            odoo_version=18.0,
            use_odooclaw=True,
            odooclaw_provider="openai",
            odooclaw_model="gpt-4o-mini",
        )

    def test_generated_files(self, project: Path):
        for rel in (
            ".docker/odooclaw.env",
            "odooclaw/config/config.json",
            "scripts/setup-odooclaw.sh",
            "scripts/smoke-test-odooclaw.sh",
        ):
            assert (project / rel).is_file(), f"{rel} must be generated"

    def test_config_is_valid_json_without_placeholders(self, project: Path):
        raw = (project / "odooclaw/config/config.json").read_text()
        config = json.loads(raw)
        assert "${" not in raw
        assert config["agents"]["defaults"]["provider"] == "openai"
        assert config["agents"]["defaults"]["model"] == "gpt-4o-mini"
        assert config["channels"]["odoo"]["webhook_port"] == 18790
        assert config["tools"]["mcp"]["servers"]["odoo-mcp"]["enabled"] is True

    def test_env_file(self, project: Path):
        env = (project / ".docker/odooclaw.env").read_text()
        assert "ODOOCLAW_CHANNELS_ODOO_WEBHOOK_PORT=18790" in env
        assert "ODOOCLAW_JOB_STORE=odoo" in env
        # DB is NOT pinned in the shared env file (it is per-compose-file).
        assert "ODOO_DB=" not in env

    def test_services_in_compose(self, project: Path):
        for compose, expected_db in (("devel.yaml", "devel"), ("prod.yaml", "prod")):
            data = yaml.safe_load((project / compose).read_text())
            svc = data["services"]["odooclaw"]
            assert svc["build"]["context"] == "./odooclaw"
            assert svc["build"]["dockerfile"] == "docker/Dockerfile"
            assert svc["environment"]["ODOO_DB"] == expected_db
            assert svc["environment"]["ODOOCLAW_CHANNELS_ODOO_TARGET_DB"] == expected_db
            assert "redis" in data["services"]
            assert "odooclaw_data" in data["volumes"]

    def test_repo_and_addons_entries(self, project: Path):
        repos = (project / "odoo/custom/src/repos.yaml").read_text()
        assert "nicolasramos/odoo-addons.git" in repos
        assert "target: odooclaw $ODOO_VERSION" in repos
        addons = yaml.safe_load((project / "odoo/custom/src/addons.yaml").read_text())
        assert "mail_bot_odooclaw" in addons["odoo-addons"]
        assert "mail_bot_odooclaw_account" in addons["odoo-addons"]

    def test_no_unrendered_jinja(self, project: Path):
        for path in project.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            # .j2 files are runtime templates (OCA readme generator), not
            # copier leftovers.
            if path.suffix == ".j2":
                continue
            try:
                content = path.read_text()
            except (UnicodeDecodeError, PermissionError):
                continue
            assert "{%" not in content, f"unrendered jinja in {path}"
            assert "{{ " not in content, f"unrendered jinja in {path}"

    def test_compose_config_valid(self, project: Path):
        with local.cwd(project):
            for compose in ("devel.yaml", "prod.yaml"):
                docker(
                    "compose",
                    "-f",
                    "common.yaml",
                    "-f",
                    compose,
                    "config",
                    "-q",
                )


class TestOdooclawVersions:
    """The module list and question availability per Odoo version."""

    @pytest.mark.parametrize("odoo_version", ODOOCLAW_ODOO_VERSIONS)
    def test_module_list_per_version(self, cloned_template, tmp_path, odoo_version):
        project = _render(
            cloned_template,
            tmp_path / f"v{odoo_version}",
            odoo_version=odoo_version,
            use_odooclaw=True,
            odooclaw_provider="openai",
            odooclaw_model="gpt-4o-mini",
        )
        addons = yaml.safe_load((project / "odoo/custom/src/addons.yaml").read_text())
        modules = addons["odoo-addons"]
        assert "mail_bot_odooclaw" in modules
        if odoo_version >= 18.0:
            assert "mail_bot_odooclaw_account" in modules
            assert "mail_bot_odooclaw_crm" in modules
        else:
            assert modules == ["mail_bot_odooclaw"]
        # Compose still valid on every supported version
        with local.cwd(project):
            docker("compose", "-f", "common.yaml", "-f", "devel.yaml", "config", "-q")
