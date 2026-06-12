"""
hermes-captcha-solver MCP Server — 纯自动化验证码求解

协议: MCP (Model Context Protocol) over stdio JSON-RPC
依赖: 仅 stdlib + ddddocr

工具:
  captcha_solve          - 级联求解: OCR → AI 视觉
  captcha_detect         - 检测验证码类型
  captcha_session_*      - 浏览器 session 持久化
"""

import json
import sys
import os

from . import detector
from . import session
from . import solver


# ---------------------------------------------------------------------------
# 工具定义
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "captcha_solve",
        "description": (
            "【主工具】纯自动化求解验证码。\n"
            "先本地 ddddocr OCR 识别（毫秒级、免费），高置信度直接返回。\n"
            "低置信度时自动调用 AI 视觉模型（GPT-4V/Claude/Ollama）复核。\n"
            "无需人工介入。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "image": {
                    "type": "string",
                    "description": "验证码图片（base64 / 文件路径 / bytes）",
                },
                "website": {
                    "type": "string",
                    "description": "网站名，用于标识和日志",
                },
                "enable_vision": {
                    "type": "boolean",
                    "description": "是否启用 AI 视觉识别（默认开启，需配 API Key）",
                    "default": True,
                },
                "vision_provider": {
                    "type": "string",
                    "enum": ["openai", "claude", "ollama"],
                    "description": "AI 视觉模型提供商",
                    "default": "openai",
                },
            },
            "required": ["image"],
        },
    },
    {
        "name": "captcha_detect",
        "description": "检测验证码类型（从页面 HTML 或文字描述）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "页面 HTML 源码或文字描述",
                },
                "source": {
                    "type": "string",
                    "enum": ["html", "description"],
                    "description": "输入类型",
                    "default": "description",
                },
            },
            "required": ["input"],
        },
    },
    {
        "name": "captcha_session_check",
        "description": "检查网站是否已有保存的登录 session（cookies）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "website": {"type": "string", "description": "网站名称或域名"},
                "max_age_hours": {
                    "type": "number",
                    "description": "有效期限（小时）",
                    "default": 72,
                },
            },
            "required": ["website"],
        },
    },
    {
        "name": "captcha_session_save",
        "description": "保存浏览器 cookies，登录成功后调用",
        "inputSchema": {
            "type": "object",
            "properties": {
                "website": {"type": "string", "description": "网站名称或域名"},
                "cookies": {
                    "type": "string",
                    "description": (
                        "cookies JSON 数组字符串。"
                        "格式: [{\"name\":\"session\",\"value\":\"abc\",\"domain\":\".example.com\"}]"
                    ),
                },
            },
            "required": ["website", "cookies"],
        },
    },
    {
        "name": "captcha_session_load",
        "description": "加载已保存的登录 session（cookies）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "website": {"type": "string", "description": "网站名称或域名"},
                "max_age_hours": {
                    "type": "number",
                    "description": "有效期限（小时）",
                    "default": 72,
                },
            },
            "required": ["website"],
        },
    },
    {
        "name": "captcha_session_list",
        "description": "列出所有已保存的 session",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ---------------------------------------------------------------------------
# 工具执行
# ---------------------------------------------------------------------------

def call_tool(name: str, arguments: dict) -> list[dict]:
    """执行工具，返回 MCP content 列表"""
    if name == "captcha_solve":
        result = solver.solve(
            image=arguments["image"],
            website=arguments.get("website", ""),
            enable_vision=arguments.get("enable_vision", True),
            vision_provider=arguments.get("vision_provider", "openai"),
        )
    elif name == "captcha_detect":
        user_input = arguments["input"]
        source = arguments.get("source", "description")
        t = detector.detect_from_html(user_input) if source == "html" else detector.detect_from_keywords(user_input)
        result = {"captcha_type": t.value, "strategy": detector.solve_strategy(t)}
    elif name == "captcha_session_check":
        result = session.check(arguments["website"], arguments.get("max_age_hours", 72))
    elif name == "captcha_session_save":
        cookies = json.loads(arguments["cookies"])
        path = session.save(arguments["website"], cookies)
        result = {"success": True, "website": arguments["website"], "cookie_count": len(cookies), "saved_to": str(path)}
    elif name == "captcha_session_load":
        cookies = session.load(arguments["website"], arguments.get("max_age_hours", 72))
        if cookies is None:
            result = {"success": False, "error": "session 不存在或已过期"}
        else:
            result = {"success": True, "website": arguments["website"], "cookie_count": len(cookies), "cookies": cookies}
    elif name == "captcha_session_list":
        result = {"sessions": session.list_all(), "count": len(session.list_all())}
    else:
        result = {"error": f"未知工具: {name}"}

    return [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]


# ---------------------------------------------------------------------------
# MCP JSON-RPC (stdlib only, no mcp package needed)
# ---------------------------------------------------------------------------

class MCPServer:
    """最小 MCP JSON-RPC 2.0 实现，通过 stdio 通信"""

    def __init__(self, name: str = "hermes-captcha-solver"):
        self.name = name
        self.version = "0.1.0"
        self._handlers = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_list_tools,
            "tools/call": self._handle_call_tool,
            "ping": self._handle_ping,
        }

    def run(self):
        """主循环：读 stdin → 处理 → 写 stdout"""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue
            response = self._dispatch(request)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()

    def _dispatch(self, request: dict):  # -> dict | None
        """分发 JSON-RPC 请求"""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        handler = self._handlers.get(method)
        if handler is None:
            return self._error(req_id, -32601, f"Method not found: {method}")

        try:
            result = handler(params)
            if req_id is None:
                return None  # notification, no response
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:
            return self._error(req_id, -32000, str(e))

    def _handle_initialize(self, params: dict) -> dict:
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": self.name, "version": self.version},
            "capabilities": {"tools": {}},
        }

    def _handle_list_tools(self, params: dict) -> dict:
        return {"tools": TOOLS}

    def _handle_call_tool(self, params: dict) -> dict:
        name = params["name"]
        arguments = params.get("arguments", {})
        content = call_tool(name, arguments)
        return {"content": content}

    def _handle_ping(self, params: dict) -> dict:
        return {}

    def _error(self, req_id, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# HTTP 模式（兼容不支持 MCP 的客户端）
# ---------------------------------------------------------------------------

def run_http(host: str = "127.0.0.1", port: int = 9527):
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/tools/call":
                self.send_error(404); return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body)
                result = call_tool(payload["name"], payload.get("arguments", {}))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"result": result}, ensure_ascii=False).encode())
            except Exception as e:
                self.send_response(400); self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        def do_GET(self):
            if self.path == "/health":
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            elif self.path == "/tools":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(TOOLS, ensure_ascii=False).encode())
            else:
                self.send_error(404)

        def log_message(self, format, *args):
            pass

    server = HTTPServer((host, port), Handler)
    print(f"hermes-captcha-solver HTTP → http://{host}:{port}", file=sys.stderr)
    print(f"  GET  /tools    - 工具列表", file=sys.stderr)
    print(f"  POST /tools/call - 调用工具", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if "--http" in sys.argv:
        import argparse
        p = argparse.ArgumentParser(description="hermes-captcha-solver")
        p.add_argument("--http", action="store_true")
        p.add_argument("--host", default="127.0.0.1")
        p.add_argument("--port", type=int, default=9527)
        args = p.parse_args()
        run_http(args.host, args.port)
    else:
        MCPServer().run()


if __name__ == "__main__":
    main()
