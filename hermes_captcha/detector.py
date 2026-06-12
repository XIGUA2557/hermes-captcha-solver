"""验证码检测器 - 从图片/HTML 中识别验证码类型"""

import base64
from enum import Enum


class CaptchaType(Enum):
    IMAGE_TEXT = "image_text"       # 图片文字验证码（最常见）
    RECAPTCHA_V2 = "recaptcha_v2"   # Google reCAPTCHA 复选框
    RECAPTCHA_V3 = "recaptcha_v3"   # Google reCAPTCHA 隐形
    HCAPTCHA = "hcaptcha"           # hCaptcha
    CLOUDFLARE = "cloudflare"       # Cloudflare Turnstile
    SLIDER = "slider"               # 滑块验证码
    SMS = "sms"                     # 短信验证码
    UNKNOWN = "unknown"             # 未知类型


# HTML 特征匹配，用于从页面源码检测验证码类型
HTML_PATTERNS = {
    CaptchaType.RECAPTCHA_V2: [
        'google.com/recaptcha',
        'g-recaptcha',
        'recaptcha/api.js',
    ],
    CaptchaType.HCAPTCHA: [
        'hcaptcha.com',
        'h-captcha',
    ],
    CaptchaType.CLOUDFLARE: [
        'cf-turnstile',
        'challenges.cloudflare.com',
    ],
    CaptchaType.SLIDER: [
        'nc_wrapper',         # 阿里滑块
        'yidun_',             # 网易易盾
        'geetest',            # 极验
        'verify_img',         # 通用滑块
        'slideVerify',
        'dragVerify',
    ],
    CaptchaType.IMAGE_TEXT: [
        'captcha',
        '验证码',
        'verification',
        'checkcode',
        'imgcode',
        'img_code',
        'authcode',
        'passcode',
    ],
    CaptchaType.SMS: [
        'sms',
        'mobile',
        'phone',
        '发送验证码',
        '获取验证码',
        '短信',
        'send.*code',
    ],
}


def detect_from_html(html: str) -> CaptchaType:
    """从页面 HTML 中检测验证码类型"""
    html_lower = html.lower()
    # 按优先级检测（先检测具体类型，再检测通用类型）
    for captcha_type in [CaptchaType.RECAPTCHA_V2, CaptchaType.HCAPTCHA,
                          CaptchaType.CLOUDFLARE, CaptchaType.SLIDER,
                          CaptchaType.SMS, CaptchaType.IMAGE_TEXT]:
        for pattern in HTML_PATTERNS[captcha_type]:
            if pattern.lower() in html_lower:
                return captcha_type
    return CaptchaType.UNKNOWN


def detect_from_keywords(text: str) -> CaptchaType:
    """从描述文字中检测验证码类型（Hermes 可能用文字描述页面状态）"""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ['图片验证码', '图形验证码', 'image captcha',
                                         'captcha image', '验证码图片']):
        return CaptchaType.IMAGE_TEXT
    if any(kw in text_lower for kw in ['短信验证码', 'sms', '手机验证码', '发送验证码']):
        return CaptchaType.SMS
    if any(kw in text_lower for kw in ['滑块', 'slide', '拖动', 'drag']):
        return CaptchaType.SLIDER
    return CaptchaType.UNKNOWN


def solve_strategy(captcha_type: CaptchaType) -> str:
    """返回对应验证码类型的求解策略说明"""
    strategies = {
        CaptchaType.IMAGE_TEXT: (
            "图片文字验证码。策略：截图 → 发送 Telegram 人工识别 → 返回文字内容。"
        ),
        CaptchaType.SMS: (
            "短信验证码。策略：提示用户在 Telegram 查看并回复验证码。"
        ),
        CaptchaType.RECAPTCHA_V2: (
            "Google reCAPTCHA v2。策略：尝试人工点击（如已配置 CDP），"
            "否则提示用户手动完成。后续可集成 CapSolver API。"
        ),
        CaptchaType.HCAPTCHA: (
            "hCaptcha。同 reCAPTCHA 处理策略。"
        ),
        CaptchaType.CLOUDFLARE: (
            "Cloudflare Turnstile。通常不可见，等待自动通过即可。"
        ),
        CaptchaType.SLIDER: (
            "滑块验证码。需要视觉定位缺口位置并计算滑动距离。"
            "当前版本暂不支持自动求解。"
        ),
        CaptchaType.UNKNOWN: (
            "未知验证码类型。建议截图后 Telegram 人工处理。"
        ),
    }
    return strategies.get(captcha_type, strategies[CaptchaType.UNKNOWN])
