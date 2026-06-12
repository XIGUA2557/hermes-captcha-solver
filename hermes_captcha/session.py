"""浏览器 Session 持久化 - 保存/恢复登录状态，避免重复触发验证码"""

import json
import time
from pathlib import Path
from typing import Optional

from . import config


def save(website: str, cookies: list[dict]) -> Path:
    """
    保存浏览器 cookies 到磁盘。

    cookies 格式: [{"name": "...", "value": "...", "domain": "..."}, ...]
    """
    safe_name = _safe_filename(website)
    path = config.SESSION_DIR / f"{safe_name}.json"
    data = {
        "website": website,
        "cookies": cookies,
        "saved_at": time.time(),
        "saved_at_iso": _now_iso(),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load(website: str, max_age_hours: float = 72) -> Optional[list[dict]]:
    """
    加载之前保存的 cookies。

    max_age_hours: cookies 最久有效时间，超过则返回 None
    """
    safe_name = _safe_filename(website)
    path = config.SESSION_DIR / f"{safe_name}.json"
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, KeyError):
        return None

    saved_at = data.get("saved_at", 0)
    age_hours = (time.time() - saved_at) / 3600
    if age_hours > max_age_hours:
        return None  # 过期

    return data.get("cookies", [])


def check(website: str, max_age_hours: float = 72) -> dict:
    """检查指定网站的 session 状态"""
    safe_name = _safe_filename(website)
    path = config.SESSION_DIR / f"{safe_name}.json"
    if not path.exists():
        return {"exists": False, "website": website}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        saved_at = data.get("saved_at", 0)
        age_hours = (time.time() - saved_at) / 3600
        return {
            "exists": True,
            "website": website,
            "saved_at": data.get("saved_at_iso", "unknown"),
            "age_hours": round(age_hours, 1),
            "is_valid": age_hours <= max_age_hours,
            "cookie_count": len(data.get("cookies", [])),
        }
    except Exception:
        return {"exists": False, "website": website}


def delete(website: str) -> bool:
    """删除指定网站的 session"""
    safe_name = _safe_filename(website)
    path = config.SESSION_DIR / f"{safe_name}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def list_all() -> list[dict]:
    """列出所有已保存的 session"""
    sessions = []
    for f in sorted(config.SESSION_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append({
                "file": f.name,
                "website": data.get("website", "unknown"),
                "saved_at": data.get("saved_at_iso", "unknown"),
                "cookie_count": len(data.get("cookies", [])),
            })
        except Exception:
            pass
    return sessions


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    """将网站名转换为安全的文件名"""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return safe.strip("_") or "unknown"


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()[:19] + "Z"
