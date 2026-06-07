# Daily Housekeeping Bot

## Objective

Run once per day and move every new Feishu Minutes / VIAIM transcript into the Obsidian knowledge base with the same quality standard as manual processing.

## Daily Flow

```text
Schedule trigger
  -> refresh Feishu token if needed
  -> pull today's Feishu Minutes
  -> pull / import today's VIAIM transcripts
  -> match each transcript to calendar context
  -> match or create contact candidates
  -> generate detailed meeting notes
  -> update contact/company files
  -> ask user via Feishu when confidence is low
  -> append audit log
```

## What The Bot Can Do Automatically

The bot may archive without asking when all conditions are true:

- transcript date/time matches exactly one calendar event within the configured window;
- event attendees or title match one existing contact/company;
- transcript mentions the same person/company or a strong alias;
- confidence score is `>= 80`;
- no conflicting existing contact is found.

## What Requires User Confirmation

Ask the user before writing CRM when:

- multiple contacts are plausible;
- transcript only has a phone number or nickname;
- ASR may have misheard a Chinese name;
- calendar event has no attendee names;
- the note involves sensitive transaction code names;
- a new contact would be created from weak evidence only;
- merge/dedupe would combine two existing contacts.

## Feishu Confirmation Interface

Preferred interaction is a Feishu interactive card. The message should be short and actionable:

```text
需要确认归档对象

录音：2026-06-04_Unknown_日本泰澳投资布局
时间：2026-06-04 12:51
原因：联系人置信度不足

[候选联系人 A] [候选联系人 B]
[手动输入] [跳过]
```

Use `send_confirmation_card`:

```bash
python3 skills-src/personal-feishu-minutes-reader/scripts/feishu_minutes_reader.py \
  --action send_confirmation_card \
  --recording-title "2026-06-04_Unknown_日本泰澳投资布局" \
  --recorded-at "2026-06-04 12:51" \
  --reason "联系人置信度不足，需要确认归档对象。" \
  --candidates-json '[{"name":"张三","company":"公司A","score":72}]'
```

If card sending or card callbacks are unavailable, fall back to a text message with `/archive`, `/new`, and `/skip` commands.

When card callbacks are available, the user does not need to remember commands. After clicking `手动输入`, the bot should accept natural-language replies:

```text
Alex Chen
这个联系人叫 Alex Chen
归到 Alex Chen
新建 Alex Chen Northstar Advisor
跳过
```

After a user confirms the contact, the bot should apply the result immediately when possible:

- rename `Unknown` meeting notes to the confirmed contact title;
- set `match_confidence: "confirmed_by_user"`;
- set `crm_updated: true`;
- create or update the contact file;
- append the meeting to `对话记录更新`;
- mark the pending item as `resolved`.

If Feishu message sending is not available, write the question to:

```text
.crm-system/pending-confirmations.md
```

and report it in the Codex thread.

The local bot backend is:

```bash
python3 scripts/feishu_bot_agent.py --transport websocket
```

Configure Feishu long connection for:

```text
im.message.receive_v1
card.action.trigger
```

On macOS, a background LaunchAgent may need Full Disk Access if the repo or Obsidian vault lives under `~/Documents`. If permissions block the agent, run it from Codex/Terminal or grant the runtime Full Disk Access.

## Suggested macOS Schedule

Use `launchd` for a local machine:

```text
~/Library/LaunchAgents/com.personalcrm.housekeeping.plist
```

Run daily at 20:30 local time. The job should call Claude Code or Codex CLI with the vault path and this instruction:

```text
Run crm-housekeeping-agent for /Users/tedliu/Documents/Obsidian/Personal CRM.
Process today's Feishu and VIAIM transcripts.
Do not update contacts on low confidence. Ask user via Feishu or pending-confirmations.md.
```

Generate the plist:

```bash
python3 scripts/install_housekeeping_launchd.py \
  --vault "/Users/tedliu/Documents/Obsidian/Personal CRM" \
  --repo "/Users/tedliu/Documents/Codex/2026-06-03/files-mentioned-by-the-user-june/outputs/Personal-CRM" \
  --time "20:30"
```

Then load it:

```bash
launchctl load ~/Library/LaunchAgents/com.personalcrm.housekeeping.plist
```

For Codex Desktop, use a recurring automation instead of `launchd` when available. The automation prompt should be:

```text
Run crm-housekeeping-agent for /Users/tedliu/Documents/Obsidian/Personal CRM.
Process today's Feishu Minutes and VIAIM transcripts.
Match calendar evidence when available.
Use the detailed notes standard before writing CRM.
Do not update contacts or merge contacts on low confidence.
Ask narrow confirmation questions via Feishu or .crm-system/pending-confirmations.md.
Append results to .crm-system/run-log.md.
```

## Feishu Token Requirements

The Feishu app must:

- include `offline_access` in OAuth scope;
- include `im:message` and `im:message:send_as_bot` if Feishu message notifications are enabled;
- have the offline access permission approved;
- have bot capability enabled if messages should be sent through Feishu;
- have refresh user_access_token enabled in security settings, if the switch is visible;
- be republished after permission/security changes.

The token cache is:

```text
~/.personal_feishu_user_token.json
```

Refresh behavior:

- access token expires in about 2 hours;
- refresh token can refresh it;
- refresh token is single-use;
- after refresh, immediately save the new access token and new refresh token.

## Audit Log

Append every run to:

```text
.crm-system/run-log.md
```

Each run should include:

- run time;
- Feishu items scanned;
- VIAIM items scanned;
- archived notes;
- contact files updated;
- pending confirmations;
- blocked items;
- token refresh status.
