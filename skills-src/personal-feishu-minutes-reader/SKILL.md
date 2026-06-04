---
name: personal-feishu-minutes-reader
description: Read Feishu/Lark Minutes and user-visible Feishu notes through personal user OAuth for a personal Obsidian CRM workflow. Use when asked to authorize Feishu, fetch a Feishu Minutes transcript, read a Feishu Minutes link, or provide Feishu meeting data for CRM archiving.
---

# Personal Feishu Minutes Reader

Use user OAuth, not a tenant bot, unless the user explicitly provides enterprise app credentials and admin approval.

## Setup

The script expects:

```text
FEISHU_APP_ID
FEISHU_APP_SECRET
```

Check auth:

```bash
python <skill_path>/scripts/feishu_minutes_reader.py --action auth_status
```

Generate OAuth URL:

```bash
python <skill_path>/scripts/feishu_minutes_reader.py --action oauth_url
```

Exchange code:

```bash
python <skill_path>/scripts/feishu_minutes_reader.py --action exchange_code --auth-code "<code>"
```

## Read Minutes

```bash
python <skill_path>/scripts/feishu_minutes_reader.py \
  --action read_minute_transcript \
  --minute-token "<minute_token_or_url>"
```

## Fallback

If the API returns permission errors:

1. Keep the Feishu link as `source_link`.
2. Ask the user to export/copy transcript.
3. Pass transcript to `personal-obsidian-crm-archiver`.

Do not block CRM archiving on Feishu API automation.

