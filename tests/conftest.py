"""Shared pytest fixtures for FTE tests."""

import pytest
from pathlib import Path


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """A fully initialized vault in a temp directory."""
    from fte.vault import init_vault
    init_vault(tmp_path)
    return tmp_path


@pytest.fixture
def needs_action_file(vault: Path) -> Path:
    """A sample task file pre-placed in Needs_Action/."""
    f = vault / "Needs_Action" / "2026-02-20-120000-reply-to-client.md"
    f.write_text("Client asked about project timeline. Please draft a reply.")
    return f
