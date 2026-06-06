#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FEISHU_BASE = "https://open.feishu.cn/open-apis"
DEFAULT_VAULT = "/Users/tedliu/Documents/Obsidian/Personal CRM"


def load_local_env():
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()


def request_json(method, url, headers=None, payload=None):
    body = None
    headers = dict(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers.setdefault("Content-Type", "application/json; charset=utf-8")
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(details)
        except json.JSONDecodeError:
            pass
        raise RuntimeError(json.dumps({
            "error": "http_error",
            "status": exc.code,
            "details": details,
        }, ensure_ascii=False))


def require_creds():
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        raise RuntimeError("Set FEISHU_APP_ID and FEISHU_APP_SECRET.")
    return app_id, app_secret


def get_tenant_access_token():
    app_id, app_secret = require_creds()
    data = request_json("POST", f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal", payload={
        "app_id": app_id,
        "app_secret": app_secret,
    })
    if data.get("code") != 0:
        raise RuntimeError(f"Failed to get tenant_access_token: {data}")
    return data["tenant_access_token"]


def send_text(open_id, text):
    tenant_token = get_tenant_access_token()
    url = f"{FEISHU_BASE}/im/v1/messages?{urlencode({'receive_id_type': 'open_id'})}"
    data = request_json("POST", url, headers={"Authorization": f"Bearer {tenant_token}"}, payload={
        "receive_id": open_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    })
    if data.get("code") != 0:
        raise RuntimeError(f"Failed to send message: {data}")
    return data


def vault_path():
    return Path(os.environ.get("PERSONAL_CRM_VAULT", DEFAULT_VAULT)).expanduser()


def append_log(filename, body):
    system_dir = vault_path() / ".crm-system"
    system_dir.mkdir(parents=True, exist_ok=True)
    path = system_dir / filename
    if not path.exists():
        title = filename.replace(".md", "").replace("-", " ").title()
        path.write_text(f"# {title}\n\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as f:
        f.write(body.rstrip() + "\n\n")
    return path


def read_pending():
    path = vault_path() / ".crm-system" / "pending-confirmations.md"
    if not path.exists():
        return "当前没有 pending confirmations 文件。"
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) > 1800:
        text = text[:1800] + "\n\n...[truncated]"
    return text or "当前没有待确认事项。"


def search_vault(query, limit=8):
    query = query.strip()
    if not query:
        return "请在 /search 后面加关键词。"
    cmd = ["rg", "-n", "--no-heading", "-i", query, str(vault_path())]
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=20)
    if result.returncode not in (0, 1):
        return f"搜索失败：{result.stderr.strip()}"
    lines = result.stdout.splitlines()[:limit]
    if not lines:
        return f"没有搜到：{query}"
    compact = []
    for line in lines:
        path, _, rest = line.partition(":")
        rel = str(Path(path).relative_to(vault_path())) if path.startswith(str(vault_path())) else path
        compact.append(f"- {rel}:{rest[:220]}")
    return "知识库搜索结果：\n" + "\n".join(compact)


def optional_llm_answer(question, context):
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return ""
    model = os.environ.get("CRM_AGENT_MODEL", "gpt-4.1-mini")
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": "You are a local personal CRM assistant. Answer using only the provided Obsidian CRM context. If uncertain, say what is missing.",
            },
            {
                "role": "user",
                "content": f"Question:\n{question}\n\nContext:\n{context}",
            },
        ],
    }
    req = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return f"LLM 调用失败，已退回知识库搜索结果：{exc}"
    parts = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(part for part in parts if part).strip()


def process_command(sender_open_id, text):
    text = text.strip()
    lowered = text.lower()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    if lowered in ("/help", "help", "帮助"):
        return (
            "Personal CRM bot commands:\n"
            "/pending 查看待确认归档\n"
            "/search 关键词 搜索 Obsidian CRM\n"
            "/ask 问题 用知识库上下文回答\n"
            "/archive 联系人姓名 确认归档对象\n"
            "/new 姓名 公司 Title 新建联系人候选\n"
            "/skip 跳过当前待确认项"
        )
    if lowered.startswith("/pending"):
        return read_pending()
    if lowered.startswith("/search"):
        return search_vault(text[len("/search"):])
    if lowered.startswith("/ask"):
        question = text[len("/ask"):].strip()
        context = search_vault(question, limit=12)
        answer = optional_llm_answer(question, context)
        return answer or context
    if lowered.startswith("/archive"):
        target = text[len("/archive"):].strip()
        if not target:
            return "请使用：/archive 联系人姓名"
        append_log("confirmation-log.md", f"## {now}\n\n- sender: {sender_open_id}\n- command: /archive\n- target: {target}")
        return f"已记录确认：归档到「{target}」。下一次 housekeeping 会据此更新 CRM。"
    if lowered.startswith("/new"):
        args = text[len("/new"):].strip()
        if not args:
            return "请使用：/new 姓名 公司 Title"
        append_log("confirmation-log.md", f"## {now}\n\n- sender: {sender_open_id}\n- command: /new\n- args: {args}")
        return f"已记录新联系人候选：{args}。下一次 housekeeping 会创建或请你补充信息。"
    if lowered.startswith("/skip"):
        append_log("confirmation-log.md", f"## {now}\n\n- sender: {sender_open_id}\n- command: /skip")
        return "已记录跳过当前待确认项。"
    return "我收到了。可以回复 /help 查看命令，或用 /ask 问我知识库里的内容。"


def process_card_action(operator_open_id, value):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    command = (value or {}).get("command", "")
    recording_title = (value or {}).get("recording_title", "")
    if command == "archive":
        target = (value or {}).get("target", "")
        append_log(
            "confirmation-log.md",
            f"## {now}\n\n- sender: {operator_open_id}\n- command: /archive\n- target: {target}\n- recording: {recording_title}",
        )
        return {"toast": {"type": "success", "content": f"已记录归档到：{target}"}}
    if command == "manual_input":
        if operator_open_id:
            send_text(operator_open_id, "请回复：/archive 联系人姓名\n或：/new 姓名 公司 Title")
        return {"toast": {"type": "info", "content": "请在聊天里输入联系人"}}
    if command == "skip":
        append_log(
            "confirmation-log.md",
            f"## {now}\n\n- sender: {operator_open_id}\n- command: /skip\n- recording: {recording_title}",
        )
        return {"toast": {"type": "success", "content": "已记录跳过"}}
    return {"toast": {"type": "warning", "content": "未识别的操作"}}


def extract_message_text(event):
    message = event.get("message", {})
    content = message.get("content", "")
    try:
        parsed = json.loads(content)
        return parsed.get("text", "")
    except json.JSONDecodeError:
        return content


def extract_sender_open_id(event):
    sender = event.get("sender", {})
    return sender.get("sender_id", {}).get("open_id", "")


def extract_card_operator_open_id(event):
    operator = event.get("operator", {})
    if operator.get("open_id"):
        return operator.get("open_id", "")
    return operator.get("operator_id", {}).get("open_id", "")


def extract_card_action_value(event):
    action = event.get("action", {})
    value = action.get("value", {})
    return value if isinstance(value, dict) else {}


class FeishuHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"ok": True, "vault": str(vault_path())})
            return
        self._send_json({"error": "not_found"}, status=404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self._send_json({"error": "invalid_json"}, status=400)
            return

        if "challenge" in payload:
            self._send_json({"challenge": payload["challenge"]})
            return

        expected_token = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")
        if expected_token and payload.get("token") and payload.get("token") != expected_token:
            self._send_json({"error": "invalid_token"}, status=403)
            return

        header = payload.get("header", {})
        event = payload.get("event", {})
        event_type = header.get("event_type", payload.get("type", ""))
        if event_type in ("card.action.trigger", "card.action.trigger_v1"):
            operator_open_id = extract_card_operator_open_id(event)
            value = extract_card_action_value(event)
            append_log(
                "feishu-bot-events.md",
                f"## {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n- sender: {operator_open_id}\n- card_action: {json.dumps(value, ensure_ascii=False)}",
            )
            self._send_json(process_card_action(operator_open_id, value))
            return
        if event_type != "im.message.receive_v1":
            self._send_json({"ok": True, "ignored": event_type})
            return

        sender_open_id = extract_sender_open_id(event)
        text = extract_message_text(event)
        append_log("feishu-bot-events.md", f"## {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n- sender: {sender_open_id}\n- text: {text}")
        if sender_open_id:
            reply = process_command(sender_open_id, text)
            send_text(sender_open_id, reply)
        self._send_json({"ok": True})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9788)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), FeishuHandler)
    print(json.dumps({
        "ok": True,
        "listening": f"http://{args.host}:{args.port}",
        "event_path": "/feishu/events",
        "health": "/health",
        "vault": str(vault_path()),
    }, ensure_ascii=False, indent=2))
    server.serve_forever()


if __name__ == "__main__":
    main()
