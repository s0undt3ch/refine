from __future__ import annotations

from pathlib import Path

import pytest

from refine.config import Config
from refine.config import InvalidConfigError


@pytest.fixture
def valid_config():
    """Fixture providing a valid configuration dictionary."""
    return {
        "select": ["codemod1", "codemod2"],
        "exclude": ["codemod3"],
        "codemod_paths": [
            Path("/path/to/codemod1"),
            Path("/path/to/codemod2"),
        ],
        "process_pool_size": 4,
    }


@pytest.fixture
def invalid_config():
    """Fixture providing an invalid configuration dictionary."""
    return {
        "select": 123,  # Invalid type: should be a set of strings
        "process_pool_size": "invalid",  # Invalid type: should be an integer
    }


def test_config_from_dict_valid(valid_config):
    """Test loading a valid configuration dictionary."""
    config = Config.from_dict(valid_config)
    assert config.select == ["codemod1", "codemod2"]
    assert config.exclude == ["codemod3"]
    assert config.codemod_paths == [Path("/path/to/codemod1"), Path("/path/to/codemod2")]
    assert config.process_pool_size == 4


def test_config_from_dict_invalid(invalid_config):
    """Test loading an invalid configuration dictionary."""
    with pytest.raises(InvalidConfigError) as exc_info:
        Config.from_dict(invalid_config)
    assert "Invalid configuration" in str(exc_info.value)


def test_config_from_default_file(tmp_path, valid_config):
    """Test loading configuration from a valid TOML file."""
    config_path = tmp_path / ".refine.toml"
    config_path.write_text(
        """
        select = ["codemod1", "codemod2"]
        exclude = ["codemod3"]
        codemod_paths = ["/path/to/codemod1", "/path/to/codemod2"]
        process_pool_size = 4
        """,
        encoding="utf-8",
    )
    config = Config.from_default_file(config_path)
    assert config.select == valid_config["select"]
    assert config.exclude == valid_config["exclude"]
    assert config.codemod_paths == valid_config["codemod_paths"]
    assert config.process_pool_size == valid_config["process_pool_size"]


def test_config_from_default_file_invalid(tmp_path):
    """Test loading configuration from an invalid TOML file."""
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
        select = "codemod1"  # Invalid TOML syntax
        """,
        encoding="utf-8",
    )
    with pytest.raises(InvalidConfigError) as exc_info:
        Config.from_default_file(config_path)
    assert "Invalid configuration" in str(exc_info.value)


def test_config_from_pyproject_file(tmp_path, valid_config):
    """Test loading configuration from a pyproject TOML file."""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """
        [tool.refine]
        select = ["codemod1", "codemod2"]
        exclude = ["codemod3"]
        codemod_paths = ["/path/to/codemod1", "/path/to/codemod2"]
        process_pool_size = 4
        """,
        encoding="utf-8",
    )
    config = Config.from_pyproject_file(pyproject_path)
    assert config.select == valid_config["select"]
    assert config.exclude == valid_config["exclude"]
    assert config.codemod_paths == valid_config["codemod_paths"]
    assert config.process_pool_size == valid_config["process_pool_size"]


def test_config_from_pyproject_file_invalid(tmp_path):
    """Test loading configuration from an invalid pyproject TOML file."""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """
        [tool.refine]
        select = "codemod1"  # Invalid type
        """,
        encoding="utf-8",
    )
    with pytest.raises(InvalidConfigError) as exc_info:
        Config.from_pyproject_file(pyproject_path)
    assert "Invalid configuration" in str(exc_info.value)
