# Feishu Bot Agent

## Objective

Turn the Feishu bot into the confirmation and query interface for Personal CRM.

The bot should:

- receive low-confidence archive confirmations;
- receive interactive card button callbacks;
- search the local Obsidian CRM vault;
- answer knowledge-base questions with retrieved context;
- record user decisions for the next housekeeping run;
- avoid updating contacts or merging contacts without explicit confirmation.

## Current Local Backend

Run:

```bash
PERSONAL_CRM_VAULT="/Users/tedliu/Documents/Obsidian/Personal CRM" \
FEISHU_APP_ID="<app_id>" \
FEISHU_APP_SECRET="<app_secret>" \
python3 scripts/feishu_bot_agent.py --host 127.0.0.1 --port 9788
```

Health check:

```bash
curl http://127.0.0.1:9788/health
```

Feishu event path:

```text
/feishu/events
```

Because Feishu cannot call `127.0.0.1`, expose it with a tunnel for real message receiving:

```bash
ngrok http 9788
```

Then configure Feishu event subscription URL:

```text
https://<ngrok-domain>/feishu/events
```

## Feishu App Requirements

Enable:

- bot capability;
- event subscription;
- receive message event: `im.message.receive_v1`;
- card action callback: `card.action.trigger`;
- send message permission: `im:message:send_as_bot`;
- app credentials in local `.env` or environment variables.

If Feishu provides a verification token, set:

```text
FEISHU_VERIFICATION_TOKEN=<token>
```

## Commands

```text
/pending
/search 关键词
/ask 问题
/archive 联系人姓名
/new 姓名 公司 Title
/skip
```

## Interactive Cards

Use cards for low-confidence archive prompts. The card keeps the message short and gives buttons for likely candidates.

Send a test card:

```bash
FEISHU_APP_ID="<app_id>" \
FEISHU_APP_SECRET="<app_secret>" \
python3 skills-src/personal-feishu-minutes-reader/scripts/feishu_minutes_reader.py \
  --action send_confirmation_card \
  --recording-title "2026-06-04_Unknown_日本泰澳投资布局" \
  --recorded-at "2026-06-04 12:51" \
  --reason "联系人置信度不足，需要确认归档对象。" \
  --candidates-json '[{"name":"Alex Chen","company":"Northstar Capital","score":72}]'
```

Card buttons:

- candidate button: records `/archive <name>`;
- `手动输入`: asks the user to reply `/archive 联系人姓名` or `/new 姓名 公司 Title`;
- `跳过`: records `/skip`.

## LLM Layer

The bot can answer from the Obsidian knowledge base in two modes:

- retrieval-only mode: search vault files and return matching notes;
- model mode: set `OPENAI_API_KEY`; the backend retrieves context and asks the model to answer from that context.

Optional model env:

```text
CRM_AGENT_MODEL=gpt-4.1-mini
```

If no model key is configured, `/ask` safely falls back to local knowledge-base search.

## Low-Confidence Archive Flow

```text
housekeeping finds uncertain transcript
  -> write pending-confirmations.md
  -> send Feishu message
  -> user replies /archive, /new, or /skip
  -> bot records confirmation-log.md
  -> next housekeeping applies the decision
```

The bot should not directly merge contacts. Merge requests must be written as proposals under:

```text
.crm-system/merge-proposals/
```
