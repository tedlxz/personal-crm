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


def safe_filename_person(name):
    cleaned = clean_contact_target(name)
    cleaned = re.sub(r"[\\/:*?\"<>|#^[\\]]+", "", cleaned)
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    return cleaned or "Unknown"


def split_recording_title(recording_title):
    parts = (recording_title or "").split("_", 2)
    if len(parts) != 3:
        return "", "", ""
    return parts[0], parts[1], parts[2]


def find_meeting_note(recording_title):
    date, _person, topic = split_recording_title(recording_title)
    year = date[:4] if date else time.strftime("%Y")
    meetings_dir = vault_path() / "20_Meetings" / year
    exact = meetings_dir / f"{recording_title}.md"
    if exact.exists():
        return exact
    if topic and meetings_dir.exists():
        matches = sorted(meetings_dir.glob(f"*_{topic}.md"))
        if matches:
            return matches[0]
    return None


def update_meeting_note_for_contact(note_path, target):
    old_stem = note_path.stem
    date, _old_person, topic = split_recording_title(old_stem)
    if not date or not topic:
        return note_path, old_stem
    new_stem = f"{date}_{safe_filename_person(target)}_{topic}"
    new_path = note_path.with_name(f"{new_stem}.md")
    text = note_path.read_text(encoding="utf-8")
    text = text.replace(old_stem, new_stem)
    text = re.sub(r'^title: ".*"$', f'title: "{date} {target} {topic}"', text, flags=re.M)
    text = re.sub(r'^participants: .*$',
                  f'participants: ["{target}"]', text, flags=re.M)
    text = re.sub(r'^primary_people: .*$',
                  f'primary_people: ["{target}"]', text, flags=re.M)
    text = re.sub(r'^contacts: .*$',
                  f'contacts: ["[[{target}]]"]', text, flags=re.M)
    text = re.sub(r'^match_confidence: .*$',
                  'match_confidence: "confirmed_by_user"', text, flags=re.M)
    text = re.sub(r'^crm_updated: .*$',
                  'crm_updated: true', text, flags=re.M)
    text = re.sub(r'^tags: .*$',
                  'tags: [meeting, viaim, crm-updated]', text, flags=re.M)
    if "confirmed_by:" not in text:
        text = text.replace('match_confidence: "confirmed_by_user"\n',
                            'match_confidence: "confirmed_by_user"\nconfirmed_by: "feishu_bot"\n')
    if "confirmed_at:" not in text:
        text = text.replace('confirmed_by: "feishu_bot"\n',
                            f'confirmed_by: "feishu_bot"\nconfirmed_at: "{date}"\n')
    text = text.replace("参与人：Unknown，转写未提供清晰姓名", f"参与人：{target}，经飞书 bot 确认归档")
    text = text.replace("关联联系人：待确认", f"关联联系人：[[{target}]]")
    text = text.replace("匹配置信度：needs_user_confirmation", "匹配置信度：confirmed_by_user")
    text = text.replace("当前不能自动更新联系人，因为 transcript 没有可确认的人名。", f"已更新到 [[{target}]] 的 `对话记录更新`。")
    text = text.replace("待用户确认主联系人后，应把本次互动追加到该联系人 `对话记录更新`。\n", "")
    if note_path != new_path and new_path.exists():
        new_path.write_text(text, encoding="utf-8")
        note_path.unlink()
    else:
        note_path.write_text(text, encoding="utf-8")
        if note_path != new_path:
            note_path.rename(new_path)
    return new_path, new_stem


def ensure_contact_for_archive(target, meeting_stem, topic):
    contacts_dir = vault_path() / "10_CRM" / "Contacts"
    contacts_dir.mkdir(parents=True, exist_ok=True)
    contact_path = contacts_dir / f"{target}.md"
    row = (
        f"| {meeting_stem[:10]} | Feishu bot confirmed archive | [[{meeting_stem}]] | "
        f"已确认该会议归档到 {target}；主题：{topic} | 补充 title、公司、联系方式；确认是否需要合并同名/近似联系人 |"
    )
    if contact_path.exists():
        text = contact_path.read_text(encoding="utf-8")
        if f"[[{meeting_stem}]]" not in text:
            if "| --- | --- | --- | --- | --- |" in text:
                text = text.replace("| --- | --- | --- | --- | --- |\n", f"| --- | --- | --- | --- | --- |\n{row}\n", 1)
            else:
                text += f"\n\n## 对话记录更新\n\n| 日期 | 场景 | 会议/对话 | 核心内容 | 后续动作 |\n| --- | --- | --- | --- | --- |\n{row}\n"
        text = re.sub(r'^last_contact_date: ".*"$', f'last_contact_date: "{meeting_stem[:10]}"', text, flags=re.M)
        contact_path.write_text(text, encoding="utf-8")
        return contact_path
    text = f"""---
type: crm_contact
name: "{target}"
title: ""
company: ""
company_file: ""
status: active
relationship_strength: unknown
first_met_date: "{meeting_stem[:10]}"
first_met_place: ""
introduced_by: ""
last_contact_date: "{meeting_stem[:10]}"
next_follow_up_date: ""
sensitivity: confidential
tags: [crm, needs-confirmation]
---

# {target}

## 基础信息

- 姓名：{target}
- Title：待确认
- 公司：待确认
- 公司简介：
- 所在城市/地区：
- 联系方式：
- 主要标签：{topic}

## 建立联系的背景

- 何时建立联系：{meeting_stem[:10]}
- 何地建立联系：待确认
- 通过谁认识：待确认
- 当时场景：{topic}
- 初始印象：
- 对方认识的人：
- 与使用者/团队的关系：待确认

## 公司与角色

- 公司名称：待确认
- 公司做什么：
- 对方在公司的角色：待确认
- 对方负责的业务/资源：
- 公司与使用者关注领域的关系：

## 关系网络

- 介绍人：
- 共同认识的人：
- 可能影响的人：
- 对方重视的关系：

## 当前画像

- 关注点：待从后续会议中补充
- 需求/痛点：
- 能提供的资源：
- 可能合作方向：
- 沟通偏好：
- 注意事项：由飞书 bot 低置信度归档确认创建，身份细节待补充。

## 对话记录更新

| 日期 | 场景 | 会议/对话 | 核心内容 | 后续动作 |
| --- | --- | --- | --- | --- |
{row}

## 待办与跟进

- [ ] 确认 {target} 的 title、公司和联系方式。
- [ ] 检查是否需要与已有相似联系人合并。

## 关键洞察

-

## 相关链接

- 公司：
- 相关会议：[[{meeting_stem}]]
- 相关项目：{topic}
- 相关 insight：
"""
    contact_path.write_text(text, encoding="utf-8")
    return contact_path


def mark_pending_resolved(old_recording_title, new_meeting_stem, target):
    path = vault_path() / ".crm-system" / "pending-confirmations.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace(old_recording_title, new_meeting_stem)
    text = re.sub(r"- 状态：needs_user_confirmation", "- 状态：resolved", text)
    text = re.sub(r"- 原因：.*", f"- 确认结果：{target}", text)
    text = re.sub(
        r"- 请确认归档对象：\n(?:  - .*\n?)+",
        f"- 已处理：meeting note 已改名，CRM 联系人 [[{target}]] 已创建/更新并写入对话记录。\n",
        text,
    )
    path.write_text(text, encoding="utf-8")


def apply_archive_confirmation(recording_title, target):
    if not recording_title or not target:
        return {"applied": False, "reason": "missing_recording_or_target"}
    note_path = find_meeting_note(recording_title)
    if not note_path:
        return {"applied": False, "reason": "meeting_note_not_found", "recording": recording_title}
    new_path, new_stem = update_meeting_note_for_contact(note_path, target)
    _date, _person, topic = split_recording_title(new_stem)
    contact_path = ensure_contact_for_archive(target, new_stem, topic)
    mark_pending_resolved(recording_title, new_stem, target)
    return {
        "applied": True,
        "meeting_note": str(new_path.relative_to(vault_path())),
        "contact": str(contact_path.relative_to(vault_path())),
    }


def record_archive(sender_open_id, target, recording_title=""):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    apply_result = apply_archive_confirmation(recording_title, target) if recording_title else {"applied": False}
    recording_line = f"\n- recording: {recording_title}" if recording_title else ""
    apply_line = f"\n- applied: {json.dumps(apply_result, ensure_ascii=False)}"
    append_log(
        "confirmation-log.md",
        f"## {now}\n\n- sender: {sender_open_id}\n- command: /archive\n- target: {target}{recording_line}{apply_line}",
    )
    clear_pending_confirmation(sender_open_id)
    if apply_result.get("applied"):
        return f"已归档到「{target}」，meeting note 和联系人 CRM 已更新。"
    return f"已记录确认：归档到「{target}」。但还没找到可自动更新的 meeting note，下一次 housekeeping 会继续处理。"


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

    def on_bot_p2p_chat_entered(data) -> None:
        return None

    handler = (
        lark.EventDispatcherHandler.builder(encrypt_key, verification_token, lark.LogLevel.INFO)
        .register_p2_im_message_receive_v1(on_message)
        .register_p2_im_message_message_read_v1(on_message_read)
        .register_p2_im_chat_access_event_bot_p2p_chat_entered_v1(on_bot_p2p_chat_entered)
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
