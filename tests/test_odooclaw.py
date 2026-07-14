import json
from pathlib import Path

import yaml
from copier.main import run_copy
from plumbum import local

from .conftest import DBVER_PER_ODOO


def test_odooclaw_enabled_by_version(
    tmp_path: Path, cloned_template: Path, supported_odoo_version: float
):
    """Test that OdooClaw files and configurations are created ONLY on supported versions (16.0-18.0) when requested."""
    is_supported = 16.0 <= supported_odoo_version <= 18.0

    with local.cwd(cloned_template):
        run_copy(
            ".",
            str(tmp_path),
            data={
                "odoo_version": supported_odoo_version,
                "postgres_version": DBVER_PER_ODOO[supported_odoo_version]["latest"],
                "use_odooclaw": True,
            },
            vcs_ref="test",
            defaults=True,
            overwrite=True,
            unsafe=True,
        )

    # Verify devel.yaml
    devel_yaml_path = tmp_path / "devel.yaml"
    assert devel_yaml_path.exists()
    with open(devel_yaml_path) as f:
        devel_data = yaml.safe_load(f)

    # Verify prod.yaml
    prod_yaml_path = tmp_path / "prod.yaml"
    assert prod_yaml_path.exists()
    with open(prod_yaml_path) as f:
        prod_data = yaml.safe_load(f)

    # Check paths
    config_json_path = tmp_path / "odooclaw" / "config" / "config.json"
    env_path = tmp_path / ".docker" / "odoo.env"
    repos_path = tmp_path / "odoo" / "custom" / "src" / "repos.yaml"

    if is_supported:
        assert "odooclaw" in devel_data["services"]
        assert "redis" in devel_data["services"]
        assert "odooclaw_data" in devel_data["volumes"]

        assert "odooclaw" in prod_data["services"]
        assert "redis" in prod_data["services"]
        assert "odooclaw_data" in prod_data["volumes"]

        assert config_json_path.exists()
        with open(config_json_path) as f:
            config_data = json.load(f)
        assert (
            config_data["agents"]["defaults"]["model_name"]
            == "${ODOOCLAW_AGENTS_DEFAULTS_MODEL_NAME:-gpt-4o-mini}"
        )

        assert env_path.exists()
        assert "ODOOCLAW_CHANNELS_ODOO_ENABLED=true" in env_path.read_text()

        assert repos_path.exists()
        with open(repos_path) as f:
            repos_data = yaml.safe_load(f)
        assert "./odoo-addons" in repos_data
    else:
        assert "odooclaw" not in devel_data.get("services", {})
        assert "redis" not in devel_data.get("services", {})
        assert "odooclaw_data" not in devel_data.get("volumes", {})

        assert "odooclaw" not in prod_data.get("services", {})
        assert "redis" not in prod_data.get("services", {})
        assert "odooclaw_data" not in prod_data.get("volumes", {})

        assert not config_json_path.exists()

        if env_path.exists():
            assert "ODOOCLAW_CHANNELS_ODOO_ENABLED" not in env_path.read_text()

        if repos_path.exists():
            with open(repos_path) as f:
                repos_data = yaml.safe_load(f)
            assert "./odoo-addons" not in repos_data


def test_odooclaw_disabled_by_default(
    tmp_path: Path, cloned_template: Path, supported_odoo_version: float
):
    """Test that OdooClaw is not configured when disabled (default value)."""
    with local.cwd(cloned_template):
        run_copy(
            ".",
            str(tmp_path),
            data={
                "odoo_version": supported_odoo_version,
                "postgres_version": DBVER_PER_ODOO[supported_odoo_version]["latest"],
                "use_odooclaw": False,
            },
            vcs_ref="test",
            defaults=True,
            overwrite=True,
            unsafe=True,
        )

    # Verify devel.yaml
    devel_yaml_path = tmp_path / "devel.yaml"
    assert devel_yaml_path.exists()
    with open(devel_yaml_path) as f:
        devel_data = yaml.safe_load(f)

    # Verify prod.yaml
    prod_yaml_path = tmp_path / "prod.yaml"
    assert prod_yaml_path.exists()
    with open(prod_yaml_path) as f:
        prod_data = yaml.safe_load(f)

    # Check paths
    config_json_path = tmp_path / "odooclaw" / "config" / "config.json"
    env_path = tmp_path / ".docker" / "odoo.env"
    repos_path = tmp_path / "odoo" / "custom" / "src" / "repos.yaml"

    assert "odooclaw" not in devel_data.get("services", {})
    assert "redis" not in devel_data.get("services", {})
    assert "odooclaw_data" not in devel_data.get("volumes", {})

    assert "odooclaw" not in prod_data.get("services", {})
    assert "redis" not in prod_data.get("services", {})
    assert "odooclaw_data" not in prod_data.get("volumes", {})

    assert not config_json_path.exists()

    if env_path.exists():
        assert "ODOOCLAW_CHANNELS_ODOO_ENABLED" not in env_path.read_text()

    if repos_path.exists():
        with open(repos_path) as f:
            repos_data = yaml.safe_load(f)
        assert "./odoo-addons" not in repos_data


def test_odooclaw_unsupported_version_ignores_request(
    tmp_path: Path, cloned_template: Path
):
    """use_odooclaw=true on Odoo 15.0 or 19.0 must NOT generate OdooClaw files.

    The `when` clause on the copier question should hide the option, and the
    Jinja `{% if odoo_version >= 16.0 and odoo_version <= 18.0 %}` guards
    should keep the template output clean even if a user forces the flag
    via answers file overrides.
    """
    for unsupported_version in (15.0, 19.0):
        with local.cwd(cloned_template):
            run_copy(
                ".",
                str(tmp_path),
                data={
                    "odoo_version": unsupported_version,
                    "postgres_version": "16",
                    "use_odooclaw": True,
                },
                vcs_ref="test",
                defaults=True,
                overwrite=True,
                unsafe=True,
            )

        devel_data = yaml.safe_load((tmp_path / "devel.yaml").read_text())
        prod_data = yaml.safe_load((tmp_path / "prod.yaml").read_text())
        assert "odooclaw" not in devel_data.get("services", {}), (
            f"odooclaw leaked into devel.yaml for v{unsupported_version}"
        )
        assert "odooclaw" not in prod_data.get("services", {}), (
            f"odooclaw leaked into prod.yaml for v{unsupported_version}"
        )
        assert not (tmp_path / "odooclaw" / "config" / "config.json").exists()
        # Clean up for the next iteration
        for f in tmp_path.iterdir():
            if f.is_file():
                f.unlink()
            elif f.is_dir():
                import shutil

                shutil.rmtree(f)


def test_odooclaw_config_has_no_shell_expansion_syntax(
    tmp_path: Path, cloned_template: Path
):
    """The generated config.json must not contain `${VAR:-default}` style strings.

    OdooClaw loads the file via `json.Unmarshal` + `env.Parse`. The shell-style
    default expansion is not performed, so a literal `${...}` would become the
    model name at runtime. The template should emit a plain default value.
    """
    with local.cwd(cloned_template):
        run_copy(
            ".",
            str(tmp_path),
            data={
                "odoo_version": 17.0,
                "postgres_version": "16",
                "use_odooclaw": True,
            },
            vcs_ref="test",
            defaults=True,
            overwrite=True,
            unsafe=True,
        )

    config_path = tmp_path / "odooclaw" / "config" / "config.json"
    assert config_path.exists()
    raw = config_path.read_text()
    # No POSIX shell default-expansion syntax in the rendered file
    assert "${" not in raw or ":-" not in raw, (
        f"Shell-style ${{VAR:-default}} leaked into config.json:\n{raw}"
    )
    parsed = json.loads(raw)
    assert parsed["agents"]["defaults"]["model_name"] == "gpt-4o-mini"


def test_setup_script_does_not_reference_missing_example(
    tmp_path: Path, cloned_template: Path
):
    """scripts/setup-odooclaw.sh must validate config.json (template output),
    not look for a config.example.json that the template never generates.
    """
    with local.cwd(cloned_template):
        run_copy(
            ".",
            str(tmp_path),
            data={
                "odoo_version": 17.0,
                "postgres_version": "16",
                "use_odooclaw": True,
            },
            vcs_ref="test",
            defaults=True,
            overwrite=True,
            unsafe=True,
        )

    script = (tmp_path / "scripts" / "setup-odooclaw.sh").read_text()
    assert "config.example.json" not in script, (
        "setup-odooclaw.sh still references a non-existent config.example.json"
    )
    assert "config.json" in script, (
        "setup-odooclaw.sh should validate config.json directly"
    )
