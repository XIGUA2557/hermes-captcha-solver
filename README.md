# hermes-captcha-solver

Hermes Agent 验证码自动求解插件。当 Hermes 浏览器自动化遇到网页验证码时，先调用 ddddocr 本地 OCR 毫秒级识别，置信度不够时自动切换 GPT-4V / Claude Vision / Ollama 视觉模型复核。登录成功后自动保存 cookies，下次访问同一网站直接跳过登录，不再触发验证码。纯自动化，无需人工介入。

## 安装

```bash
git clone https://github.com/XIGUA2557/hermes-captcha-solver.git
cd hermes-captcha-solver
pip install -e .
```

如需 AI 视觉复核，复制 `.env.example` 为 `.env` 并填入 `OPENAI_API_KEY`。不配也能用，纯 OCR 对清晰验证码准确率 ~90%。

## 接入 Hermes

`~/.hermes/config.yaml` 加一段：

```yaml
mcp_servers:
  captcha-solver:
    command: python
    args: ["-m", "hermes_captcha.server"]
    cwd: /path/to/hermes-captcha-solver
    env:
      PYTHONPATH: /path/to/hermes-captcha-solver
```

把 skill 装进去：

```bash
cp -r skills/captcha-solver ~/.hermes/skills/
```

重启 Hermes 即可。

## 使用流程

Hermes 加载 skill 后，验证码求解完全自动：

```
Hermes 打开登录页 → 填写账号密码 → 遇到验证码
  → 自动截图 → captcha_solve → 填入验证码 → 登录成功
  → 自动保存 cookies → 下次访问跳过登录
```

## 可用工具

| 工具 | 作用 |
|------|------|
| `captcha_solve` | 求解验证码（OCR → AI 视觉） |
| `captcha_detect` | 判断验证码类型 |
| `captcha_session_check` | 查是否有已保存的登录态 |
| `captcha_session_save` | 保存 cookies |
| `captcha_session_load` | 加载 cookies 跳过登录 |
| `captcha_session_list` | 列出所有已保存的登录态 |

## License

MIT
