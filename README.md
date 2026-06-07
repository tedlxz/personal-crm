# Personal CRM

Personal CRM is a local-first meeting memory and relationship management system for Obsidian, Claude Code, and Codex.

It connects meeting transcripts from VIAIM / iFLYTEK, Feishu Minutes, and calendar context from Outlook/Gmail/Google Calendar/ICS, then writes structured contact files, meeting notes, company profiles, follow-ups, and insights into an Obsidian vault.

## 先读这个：系统能做什么

第一次了解这个项目，建议先读：

[Personal CRM 系统概览](docs/system-overview.zh.md)

里面有系统示意图、核心功能、日常使用方式和需要哪些授权。

## 中文快速安装

### 方式一：用 Git 安装

```bash
git clone https://github.com/tedlxz/personal-crm.git
cd personal-crm
python3 scripts/personal_crm_install_wizard.py
```

安装向导会用中文提示你填写 Obsidian vault 路径、飞书 App ID / App Secret，并把本地配置写入 `.env`。

### 方式二：用压缩包安装

1. 解压 `Personal-CRM-deliverable.zip`。
2. 把根目录里的 [START_HERE_拖给Codex安装.md](START_HERE_拖给Codex安装.md) 拖给 Codex。
3. 如果中文文件名在解压后显示异常，改用 [START_HERE_INSTALL_FOR_CODEX.md](START_HERE_INSTALL_FOR_CODEX.md)。
4. 让 Codex 按文件里的步骤执行安装。

### 默认安装位置

如果你不指定路径，系统会使用：

```text
~/Documents/Obsidian/Personal CRM
```

安装成功后，用 Obsidian 打开这个文件夹即可。

## 飞书配置需要用户自己准备什么

每个用户都需要在自己的飞书开放平台应用里获取自己的凭证。不要复用别人的 App ID 或 App Secret。

在 [飞书开放平台](https://open.feishu.cn/) 创建或打开「企业自建应用」后：

1. 「凭证与基础信息」里复制 `App ID` 和 `App Secret`。
2. 「安全设置」里添加 OAuth 重定向 URL：

```text
http://localhost:9876/callback
```

3. 「事件与回调」里选择长连接接收事件和回调。
4. 「权限管理」里至少开通并发布：

```text
im:message:send_as_bot
im:message
minutes:minutes.search:read
minutes:minutes:readonly
minutes:minutes.transcript:export
calendar:calendar:readonly
contact:user.base:readonly
offline_access
```

安装向导会把这些值写入本地 `.env`。`.env` 已经被 `.gitignore` 排除，不应提交。

## What This Package Contains

```text
START_HERE_拖给Codex安装.md
START_HERE_INSTALL_FOR_CODEX.md
.env.example
docs/
  system-overview.zh.md
  execution-plan.md
  prd.md
  crm-housekeeping-agent.md
  contact-matching-and-dedupe.md
  daily-housekeeping-bot.md
  feishu-bot-agent.md
  viaim-transcript-automation-validation.md
  wechat-contact-ingestion.md
scripts/
  contact_matcher.py
  feishu_bot_agent.py
  install_housekeeping_launchd.py
  install_lark_codex_bridge_launchd.py
  personal_crm_install_wizard.py
  setup_personal_crm_vault.py
skills/
  contact-builder.skill
  crm-housekeeping-agent.skill
  personal-crm-bootstrap.skill
  personal-feishu-minutes-reader.skill
  personal-obsidian-crm-archiver.skill
  personal-outlook-calendar-matcher.skill
  viaim-note-sync.skill
  wechat-contact-reader.skill
skills-src/
  contact-builder/
  crm-housekeeping-agent/
  personal-crm-bootstrap/
  personal-feishu-minutes-reader/
  personal-obsidian-crm-archiver/
  personal-outlook-calendar-matcher/
  viaim-note-sync/
  wechat-contact-reader/
```

## Manual Quick Start

1. Install Obsidian.
2. Install Claude Code or use Codex with Chrome plugin access.
3. Create or choose an Obsidian vault.
4. Run:

```bash
python scripts/setup_personal_crm_vault.py --vault "/absolute/path/to/ObsidianVault"
```

5. Use the packaged skills or their source folders to automate:

```text
VIAIM transcript -> calendar matching -> Claude/Codex notes -> Obsidian CRM
```

Transcripts are not archived as shallow summaries. Codex / Claude must first convert each transcript into a detailed bullet-style Markdown meeting note named `YYYY-MM-DD_主要人物_主题.md`, while preserving exact data, people, companies, risks, decisions, and action items. The note must then be linked back to the corresponding contact file under `10_CRM/Contacts`.

## Recommended Automation Flow

```text
VIAIM Cloud
  -> select recording by time/title
  -> switch to Transcript
  -> extract transcript from DOM
  -> save to Obsidian inbox
  -> match calendar event
  -> generate meeting note
  -> update contact CRM
```

## Feishu Minutes Flow

The Feishu Minutes path has been validated with personal user OAuth:

```text
Feishu custom app
  -> approve minutes scopes
  -> OAuth user authorization
  -> search historical minutes by time range
  -> export transcript by minute token
  -> archive into Obsidian CRM
```

See [docs/execution-plan.md](docs/execution-plan.md) section `4.2` for the exact permissions, redirect URL, commands, and error handling notes.

## CRM Housekeeping

The long-running value comes from recurring housekeeping:

```text
scan unarchived transcripts
  -> match calendar/contact evidence
  -> archive high-confidence items
  -> ask narrow confirmation questions when uncertain
  -> create contact candidates
  -> generate reusable insights
```

Use:

- `crm-housekeeping-agent.skill`
- `contact-builder.skill`
- `wechat-contact-reader.skill`
- [Daily Housekeeping Bot](docs/daily-housekeeping-bot.md)
- [Contact Matching And Dedupe](docs/contact-matching-and-dedupe.md)

For a local daily schedule:

```bash
python3 scripts/install_housekeeping_launchd.py \
  --vault "$HOME/Documents/Obsidian/Personal CRM" \
  --repo "$(pwd)" \
  --time "20:30"
```

For Feishu bot confirmation and knowledge-base Q&A, run:

```bash
python3 scripts/feishu_bot_agent.py --transport websocket
```

Use Feishu long connection for message events and card callbacks. The bot can understand short natural-language replies such as `归到 Alex Chen` or `这个联系人叫 Alex Chen`. See [Feishu Bot Agent](docs/feishu-bot-agent.md).

To keep the bot running as a local macOS service:

```bash
FEISHU_APP_ID="<app_id>" \
FEISHU_APP_SECRET="<app_secret>" \
python3 scripts/install_feishu_bot_agent_launchd.py --load
```

If macOS blocks the service from reading `~/Documents`, grant Full Disk Access to the runtime or keep the agent running from Codex/Terminal.

For Lark CLI/CUI natural-language questions that should search the Obsidian CRM first:

```bash
CODEX_WORKDIR="$(pwd)" \
PERSONAL_CRM_VAULT="$HOME/Documents/Obsidian/Personal CRM" \
LARK_CODEX_SANDBOX="workspace-write" \
node scripts/lark_codex_bridge.mjs
```

For daily use, keep the Lark CLI/CUI bridge online as a macOS service:

```bash
python3 scripts/install_lark_codex_bridge_launchd.py --load
```

This service listens to Feishu messages, immediately replies `收到，Codex 正在处理...`, then runs Codex with access to both the Personal CRM repo and the Obsidian vault.

## Calendar Strategy

The preferred calendar source is whichever Codex/Claude Code can actually read:

1. Work/school Outlook connector, if available.
2. Gmail meeting invitations and `.ics` attachments.
3. Google Calendar as a scheduling hub, with work email added as attendee.
4. Local `.ics` file or pasted agenda as fallback.

## Security Notes

- Keep the Obsidian vault local by default.
- Do not commit personal transcripts, audio, tokens, or CRM files.
- Store API credentials in environment variables, not in this repository.
- Treat uncertain meeting content as `confidential`.

## Primary Documents

- [Execution Plan](docs/execution-plan.md)
- [PRD](docs/prd.md)
- [CRM Housekeeping Agent](docs/crm-housekeeping-agent.md)
- [Daily Housekeeping Bot](docs/daily-housekeeping-bot.md)
- [Feishu Bot Agent](docs/feishu-bot-agent.md)
- [Contact Matching And Dedupe](docs/contact-matching-and-dedupe.md)
- [VIAIM Automation Validation](docs/viaim-transcript-automation-validation.md)
- [WeChat Contact Ingestion](docs/wechat-contact-ingestion.md)
