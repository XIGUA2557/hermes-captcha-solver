# Captcha Solver

> Hermes Agent 验证码求解技能 — 纯自动化（OCR + AI 视觉）

## When to Use

当 Hermes 在浏览器自动化中遇到图片文字验证码时使用。

## Workflow

### Step 1: Check Session First

登录前先检查 session，避免触发验证码:

```
调用: captcha_session_check 参数: {"website": "<网站名>"}
```

如果 `is_valid: true` → 加载 cookies → 刷新页面 → 已登录。

### Step 2: Solve the Captcha

截图验证码元素后，调用级联求解:

```
调用: captcha_solve
参数: {
  "image": "/tmp/captcha.png",
  "website": "淘宝",
  "enable_vision": true,
  "vision_provider": "openai"
}
```

求解过程:
1. ddddocr 本地 OCR（毫秒级，高置信度直接返回）
2. AI 视觉模型复核（GPT-4V / Claude / Ollama）
3. 返回验证码结果

### Step 3: Save Session

登录成功后保存 cookies:
```
调用: captcha_session_save
参数: {"website": "<网站名>", "cookies": "<cookies JSON>"}
```

## Example

```
Hermes 浏览器 → 淘宝登录 → 出现验证码
→ 截图验证码 /tmp/captcha.png
→ captcha_solve({"image": "/tmp/captcha.png", "website": "淘宝"})
→ OCR: "A3K8" (high confidence)
→ 填入验证码 → 登录成功
→ captcha_session_save(...)
→ 下次访问跳过登录
```

## Tips

- OCR 对清晰数字字母验证码准确率 ~95%，无需任何 API Key
- AI 视觉模型用于扭曲严重或带干扰线的验证码
- 如果两种方法都失败，检查验证码图片是否完整、是否需要预处理
