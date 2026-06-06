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
HELP_TEXT = (
    "我可以直接理解自然语言，也保留这些命令：\n"
    "/pending 查看待确认归档\n"
    "/search 关键词 搜索 Obsidian CRM\n"
    "/ask 问题 用知识库上下文回答\n"
    "/archive 联系人姓名 确认归档对象\n"
    "/new 姓名 公司 Title 新建联系人候选\n"
    "/skip 跳过当前待确认项\n\n"
    "你也可以直接说：这个联系人叫 Alex Chen，归到 Alex Chen，新建 Alex Chen Northstar Advisor。"
)


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


def send_text_to_chat(chat_id, text):
    tenant_token = get_tenant_access_token()
    url = f"{FEISHU_BASE}/im/v1/messages?{urlencode({'receive_id_type': 'chat_id'})}"
    data = request_json("POST", url, headers={"Authorization": f"Bearer {tenant_token}"}, payload={
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    })
    if data.get("code") != 0:
        raise RuntimeError(f"Failed to send chat message: {data}")
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


def system_path(filename):
    system_dir = vault_path() / ".crm-system"
    system_dir.mkdir(parents=True, exist_ok=True)
    return system_dir / filename


def state_path():
    return system_path("bot-session-state.json")


def load_state():
    path = state_path()
    if not path.exists():
        return {"pending_by_sender": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"pending_by_sender": {}}
    state.setdefault("pending_by_sender", {})
    return state


def save_state(state):
    state_path().write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def set_pending_confirmation(sender_open_id, recording_title, source="card"):
    if not sender_open_id:
        return
    state = load_state()
    state.setdefault("pending_by_sender", {})[sender_open_id] = {
        "recording_title": recording_title or "",
        "source": source,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_state(state)


def get_pending_confirmation(sender_open_id):
    return load_state().get("pending_by_sender", {}).get(sender_open_id or "", {})


def clear_pending_confirmation(sender_open_id):
    if not sender_open_id:
        return
    state = load_state()
    pending = state.setdefault("pending_by_sender", {})
    if sender_open_id in pending:
        del pending[sender_open_id]
        save_state(state)


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


def clean_contact_target(raw):
    text = (raw or "").strip()
    text = re.sub(r"^[：:，,。.\s]+", "", text)
    text = re.sub(r"[。.!！?？；;\s]+$", "", text)
    text = re.sub(r"^(联系人|名字|姓名|对象|人)\s*(是|叫|为)?\s*", "", text)
    return text.strip(" '\"“”‘’")


def looks_like_contact_name(text):
    text = clean_contact_target(text)
    if not text or len(text) > 60:
        return False
    if any(token in text.lower() for token in ("http", "www", "/ask", "/search")):
        return False
    if re.search(r"[?？]", text):
        return False
    return bool(re.fullmatch(r"[\w\u3400-\u9fff .·・\-（）()&]+", text))


def parse_natural_confirmation(text, has_pending):
    stripped = text.strip()
    lowered = stripped.lower()
    if not stripped:
        return None
    if any(word in lowered for word in ("skip", "ignore")) or any(word in stripped for word in ("跳过", "先不处理", "不归档")):
        return {"command": "skip"}

    new_patterns = [
        r"(?:新建|创建|新增)(?:联系人)?\s*[:：]?\s*(.+)",
        r"(.+?)\s*(?:是|作为)\s*新联系人",
    ]
    for pattern in new_patterns:
        match = re.search(pattern, stripped, flags=re.I)
        if match:
            target = clean_contact_target(match.group(1))
            if target:
                return {"command": "new", "args": target}

    archive_patterns = [
        r"(?:归档到|归到|挂到|记到|放到|更新到)\s*[:：]?\s*(.+)",
        r"(?:这个(?:新的)?联系人(?:叫|是)?|联系人(?:叫|是)|名字(?:叫|是)|姓名(?:叫|是))\s*[:：]?\s*(.+)",
        r"(?:这个(?:call|会议|录音|note|记录)?(?:应该)?是|应该是|就是|是)\s*[:：]?\s*(.+)",
    ]
    for pattern in archive_patterns:
        match = re.search(pattern, stripped, flags=re.I)
        if match:
            target = clean_contact_target(match.group(1))
            if target:
                return {"command": "archive", "target": target}

    if has_pending and looks_like_contact_name(stripped):
        return {"command": "archive", "target": clean_contact_target(stripped)}
    return None


def looks_like_knowledge_query(text):
    stripped = text.strip()
    lowered = stripped.lower()
    if not stripped:
        return False
    if re.search(r"[?？]", stripped):
        return True
    query_markers = (
        "帮我找",
        "找一下",
        "搜一下",
        "查一下",
        "查找",
        "有没有",
        "之前",
        "上一次",
        "上一轮",
        "估值",
        "谁是",
        "是什么",
        "记得",
        "回忆一下",
    )
    return any(marker in stripped for marker in query_markers) or lowered.startswith(("search ", "find "))


def process_knowledge_query(text):
    context = search_vault(text, limit=12)
    answer = optional_llm_answer(text, context)
    return answer or context


def record_archive(sender_open_id, target, recording_title=""):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    recording_line = f"\n- recording: {recording_title}" if recording_title else ""
    append_log(
        "confirmation-log.md",
        f"## {now}\n\n- sender: {sender_open_id}\n- command: /archive\n- target: {target}{recording_line}",
    )
    clear_pending_confirmation(sender_open_id)
    return f"已记录确认：归档到「{target}」。下一次 housekeeping 会据此更新 CRM。"


def record_new_contact(sender_open_id, args, recording_title=""):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    recording_line = f"\n- recording: {recording_title}" if recording_title else ""
    append_log(
        "confirmation-log.md",
        f"## {now}\n\n- sender: {sender_open_id}\n- command: /new\n- args: {args}{recording_line}",
    )
    clear_pending_confirmation(sender_open_id)
    return f"已记录新联系人候选：{args}。下一次 housekeeping 会创建或请你补充信息。"


def record_skip(sender_open_id, recording_title=""):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    recording_line = f"\n- recording: {recording_title}" if recording_title else ""
    append_log("confirmation-log.md", f"## {now}\n\n- sender: {sender_open_id}\n- command: /skip{recording_line}")
    clear_pending_confirmation(sender_open_id)
    return "已记录跳过当前待确认项。"


def process_natural_language(sender_open_id, text):
    pending = get_pending_confirmation(sender_open_id)
    intent = parse_natural_confirmation(text, bool(pending))
    if intent:
        recording_title = pending.get("recording_title", "")
        command = intent.get("command")
        if command == "archive":
            if not pending:
                target = intent.get("target", "")
                return f"我理解你想归档到「{target}」，但当前没有待确认录音上下文。请先点对应卡片的「手动输入」，或回复 /pending 看待确认项。"
            return record_archive(sender_open_id, intent.get("target", ""), recording_title)
        if command == "new":
            return record_new_contact(sender_open_id, intent.get("args", ""), recording_title)
        if command == "skip":
            if not pending:
                return "当前没有待确认录音上下文。请回复 /pending 查看待确认项。"
            return record_skip(sender_open_id, recording_title)
    if looks_like_knowledge_query(text):
        return process_knowledge_query(text)
    return ""


def process_command(sender_open_id, text):
    text = text.strip()
    lowered = text.lower()
    if lowered in ("/help", "help", "帮助"):
        return HELP_TEXT
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
        pending = get_pending_confirmation(sender_open_id)
        return record_archive(sender_open_id, target, pending.get("recording_title", ""))
    if lowered.startswith("/new"):
        args = text[len("/new"):].strip()
        if not args:
            return "请使用：/new 姓名 公司 Title"
        pending = get_pending_confirmation(sender_open_id)
        return record_new_contact(sender_open_id, args, pending.get("recording_title", ""))
    if lowered.startswith("/skip"):
        pending = get_pending_confirmation(sender_open_id)
        return record_skip(sender_open_id, pending.get("recording_title", ""))
    natural_reply = process_natural_language(sender_open_id, text)
    if natural_reply:
        return natural_reply
    return "我收到了。你可以直接说“归到 Alex Chen”“这个联系人叫 Alex Chen”，也可以回复 /help 查看命令。"


def process_card_action(operator_open_id, value):
    command = (value or {}).get("command", "")
    recording_title = (value or {}).get("recording_title", "")
    if command == "archive":
        target = (value or {}).get("target", "")
        record_archive(operator_open_id, target, recording_title)
        return {"toast": {"type": "success", "content": f"已记录归档到：{target}"}}
    if command == "manual_input":
        set_pending_confirmation(operator_open_id, recording_title)
        if operator_open_id:
            send_text(operator_open_id, "直接回复联系人即可，例如：Alex Chen\n也可以说：这个联系人叫 Alex Chen，或：新建 Alex Chen Northstar Advisor")
        return {"toast": {"type": "info", "content": "请在聊天里输入联系人"}}
    if command == "skip":
        record_skip(operator_open_id, recording_title)
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


def run_websocket_agent():
    try:
        import lark_oapi as lark
        from lark_oapi.api.im.v1 import P2ImMessageReceiveV1
        from lark_oapi.event.callback.model.p2_card_action_trigger import (
            P2CardActionTrigger,
            P2CardActionTriggerResponse,
        )
    except ImportError as exc:
        raise RuntimeError("Install dependency first: python3 -m pip install lark-oapi") from exc

    app_id, app_secret = require_creds()
    verification_token = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")
    encrypt_key = os.environ.get("FEISHU_ENCRYPT_KEY", "")

    def on_message(data: P2ImMessageReceiveV1) -> None:
        event = data.event
        if not event or not event.sender or not event.message:
            return
        sender_id = event.sender.sender_id
        open_id = getattr(sender_id, "open_id", "") if sender_id else ""
        chat_id = event.message.chat_id or ""
        text = extract_message_text({"message": {"content": event.message.content or ""}})
        append_log(
            "feishu-bot-events.md",
            f"## {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n- transport: websocket\n- sender: {open_id}\n- chat_id: {chat_id}\n- text: {text}",
        )
        reply = process_command(open_id, text)
        if chat_id:
            send_text_to_chat(chat_id, reply)
        elif open_id:
            send_text(open_id, reply)

    def on_card_action(data: P2CardActionTrigger) -> P2CardActionTriggerResponse:
        event = data.event
        operator_open_id = ""
        value = {}
        if event:
            if event.operator:
                operator_open_id = event.operator.open_id or ""
            if event.action and isinstance(event.action.value, dict):
                value = event.action.value
        append_log(
            "feishu-bot-events.md",
            f"## {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n- transport: websocket\n- sender: {operator_open_id}\n- card_action: {json.dumps(value, ensure_ascii=False)}",
        )
        response = process_card_action(operator_open_id, value)
        return P2CardActionTriggerResponse(response)

    def on_message_read(data) -> None:
        return None

    handler = (
        lark.EventDispatcherHandler.builder(encrypt_key, verification_token, lark.LogLevel.INFO)
        .register_p2_im_message_receive_v1(on_message)
        .register_p2_im_message_message_read_v1(on_message_read)
        .register_p2_card_action_trigger(on_card_action)
        .build()
    )
    print(json.dumps({
        "ok": True,
        "transport": "websocket",
        "message": "Connected through Feishu long connection. Keep this process running.",
        "vault": str(vault_path()),
    }, ensure_ascii=False, indent=2))
    lark.ws.Client(app_id, app_secret, event_handler=handler, log_level=lark.LogLevel.INFO).start()
    while True:
        time.sleep(3600)


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
    parser.add_argument("--transport", choices=["http", "websocket"], default="http")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9788)
    args = parser.parse_args()
    if args.transport == "websocket":
        run_websocket_agent()
        return
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
