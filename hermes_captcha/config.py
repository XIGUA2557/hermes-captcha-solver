"""配置管理 - 从环境变量和 .env 文件加载"""

import os
from pathlib import Path


def _find_project_root() -> Path:
    candidates = [
        Path.cwd(),
        Path(__file__).resolve().parent.parent,
        Path.home() / ".hermes-captcha-solver",
    ]
    for d in candidates:
        if (d / ".env").exists() or (d / "pyproject.toml").exists():
            return d
    return candidates[1]


def _load_dotenv():
    env_path = _find_project_root() / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = value


_load_dotenv()

SESSION_DIR = Path(
    os.environ.get("SESSION_DIR") or Path.home() / ".hermes-captcha-sessions"
)
SESSION_DIR.mkdir(parents=True, exist_ok=True)
