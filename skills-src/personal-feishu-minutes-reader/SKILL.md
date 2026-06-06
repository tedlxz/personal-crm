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

Configure the Feishu custom app before OAuth:

```text
Redirect URL: http://localhost:9876/callback
Required scopes:
  minutes:minutes.search:read
  minutes:minutes:readonly
  minutes:minutes.transcript:export
  contact:user.base:readonly
  drive:drive:readonly
  docx:document
  search:docs:read
  calendar:calendar:readonly
```

Feishu permission changes require publishing the app version and may require tenant admin approval, even for a personal workflow. If scopes are added after a token was issued, run OAuth again and exchange a fresh code.

Check auth:

```bash
python3 <skill_path>/scripts/feishu_minutes_reader.py --action auth_status
```

Generate OAuth URL:

```bash
python3 <skill_path>/scripts/feishu_minutes_reader.py --action oauth_url
```

Exchange code:

```bash
python3 <skill_path>/scripts/feishu_minutes_reader.py --action exchange_code --auth-code "<code>"
```

The redirect target may fail to load because no local web server is running. Copy the `code` value from the browser address bar and exchange it immediately. The code is short-lived and single-use.

## Search Minutes

Prefer searching with a time range. Feishu may return no items for an empty search even when historical minutes exist.

```bash
python3 <skill_path>/scripts/feishu_minutes_reader.py \
  --action search_minutes \
  --page-size 10 \
  --start "2026-01-01T00:00:00+08:00" \
  --end "2026-12-31T23:59:59+08:00"
```

Use `raw.items[].token` as the `minute_token`. Preserve `raw.items[].meta_data.app_link` as `source_link`.

## Read Minute Transcript

```bash
python3 <skill_path>/scripts/feishu_minutes_reader.py \
  --action read_minute_transcript \
  --minute-token "<minute_token_or_url>"
```

The transcript endpoint returns `text/plain`. Pass `transcript_text` to `personal-obsidian-crm-archiver` or `crm-housekeeping-agent`.

## Fallback

If the API returns permission errors:

1. Keep the Feishu link as `source_link`.
2. If the error mentions `minutes:minutes.search:read`, ask the user to add/search-approve that scope and rerun OAuth.
3. Otherwise ask the user to export/copy transcript.
4. Pass transcript to `personal-obsidian-crm-archiver`.

Do not block CRM archiving on Feishu API automation.
