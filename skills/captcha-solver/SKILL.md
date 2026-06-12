# Captcha Solver

> 纯自动化验证码求解 — OCR + AI 视觉，无需人工介入

## When to Use

以下任一情况出现时**必须**加载本技能：

| 触发条件 | 示例 |
|----------|------|
| 浏览器页面出现图片验证码 | 登录页、注册页的图形验证码 |
| 表单提交后被拦截要求输入验证码 | "请输入右侧验证码" |
| 页面提示需要短信/邮箱验证码 | "验证码已发送至您的手机" |
| 登录流程中检测到 reCAPTCHA/hCaptcha | Google 机器人验证 |
| 用户说"帮我登录XX网站" | 淘宝、京东、银行等需要验证码的网站 |

---

## Tool Reference

本技能提供以下 MCP 工具，全部通过 `captcha-solver` MCP Server 调用。

### captcha_solve — 求解验证码（主工具）

```
参数:
  image            (必填) 验证码图片。支持: 本地文件路径 / base64编码 / data:image URI
  website          (可选) 网站名，用于日志标记，如 "淘宝"、"京东"
  enable_vision    (可选) 是否启用 AI 视觉复核，默认 true
  vision_provider  (可选) AI 提供方: openai | claude | ollama，默认 openai

返回:
  success: true/false
  code:    "ABCD"     ← 识别出的验证码文字（全大写）
  method:  "ocr" | "vision"
  confident: true/false
  attempts: [...]     ← 各级求解的尝试记录
```

**求解逻辑**：先 ddddocr 本地 OCR（毫秒级），高置信度直接返回；否则调 AI 视觉复核。

### captcha_detect — 检测验证码类型

```
参数:
  input   (必填) 页面 HTML 源码 或 文字描述
  source  (可选) "html" | "description"，默认 "description"

返回:
  captcha_type: "image_text" | "recaptcha_v2" | "hcaptcha" | "slider" | "sms" | "unknown"
  strategy:     推荐的求解策略说明
```

### captcha_session_check — 检查登录状态

```
参数:
  website       (必填) 网站标识
  max_age_hours (可选) 有效期(小时)，默认 72

返回:
  exists: true/false
  is_valid: true/false    ← 存在且未过期
  age_hours: 已保存时长
  cookie_count: cookies 数量
```

### captcha_session_save — 保存登录状态

```
参数:
  website (必填) 网站标识
  cookies (必填) cookies JSON 字符串 ← 从 Playwright browser_context.cookies() 获取

返回:
  success: true/false
  saved_to: 文件路径
```

### captcha_session_load — 恢复登录状态

```
参数:
  website       (必填) 网站标识
  max_age_hours (可选) 有效期(小时)，默认 72

返回:
  success: true/false
  cookies: [...]  ← 可直接传给 browser_context.add_cookies()
```

### captcha_session_list — 列出所有 session

```
无参数。返回所有已保存的 session 摘要列表。
```

---

## Complete Workflow

### 场景 A：登录带验证码的网站（完整流程）

```
Step 0: 获取网站标识
  从 URL 提取域名作为 website 参数，如:
  https://login.taobao.com/... → website = "taobao.com"
  https://passport.jd.com/...   → website = "jd.com"

Step 1: 先查 session（避免触发验证码）
  → captcha_session_check({"website": "taobao.com"})

  如果 is_valid = true:
    → captcha_session_load({"website": "taobao.com"})
    → 将返回的 cookies 全部添加到浏览器: browser_context.add_cookies(cookies)
    → 刷新页面，通常已处于登录态，直接跳过后续步骤
  如果 is_valid = false:
    → 继续下一步

Step 2: 导航到登录页，填写账号密码
  注意: 填写速度不要太快，模拟人类打字节奏（每字符间隔 50-200ms）

Step 3: 检测验证码类型
  → 获取当前页面 HTML: page.content()
  → captcha_detect({"input": html, "source": "html"})

  根据返回的 captcha_type 决定策略:
  - "image_text": 继续 Step 4-5
  - "recaptcha_v2" / "hcaptcha": 提示用户当前版本暂不支持自动求解此类验证码
  - "slider": 提示用户当前版本暂不支持滑块验证码
  - "sms": 提示用户查看手机短信，或在对话中询问验证码
  - "unknown": 继续 Step 4，尝试通用求解

Step 4: 截图验证码元素并求解
  → 定位验证码图片元素（通常是 <img> 标签，src 包含 captcha/code/verify 等关键词）
  → 截图该元素，保存为本地 PNG 文件（如 /tmp/captcha.png）
  → captcha_solve({
        "image": "/tmp/captcha.png",
        "website": "taobao.com",
        "enable_vision": true
      })

  关键: 截图务必只包含验证码区域，裁掉周围留白，提高识别准确率。

Step 5: 填入验证码并提交
  → 定位验证码输入框
  → 填入返回的 code（全大写）
  → 点击登录/提交按钮
  → 等待页面跳转或提示

Step 6: 判断登录结果
  成功标志:
  - URL 跳转到用户主页或目标页面
  - 页面出现用户名/头像等登录态元素
  - 不再有登录表单

  失败处理:
  - 如果提示"验证码错误": 点击刷新验证码 → 回到 Step 4
  - 如果提示"验证码已过期": 点击刷新验证码 → 回到 Step 4
  - 连续失败 3 次: 告知用户，暂停自动化

Step 7: 保存 session
  → 登录成功后立即保存 cookies:
  → cookies = await browser_context.cookies()
  → captcha_session_save({"website": "taobao.com", "cookies": json.dumps(cookies)})

  这样下次访问同一网站时，Step 1 就能直接命中 session，跳过登录。
```

### 场景 B：用户说"帮我登录XX"（快捷流程）

```
用户说"帮我登录淘宝" → 加载 captcha-solver skill
  ↓
1. captcha_session_check("taobao.com")
   → valid? 直接回复"已登录"
   → 不行? 继续
2. 浏览器打开登录页
3. 如果用户提供了账号密码，直接填写
   否则询问: "请提供淘宝账号和密码"
4. 检测验证码 → captcha_solve → 填入
5. 登录成功 → captcha_session_save → 回复"已登录淘宝，下次自动跳过验证"
```

### 场景 C：没有 API Key 仅用 OCR

```
captcha_solve 参数中 enable_vision 设为 false:
  captcha_solve({"image": "...", "website": "...", "enable_vision": false})

→ 只用 ddddocr 本地 OCR
→ 无需任何 API Key
→ 对清晰数字字母验证码准确率 ~90%+
→ 适合大多数国内网站的简单验证码
```

---

## Important Notes

### 截图技巧
- **精确定位**：用 CSS 选择器或 XPath 定位验证码 `<img>` 元素
- **只截验证码**：不要截整个页面，只截 `<img>` 元素本身
- **避免缩放**：截图保持原始分辨率，不要缩放
- **格式用 PNG**：无损格式，不要用 JPEG（压缩噪点会干扰 OCR）

### 验证码刷新
- OCR 识别失败时，先尝试点击验证码图片刷新，重新截图再试
- 同一次登录最多重试 3 次，超过则告知用户

### Session 管理
- session 默认有效期 72 小时，超时自动失效
- 同一网站只保留最新 session
- 用 `captcha_session_list` 查看所有已保存的登录态
- 敏感网站（银行等）建议设置较短的 `max_age_hours`

### 错误处理
- `captcha_solve` 返回 `success: false` → 查看 `attempts` 了解失败原因
- OCR 低置信度 + 未启用 AI 视觉 → 结果可能不准确，建议重试或刷新验证码
- OCR 和 AI 都失败 → 告知用户，建议人工介入

### AI 视觉配置
- 使用 GPT-4V: 设置环境变量 `OPENAI_API_KEY`，`vision_provider="openai"`
- 使用 Claude: 设置环境变量 `ANTHROPIC_API_KEY`，`vision_provider="claude"`
- 使用本地模型: 设置 `OLLAMA_VISION_MODEL`，`vision_provider="ollama"`

---

## 验证码类型识别参考

| 类型 | HTML 特征 | 求解策略 |
|------|----------|---------|
| 图片文字 | `<img src="...captcha...">`、`<input name="captcha">` | ✅ captcha_solve |
| reCAPTCHA v2 | `google.com/recaptcha`、`g-recaptcha` | ⚠️ 提示用户手动完成 |
| hCaptcha | `hcaptcha.com`、`h-captcha` | ⚠️ 提示用户手动完成 |
| Cloudflare | `cf-turnstile` | ✅ 通常自动通过，等待即可 |
| 滑块 | `geetest`、`nc_wrapper`、`yidun_` | ❌ 当前版本不支持 |
| 短信 | `sms`、`发送验证码`、`手机验证码` | ⚠️ 引导用户查看手机 |

---

## Example Dialogs

### 示例 1：OCR 直接命中

```
Hermes: 正在登录淘宝...
        → captcha_session_check → 无 session
        → 打开登录页 → 填写账号密码
        → 检测到图片验证码 → 截图
        → captcha_solve({image: "/tmp/captcha.png", website: "taobao.com"})
        → 返回: {success: true, code: "A3K8", method: "ocr", confident: true}
        → 填入 A3K8 → 登录成功
        → captcha_session_save → session 已保存
        ✅ 已登录淘宝（下次自动跳过验证码）
```

### 示例 2：OCR 低置信度 → AI 复核

```
Hermes: 正在登录...
        → captcha_solve({image: "/tmp/captcha.png", website: "jd.com"})
        → OCR: "X7MP2Q" (低置信度)
        → AI Vision: "X7MP2Q" ✅ (与 OCR 一致，高置信度确认)
        → 返回: {success: true, code: "X7MP2Q", method: "vision", confident: true}
```

### 示例 3：session 命中跳过登录

```
Hermes: 正在登录淘宝...
        → captcha_session_check("taobao.com") → {exists: true, is_valid: true}
        → captcha_session_load("taobao.com") → 3 cookies
        → 加载 cookies → 刷新页面 → 已处于登录态
        ✅ 已登录淘宝（session 命中，无需验证码）
```
