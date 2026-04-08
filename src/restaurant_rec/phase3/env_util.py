from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_project_dotenv(config_path: Path | str | None = None) -> None:
    """
    Load `.env` from the config file directory (if `config_path` given), else walk parents
    of this package for a `.env` next to `config.yaml` / `pyproject.toml`, else `load_dotenv()` cwd.
    """
    candidates: list[Path] = []
    if config_path is not None:
        p = Path(config_path).resolve()
        candidates.append(p.parent / ".env")
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidates.append(parent / ".env")
        if (parent / "config.yaml").is_file() or (parent / "pyproject.toml").is_file():
            break
    for env_file in candidates:
        if env_file.is_file():
            load_dotenv(env_file)
            return
    load_dotenv()
