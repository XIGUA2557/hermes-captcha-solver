# Gmail Browser

> 浏览器自动化登录 Gmail，配合 captcha-solver 处理验证码

## When to Use

用户说以下任意一句话时加载本技能：

- "帮我登录 Gmail"
- "帮我查一下邮件"
- "帮我发一封邮件"
- "检查我的 Gmail 收件箱"

---

## 登录流程

### Step 1：检查 session

```
→ captcha_session_check({"website": "gmail.com"})

如果 is_valid: true  → 加载 cookies → 跳转 gmail → 已登录 ✅
如果 is_valid: false → 继续下一步
```

### Step 2：导航到 Gmail

浏览器打开 `https://mail.google.com/`，Google 会自动跳转到登录页。

### Step 3：填写邮箱

- 定位 email 输入框（`input[type="email"]`）
- 填入用户邮箱地址（如用户未提供则询问）
- 点击"下一步"

### Step 4：填写密码

- 等待密码输入框出现
- 填入密码（如用户未提供则询问）
- 点击"下一步"

### Step 5：处理二次验证（2FA）

Google 可能弹出以下任一验证方式：

| 验证方式 | 处理 |
|---------|------|
| 手机 Google 提示 | 告知用户："请在手机上点击「是」以确认登录"，等待 30 秒后检查是否跳转 |
|  Authenticator 验证码 | 告知用户："请输入 Google Authenticator 中的 6 位数字验证码" |
| 短信验证码 | 告知用户："请输入手机收到的 Google 验证码" |
| 备用验证码 | 告知用户："请提供一个 Google 备用验证码" |
| 图片验证码 | 调用 captcha-solver: 截图 → captcha_solve → 填入 |

**关键**：Google 的 2FA 页面需要用户手动完成，Hermes 应提示用户并等待。

### Step 6：确认登录成功

登录成功标志：
- URL 变为 `mail.google.com/mail/...`
- 页面出现收件箱列表
- 不再有登录表单或验证页面

### Step 7：保存 session

```
cookies = await browser_context.cookies()
→ captcha_session_save({"website": "gmail.com", "cookies": json.dumps(cookies)})
```

---

## 常用操作（登录后）

### 查收件箱

浏览器打开 `https://mail.google.com/mail/u/0/#inbox`，读取邮件列表。定位：
- 邮件行: `tr.zA` 或 `div[role="row"]`
- 发件人: `span[email]` 或 `td.yX`
- 主题: `span.bog`
- 摘要: `span.y2`

### 搜索邮件

导航到 `https://mail.google.com/mail/u/0/#search/<关键词>`

### 读邮件内容

点击邮件行 → 等待邮件内容加载 → 获取 `.a3s.aiL` 内的文本。

### 发邮件

1. 点击"撰写"按钮: `div.T-I.T-I-KE.L3`
2. 填写收件人: `textarea[name="to"]`
3. 填写主题: `input[name="subjectbox"]`
4. 填写正文: `div[aria-label="邮件正文"]`
5. 点击"发送": `div.T-I.J-J5-Ji.aoO.T-I-atl.L3`

### 回复邮件

打开邮件后点击"回复": `div[data-tooltip="回复"]`，后续同发邮件流程。

---

## 注意事项

- Google 登录如果连续失败验证码，可能触发风控锁定账户，建议最多重试 2 次
- Gmail 页面元素 class 名是动态混淆的（如 `T-I-KE`），但 `role` 和 `aria-label` 属性相对稳定，优先用这些定位
- 如果用户开启了"无密码登录"（Passkey），可能需要强制使用密码登录：点击"尝试其他方式登录" → 选择"密码"
- 建议 `max_age_hours` 设为 24 小时（Gmail session 比一般网站更容易过期）
