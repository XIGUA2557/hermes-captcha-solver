"""
AI 视觉模型验证码求解 — 使用 GPT-4V / Claude Vision / Qwen-VL

当本地 OCR 置信度低时，用多模态大模型做二次识别。
需要配置对应的 API Key。
"""

import base64
import json
import os
from typing import Optional

import requests


class VisionSolver:
    """调用多模态 AI 识别验证码"""

    def __init__(self, provider: str = "openai"):
        """
        provider: "openai" | "claude" | "ollama" (本地多模态模型)
        """
        self.provider = provider.lower()

    def solve(self, image_bytes: bytes, website: str = "") -> dict:
        if self.provider == "openai":
            return self._solve_openai(image_bytes)
        elif self.provider == "claude":
            return self._solve_claude(image_bytes)
        elif self.provider == "ollama":
            return self._solve_ollama(image_bytes)
        else:
            return {"success": False, "method": "vision",
                    "error": f"不支持的 provider: {self.provider}"}


    def _solve_openai(self, image_bytes: bytes) -> dict:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("VISION_MODEL", "gpt-4o")

        if not api_key:
            return {"success": False, "method": "vision",
                    "error": "未配置 OPENAI_API_KEY"}

        img_b64 = base64.b64encode(image_bytes).decode()

        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        "这是一个网站登录页面的验证码图片。"
                        "请只返回图片中的验证码字符（字母数字），不要任何其他内容。"
                        "忽略干扰线和噪点，只输出你能辨认的字符。"
                        "如果无法辨认，回复 'NONE'。"
                    )},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{img_b64}",
                        "detail": "high"
                    }},
                ],
            }],
            "max_tokens": 20,
            "temperature": 0,
        }

        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=15,
            )
            data = resp.json()
            code = data["choices"][0]["message"]["content"].strip().upper()
            if code == "NONE" or len(code) > 10:
                return {"success": False, "method": "vision",
                        "error": f"AI 无法识别: {code}"}
            return {"success": True, "method": "vision", "code": code}
        except Exception as e:
            return {"success": False, "method": "vision", "error": str(e)}


    def _solve_claude(self, image_bytes: bytes) -> dict:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"success": False, "method": "vision",
                    "error": "未配置 ANTHROPIC_API_KEY"}

        img_b64 = base64.b64encode(image_bytes).decode()
        media_type = "image/png"

        payload = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 20,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": img_b64,
                    }},
                    {"type": "text", "text": (
                        "识别这张验证码图片中的字符。只输出字符本身，不要其他内容。"
                        "无法识别则回复 NONE。"
                    )},
                ],
            }],
        }

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
                timeout=15,
            )
            data = resp.json()
            code = data["content"][0]["text"].strip().upper()
            if code == "NONE" or len(code) > 10:
                return {"success": False, "method": "vision",
                        "error": f"AI 无法识别: {code}"}
            return {"success": True, "method": "vision", "code": code}
        except Exception as e:
            return {"success": False, "method": "vision", "error": str(e)}


    def _solve_ollama(self, image_bytes: bytes) -> dict:
        """使用本地 Ollama 多模态模型（如 llava, minicpm-v）"""
        model = os.environ.get("OLLAMA_VISION_MODEL", "minicpm-v")
        img_b64 = base64.b64encode(image_bytes).decode()

        try:
            resp = requests.post(
                os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434") + "/api/generate",
                json={
                    "model": model,
                    "prompt": "识别验证码图片中的字符，只输出字符内容，不要解释。无法识别则输出NONE。",
                    "images": [img_b64],
                    "stream": False,
                },
                timeout=30,
            )
            data = resp.json()
            code = data.get("response", "").strip().upper()
            if code == "NONE" or len(code) > 10:
                return {"success": False, "method": "vision",
                        "error": f"Ollama 识别失败: {code}"}
            return {"success": True, "method": "vision", "code": code}
        except Exception as e:
            return {"success": False, "method": "vision", "error": str(e)}


# ------------------------------------------------------------------
# 便捷函数
# ------------------------------------------------------------------

def solve_vision(image_bytes: bytes, provider: str = "openai") -> dict:
    """尝试用 AI 视觉模型识别验证码"""
    try:
        solver = VisionSolver(provider)
        return solver.solve(image_bytes)
    except Exception as e:
        return {"success": False, "method": "vision", "error": str(e)}
