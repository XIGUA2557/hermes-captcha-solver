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
cd hermes-captcha-solver
pip install -e .
```

> **依赖**: `ddddocr`（自动安装）、`Pillow`（通常已有）。MCP 协议为 stdlib 自主实现，无需 `mcp` 包。Python 3.9+ 即可运行。

### 配置 AI 视觉（可选）

OCR 已经能处理大多数清晰验证码。如果需要 AI 复核扭曲很严重的验证码，配置 `.env`:

```bash
cp .env.example .env
# 填入 OPENAI_API_KEY 或 ANTHROPIC_API_KEY
```

不配 API Key 时，`captcha_solve` 只走 OCR（`enable_vision=False`）。

## 使用

### MCP 模式（推荐）

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  captcha-solver:
    command: python -m hermes_captcha.server
    env:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
```

### HTTP 模式

```bash
python -m hermes_captcha.server --http --port 9527
```

```bash
# 测试
curl http://127.0.0.1:9527/tools
curl -X POST http://127.0.0.1:9527/tools/call \
  -d '{"name":"captcha_solve","arguments":{"image":"/tmp/captcha.png"}}'
```

## 工具列表

| 工具 | 说明 |
|------|------|
| `captcha_solve` | 级联求解（OCR → AI 视觉） |
| `captcha_detect` | 检测验证码类型 |
| `captcha_session_check` | 检查登录 session |
| `captcha_session_save` | 保存 cookies |
| `captcha_session_load` | 加载 cookies |
| `captcha_session_list` | 列出所有 session |

## License

MIT
