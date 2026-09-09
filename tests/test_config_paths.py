"""Config paths must not depend on the current working directory.

`load_dotenv(".env")` and every relative path in .env resolved against the
CWD, so anything run from outside the repo root - a scratch script, the
scheduled Tuesday job - silently loaded no secrets and wrote output to the
wrong place. Every relative path is now anchored to the repository root.
"""

from pathlib import Path

from cbs_fantasy_tooling.config import REPO_ROOT, Config


def _empty_env(tmp_path):
    f = tmp_path / "empty.env"
    f.write_text("")
    return f


def test_repo_root_is_the_package_parent():
    assert (REPO_ROOT / "cbs_fantasy_tooling" / "config.py").exists()
    assert (REPO_ROOT / "pyproject.toml").exists()


def test_default_env_file_is_anchored_to_repo_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = Config(env_file="does-not-exist.env")
    assert cfg.env_path == REPO_ROOT / "does-not-exist.env"
    assert cfg.env_path.is_absolute()


def test_relative_output_dir_anchored_to_repo_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OUTPUT_DIR", "data/from-test")
    cfg = Config(env_file=str(_empty_env(tmp_path)))
    assert Path(cfg.output_dir) == REPO_ROOT / "data" / "from-test"


def test_absolute_paths_are_left_alone(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "abs-out"))
    cfg = Config(env_file=str(_empty_env(tmp_path)))
    assert Path(cfg.output_dir) == tmp_path / "abs-out"


def test_credentials_and_token_anchored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    monkeypatch.setenv("GMAIL_TOKEN_FILE", "token.json")
    cfg = Config(env_file=str(_empty_env(tmp_path)))
    assert Path(cfg.gmail_credentials_file) == REPO_ROOT / "credentials.json"
    assert Path(cfg.gmail_token_file) == REPO_ROOT / "token.json"


def test_history_dir_defaults_to_output_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", "data/x")
    monkeypatch.delenv("HISTORY_DIR", raising=False)
    cfg = Config(env_file=str(_empty_env(tmp_path)))
    assert cfg.history_dir == cfg.output_dir


def test_env_file_in_cwd_is_not_read(tmp_path, monkeypatch):
    """The regression: a .env in the CWD must not shadow the repo's .env."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text('OUTPUT_DIR="data/FROM_CWD"\n')
    monkeypatch.delenv("OUTPUT_DIR", raising=False)
    cfg = Config()
    assert "FROM_CWD" not in cfg.output_dir
