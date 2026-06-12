"""
级联验证码求解器 — 纯自动化

策略顺序:
  L1: ddddocr 本地 OCR（免费、毫秒级、无网络依赖）
  L2: AI 视觉模型（GPT-4V / Claude / Ollama，可选）
"""

import logging
from io import BytesIO
from typing import Union

logger = logging.getLogger(__name__)


def solve(
    image: Union[str, bytes],
    website: str = "",
    enable_vision: bool = True,
    vision_provider: str = "openai",
) -> dict:
    """
    纯自动化求解验证码: OCR → AI 视觉。
    """
    # 解析图片
    try:
        img_bytes = _to_bytes(image)
    except Exception as e:
        return {"success": False, "error": f"图片解析失败: {e}", "method": "none"}

    # 图片太大先压缩
    if len(img_bytes) > 1024 * 1024:
        img_bytes = _compress(img_bytes)

    attempts: list[dict] = []

    # ── L1: 本地 OCR ──────────────────────────────────
    from . import ocr_solver
    ocr = ocr_solver.solve_ocr(img_bytes)
    attempts.append(ocr)

    if ocr["success"] and ocr.get("confident"):
        return _ok(ocr["code"], "ocr", ocr.get("confident"), attempts)

    # ── L2: AI 视觉模型 ───────────────────────────────
    if not enable_vision:
        # 不启用 AI 时直接返回 OCR 结果（即使低置信度）
        if ocr["success"]:
            return _ok(ocr["code"], "ocr", False, attempts)
        return _fail("OCR 无法识别，且未启用 AI 视觉复核", attempts)

    from . import vision_solver as vs
    vis = vs.solve_vision(img_bytes, vision_provider)
    attempts.append(vis)

    if vis["success"]:
        confidence = "high" if ocr.get("code") == vis["code"] else "medium"
        return _ok(vis["code"], "vision", confidence, attempts)

    # 全部失败
    return _fail(
        f"OCR 和 AI 均未识别: OCR={ocr.get('error','?')}, AI={vis.get('error','?')}",
        attempts,
    )


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def _ok(code: str, method: str, confidence: Union[bool, str], attempts: list) -> dict:
    return {
        "success": True,
        "code": code,
        "method": method,
        "confident": bool(confidence),
        "attempts": [{"method": a["method"], "success": a.get("success"), "code": a.get("code")} for a in attempts],
    }


def _fail(error: str, attempts: list[dict]) -> dict:
    return {
        "success": False,
        "error": error,
        "method": "none",
        "attempts": [{"method": a["method"], "success": a.get("success"), "code": a.get("code")} for a in attempts],
    }


def _to_bytes(image: Union[str, bytes]) -> bytes:
    """统一将各种格式的输入转为 bytes"""
    import base64
    from pathlib import Path

    if isinstance(image, bytes):
        return image

    if isinstance(image, str):
        p = Path(image)
        if p.exists() and p.is_file():
            return p.read_bytes()
        if image.startswith("data:"):
            image = image.split(",", 1)[1]
        try:
            return base64.b64decode(image)
        except Exception:
            raise ValueError(f"无法解析图片: 不是有效的 base64、路径或 bytes")

    raise TypeError(f"不支持的图片类型: {type(image)}")


def _compress(image_bytes: bytes, max_side: int = 800) -> bytes:
    """压缩 PNG 图片"""
    try:
        from PIL import Image
        img = Image.open(BytesIO(image_bytes))
        w, h = img.size
        if max(w, h) > max_side:
            ratio = max_side / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except ImportError:
        return image_bytes
