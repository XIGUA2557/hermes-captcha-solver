# hermes-captcha-solver

Hermes Agent 验证码自动求解 MCP 插件 — 纯自动化，无需人工介入。

## 原理

```
验证码图片
  ↓
① ddddocr 本地 OCR（毫秒级、免费、离线）
  ↓ 低置信度
② AI 视觉模型（GPT-4V / Claude / Ollama）复核
  ↓
返回验证码文字
```

## 安装

```bash
git clone https://github.com/XIGUA2557/hermes-captcha-solver.git
cd hermes-captcha-solver
pip install -e .
```

> **依赖**: `ddddocr`（自动安装）、`Pillow`（通常已有）。MCP 协议为 stdlib 自实现，零外部依赖。Python 3.9+ 即可。

### 配置 AI 视觉（可选）

OCR 已能处理大多数清晰验证码。如需 AI 复核扭曲严重的验证码：

```bash
cp .env.example .env
# 填入 OPENAI_API_KEY 或 ANTHROPIC_API_KEY
# 或用 Ollama 本地视觉模型: OLLAMA_VISION_MODEL=minicpm-v
```

不配 API Key 时走纯 OCR。

## 接入 Hermes

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  captcha-solver:
    command: python
    args: ["-m", "hermes_captcha.server"]
    cwd: /path/to/hermes-captcha-solver
    env:
      PYTHONPATH: /path/to/hermes-captcha-solver
```

安装 Skill：

```bash
cp -r skills/captcha-solver ~/.hermes/skills/
```

重启 Hermes，`captcha_*` 工具自动可用。

## 工具参考

### captcha_solve — 求解验证码（主工具）

先 ddddocr 本地 OCR（毫秒级），高置信度直接返回；否则调 AI 视觉复核。

```
参数:
  image            (必填) 验证码图片: 文件路径 / base64 / data:image URI
  website          (可选) 网站名，如 "淘宝"
  enable_vision    (可选) 启用 AI 视觉复核，默认 true
  vision_provider  (可选) openai | claude | ollama，默认 openai

返回:
  { success: true, code: "A3K8", method: "ocr", confident: true }
```

### captcha_detect — 检测验证码类型

```
参数:
  input   (必填) 页面 HTML 或文字描述
  source  (可选) "html" | "description"

返回:
  { captcha_type: "image_text"|"recaptcha_v2"|"hcaptcha"|"slider"|"sms"|"unknown",
    strategy: "求解策略说明" }
```

### captcha_session_* — 登录态管理

| 工具 | 说明 |
|------|------|
| `captcha_session_check` | 检查是否有已保存的登录 session |
| `captcha_session_save` | 保存 cookies（登录成功后调用） |
| `captcha_session_load` | 加载 cookies（跳过登录） |
| `captcha_session_list` | 列出所有已保存的 session |

---

## 使用指南

### 完整登录流程（7 步）

```
Step 1: 查 session
  → captcha_session_check({"website": "taobao.com"})
  → valid? 加载 cookies → 刷新 → 已登录 ✅ 跳过后续

Step 2: 打开登录页，填写账号密码
  注意: 模拟人类打字节奏，每字符间隔 50-200ms

Step 3: 检测验证码类型
  → captcha_detect({"input": html, "source": "html"})

Step 4: 截图验证码元素并求解
  → 定位验证码 <img> 元素（src 含 captcha/code/verify）
  → 截图保存为 PNG（只截验证码区域，裁掉留白）
  → captcha_solve({"image": "/tmp/captcha.png", "website": "taobao.com"})

Step 5: 填入验证码并提交
  → 定位输入框 → 填入 code → 点击登录

Step 6: 判断结果
  成功: URL 跳转 → 出现用户名/头像
  失败: "验证码错误" → 点击刷新验证码 → 回到 Step 4
       连续失败 3 次 → 告知用户

Step 7: 保存 session
  → cookies = await browser_context.cookies()
  → captcha_session_save({"website": "taobao.com", "cookies": json.dumps(cookies)})
```

### 快速场景

**用户说"帮我登录XX"**：

```
1. captcha_session_check("taobao.com") → valid? 直接回复 ✅
2. 浏览器打开登录页 → 填写账号密码
3. 检测验证码 → captcha_solve → 填入
4. 登录成功 → captcha_session_save → "已登录，下次自动跳过"
```

**无 API Key 纯 OCR**：

```
captcha_solve({"image": "...", "enable_vision": false})
→ 只用 ddddocr，无需任何 API Key，清晰数字字母 ~90% 准确率
```

### 截图技巧

- 用 CSS 选择器精确定位验证码 `<img>`，只截图该元素
- 保存为 PNG 格式（无损，JPEG 噪点会干扰 OCR）
- 不要缩放，保持原始分辨率

### 验证码类型识别

| 类型 | HTML 特征 | 求解策略 |
|------|----------|---------|
| 图片文字 | `<img src="...captcha...">` | ✅ captcha_solve |
| reCAPTCHA v2 | `google.com/recaptcha` | ⚠️ 手动完成 |
| hCaptcha | `hcaptcha.com` | ⚠️ 手动完成 |
| Cloudflare | `cf-turnstile` | ✅ 等待自动通过 |
| 滑块 | `geetest`、`nc_wrapper` | ❌ 暂不支持 |
| 短信 | `发送验证码` | ⚠️ 引导查看手机 |

### 错误处理

| 情况 | 处理 |
|------|------|
| `success: false` | 查看 `attempts` 了解 OCR/AI 各自失败原因 |
| OCR 低置信度 | 结果可能不准，刷新验证码重试 |
| OCR + AI 都失败 | 告知用户，建议人工介入 |
| 验证码错误 | 刷新验证码重新求解，最多 3 次 |
| session 过期 | 重新走完整登录流程 |

### AI 视觉配置

| 模型 | 环境变量 | vision_provider |
|------|---------|-----------------|
| GPT-4V | `OPENAI_API_KEY` | `"openai"` |
| Claude | `ANTHROPIC_API_KEY` | `"claude"` |
| Ollama 本地 | `OLLAMA_VISION_MODEL` | `"ollama"` |

---

## 示例对话

**OCR 直接命中**：

```
Hermes: 正在登录淘宝...
  → captcha_solve({image: "/tmp/captcha.png", website: "taobao.com"})
  → {success: true, code: "A3K8", method: "ocr", confident: true}
  → 填入 A3K8 → 登录成功
  → captcha_session_save → session 已保存
  ✅ 已登录淘宝（下次自动跳过验证码）
```

**session 命中**：

```
Hermes: 正在登录淘宝...
  → captcha_session_check("taobao.com") → {is_valid: true}
  → 加载 cookies → 刷新 → 已登录
  ✅ 无需验证码
```

**OCR + AI 复核**：

```
Hermes: 正在登录...
  → captcha_solve({...})
  → OCR: "X7MP2Q" (低置信度)
  → AI Vision: "X7MP2Q" ✅
  → {success: true, code: "X7MP2Q", method: "vision", confident: true}
```

---

## 项目结构

```
hermes-captcha-solver/
├── hermes_captcha/
│   ├── server.py          # MCP stdio + HTTP 双模式
│   ├── solver.py          # OCR → AI Vision 级联调度
│   ├── ocr_solver.py      # ddddocr 本地识别
│   ├── vision_solver.py   # GPT-4V / Claude / Ollama
│   ├── detector.py        # 6 种验证码类型检测
│   ├── session.py         # Cookies 持久化
│   └── config.py          # 配置加载
├── skills/captcha-solver/
│   └── SKILL.md           # Hermes Skill 定义
└── tests/                 # 测试验证码图片
```

## License

MIT
