"""Configuration loading for command line entrypoints.

The config file is JSON syntax stored with a .yaml extension. JSON is valid
YAML, but using the standard library keeps this project easy to run in a fresh
hackathon environment without requiring PyYAML.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_config(path: str | Path) -> Dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def project_path(path: str | Path, *, root: str | Path) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    return Path(root) / raw

