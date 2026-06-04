---
name: wechat-contact-reader
description: Ingest local WeChat contact/session exports into the personal CRM pipeline. Use when asked to read WeChat contacts, map WeChat aliases to CRM contacts, create contact candidates from WeChat, or evaluate local WeChat export tools such as wechat-cli. This skill is read-only and must not send messages or modify WeChat.
---

# WeChat Contact Reader

Use this skill to bring WeChat contact context into CRM matching.

## Preferred Tool

Prefer `wechat-cli` for MVP:

```text
https://github.com/huohuoer/wechat-cli
```

Reasons:

- local-first;
- command-line workflow;
- JSON output;
- suitable for AI agents;
- can export contacts, sessions, history, and files.

## Avoid by Default

Avoid live WeChat automation or hook frameworks for MVP, including WeChatFerry-style approaches, unless the user explicitly accepts the risk.

## Data Scope

Read only:

- contacts;
- remarks/aliases;
- session titles;
- phone/email when exported;
- recent session metadata.

Do not:

- send messages;
- modify contacts;
- upload chat history;
- write exported WeChat data to GitHub.

## Local Storage

Store exports under:

```text
.crm-system/wechat/
```

Treat all WeChat-derived data as:

```yaml
sensitivity: confidential
```

## Handoff

Pass contact candidates to `contact-builder`.

Candidate schema:

```json
{
  "source": "wechat",
  "display_name": "",
  "remark_name": "",
  "alias": "",
  "phone": "",
  "company_guess": "",
  "recent_session_titles": [],
  "confidence": "high|medium|low"
}
```

