"""
本地 OCR 验证码识别 — 使用 ddddocr

ddddocr 是专门针对国内网站验证码训练的轻量 OCR 库:
- 无需 GPU，CPU 推理毫秒级
- 支持扭曲、粘连、带干扰线的数字字母
- 支持点选验证码（文字识别模式）
- pip install ddddocr 即可，无外部依赖
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ddddocr 内部使用 Image.ANTIALIAS（Pillow 10+ 已移除），需补丁
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

try:
    import ddddocr
    HAS_DDDD = True
except ImportError:
    HAS_DDDD = False
    ddddocr = None


class OcrSolver:
    """ddddocr 验证码识别器 —— 单例，避免重复加载模型"""

    def __init__(self):
        if not HAS_DDDD:
            raise ImportError("请安装 ddddocr: pip install ddddocr")
        self._ocr = ddddocr.DdddOcr()

    def solve(self, image_bytes: bytes) -> tuple[str, bool]:
        """
        识别验证码图片中的文字。

        返回: (结果文本, 是否高置信度)
        """
        result = self._ocr.classification(image_bytes)
        if not result:
            return "", False

        text = result.strip().upper()
        confidence = self._evaluate_confidence(text)
        return text, confidence


    def _evaluate_confidence(self, text: str) -> bool:
        """
        启发式评估识别结果是否可信。

        高置信度条件:
        - 长度在 4-6 位（常见验证码长度）
        - 全是字母数字，没有乱码字符
        - 不是全部相同的字符
        """
        if len(text) < 3 or len(text) > 8:
            return False
        if not text.isalnum():
            return False
        if len(set(text)) == 1:  # 全是同一个字符（如 "1111"）
            return False
        return True


# 单例
_ocr_solver: Optional[OcrSolver] = None


def solve_ocr(image_bytes: bytes) -> dict:
    """
    便捷函数: 尝试用 OCR 识别验证码。

    返回:
        {"success": True, "code": "ABCD", "method": "ocr"}
        {"success": False, "method": "ocr", "error": "..."}
    """
    global _ocr_solver

    if not HAS_DDDD:
        return {"success": False, "method": "ocr",
                "error": "ddddocr 未安装。安装: pip install ddddocr"}

    try:
        if _ocr_solver is None:
            _ocr_solver = OcrSolver()
        text, confident = _ocr_solver.solve(image_bytes)
    except Exception as e:
        return {"success": False, "method": "ocr", "error": str(e)}

    if not text:
        return {"success": False, "method": "ocr",
                "error": "OCR 未能识别出任何字符"}

    result = {"success": True, "method": "ocr", "code": text, "confident": confident}
    if not confident:
        result["warning"] = "识别结果置信度低，建议人工核对"
    return result
