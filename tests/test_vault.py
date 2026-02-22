"""Tests for fte.vault — vault initialization."""

from pathlib import Path
import pytest
from fte.vault import init_vault, REQUIRED_DIRS


def test_creates_all_required_dirs(tmp_path: Path):
    init_vault(tmp_path)
    for d in REQUIRED_DIRS:
        assert (tmp_path / d).is_dir(), f"Missing directory: {d}"


def test_creates_company_handbook(tmp_path: Path):
    init_vault(tmp_path)
    handbook = tmp_path / "Company_Handbook.md"
    assert handbook.exists()
    assert "Rules of Engagement" in handbook.read_text()


def test_creates_dashboard(tmp_path: Path):
    init_vault(tmp_path)
    assert (tmp_path / "Dashboard.md").exists()


def test_idempotent_on_rerun(tmp_path: Path):
    """Running init twice must not raise and must not overwrite existing files."""
    init_vault(tmp_path)
    # Write sentinel content to handbook
    handbook = tmp_path / "Company_Handbook.md"
    handbook.write_text("# My Custom Handbook")

    init_vault(tmp_path)  # second run

    # Existing handbook content preserved
    assert handbook.read_text() == "# My Custom Handbook"
    # All dirs still exist
    for d in REQUIRED_DIRS:
        assert (tmp_path / d).is_dir()


def test_returns_status_tuples(tmp_path: Path):
    results = init_vault(tmp_path)
    names = [r[0] for r in results]
    statuses = [r[1] for r in results]

    assert "Inbox/" in names
    assert "Company_Handbook.md" in names
    assert all(s in ("created", "exists") for s in statuses)


def test_existing_items_report_exists(tmp_path: Path):
    init_vault(tmp_path)
    results = init_vault(tmp_path)
    statuses = {name: status for name, status in results}
    assert statuses["Inbox/"] == "exists"
    assert statuses["Company_Handbook.md"] == "exists"


def test_creates_vault_root_if_missing(tmp_path: Path):
    target = tmp_path / "deep" / "nested" / "vault"
    init_vault(target)
    assert target.is_dir()
    assert (target / "Inbox").is_dir()


def test_logs_vault_init_action(tmp_path: Path):
    init_vault(tmp_path)
    logs_dir = tmp_path / "Logs"
    assert logs_dir.exists()
    log_files = list(logs_dir.glob("*.json"))
    assert len(log_files) == 1
    content = log_files[0].read_text()
    assert "vault_init" in content
