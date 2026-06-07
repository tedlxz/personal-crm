# Feishu Bot Agent

## Objective

Turn the Feishu bot into the confirmation and query interface for Personal CRM.

The bot should:

- receive low-confidence archive confirmations;
- receive interactive card button callbacks;
- search the local Obsidian CRM vault;
- answer knowledge-base questions with retrieved context;
- record user decisions for the next housekeeping run;
- understand short natural-language replies such as `这个联系人叫 Alex Chen` or `归到 Alex Chen`;
- avoid updating contacts or merging contacts without explicit confirmation.

## Role Of Lark CLI / CUI

`lark-cli` is the Feishu API/CUI toolbox. It is useful for:

- sending Feishu messages;
- reading Feishu resources such as Minutes, calendar, docs, and contacts;
- consuming regular message events such as `im.message.receive_v1`;
- debugging permissions and event schemas.

It does not replace the agent brain. The Personal CRM still needs a local agent layer to remember which low-confidence card is being discussed, translate natural language into structured CRM actions, write Obsidian logs, and decide when to call Codex/Claude for deeper work.

In practice:

```text
Feishu bot UI
  -> Feishu long connection / lark-cli tools
  -> local CRM agent router
  -> Obsidian vault + Codex/Claude + Feishu APIs
```

For natural-language knowledge-base questions through Lark CLI/CUI, use:

```bash
CODEX_WORKDIR="/Users/tedliu/Documents/Codex/2026-06-03/files-mentioned-by-the-user-june/outputs/Personal-CRM" \
PERSONAL_CRM_VAULT="/Users/tedliu/Documents/Obsidian/Personal CRM" \
LARK_CODEX_SANDBOX="workspace-write" \
LARK_CODEX_TIMEOUT_MS="300000" \
node scripts/lark_codex_bridge.mjs
```

This bridge runs:

```text
codex exec -C <Personal CRM repo> --add-dir <Obsidian vault>
```

The prompt tells Codex to search the Obsidian vault first, then use web search only when the vault does not contain enough evidence. Without `--add-dir`, Codex may answer from the temporary CUI workspace and miss local CRM notes.

## Current Local Agent

Preferred mode is Feishu long connection:

Run:

```bash
PERSONAL_CRM_VAULT="/Users/tedliu/Documents/Obsidian/Personal CRM" \
FEISHU_APP_ID="<app_id>" \
FEISHU_APP_SECRET="<app_secret>" \
python3 scripts/feishu_bot_agent.py --transport websocket
```

The process must remain running while the bot is expected to answer messages or card clicks.

For daily use on macOS, install it as a local `launchd` service:

```bash
FEISHU_APP_ID="<app_id>" \
FEISHU_APP_SECRET="<app_secret>" \
python3 scripts/install_feishu_bot_agent_launchd.py --load
```

This creates:

```text
~/Library/LaunchAgents/com.personalcrm.feishu-bot.plist
```

Logs are written to:

```text
~/Library/Logs/PersonalCRM/
```

macOS privacy note: if the repo or vault is under `~/Documents`, a LaunchAgent may fail with `Operation not permitted` unless the relevant terminal/Python runtime has Full Disk Access. If that happens, either grant Full Disk Access, run the agent from an interactive Codex/Terminal session, or move the agent/vault to a non-protected local folder.

HTTP webhook mode is kept as a fallback for deployments with a stable HTTPS callback URL:

```bash
python3 scripts/feishu_bot_agent.py --host 127.0.0.1 --port 9788
```

In long-connection mode, do not configure a tunnel URL. Configure Feishu:

```text
事件与回调 -> 事件配置 -> 使用长连接接收事件
事件与回调 -> 回调配置 -> 使用长连接接收回调
```

## Feishu App Requirements

Enable:

- bot capability;
- event subscription;
- receive message event: `im.message.receive_v1`;
- card action callback: `card.action.trigger`;
- send message permission: `im:message:send_as_bot`;
- app credentials in local `.env` or environment variables.

For long connection, both message events and card callbacks must use long connection.

`lark-cli` can verify message event consumption:

```bash
lark-cli event status --json
lark-cli event schema im.message.receive_v1 --json
```

Card button callbacks may not appear in `lark-cli event list`; the Python agent uses the Feishu SDK callback handler for `card.action.trigger`.

## Natural Language Replies

The bot keeps short-term state in:

```text
.crm-system/bot-session-state.json
```

When the user clicks `手动输入` on a card, the agent records which recording is awaiting confirmation. The next reply can be plain language:

```text
Alex Chen
这个联系人叫 Alex Chen
归到 Alex Chen
新建 Alex Chen Northstar Advisor
跳过
```

The agent writes the structured result to:

```text
.crm-system/confirmation-log.md
```

The agent should also apply the confirmation immediately when it can find the meeting note:

- rename `YYYY-MM-DD_Unknown_主题.md` to `YYYY-MM-DD_联系人_主题.md`;
- update meeting frontmatter to `match_confidence: "confirmed_by_user"` and `crm_updated: true`;
- create or update the contact file under `10_CRM/Contacts/`;
- append the meeting to the contact's `对话记录更新`;
- mark the pending confirmation as `resolved`.

If the meeting note cannot be found, the agent still records `confirmation-log.md` and housekeeping will retry later.

## Commands

Commands are still supported for precision and debugging:

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
- `手动输入`: asks the user to reply naturally, for example `Alex Chen` or `这个联系人叫 Alex Chen`;
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
  -> user clicks a candidate or replies naturally
  -> bot records confirmation-log.md
  -> bot immediately renames the meeting note and updates the contact CRM file
  -> housekeeping later audits unresolved confirmations only
```

The bot should not directly merge contacts. Merge requests must be written as proposals under:

```text
.crm-system/merge-proposals/
```
