# Personal CRM

Personal CRM is a local-first meeting memory and relationship management system for Obsidian, Claude Code, and Codex.

It connects meeting transcripts from VIAIM / iFLYTEK, Feishu Minutes, and calendar context from Outlook/Gmail/Google Calendar/ICS, then writes structured contact files, meeting notes, company profiles, follow-ups, and insights into an Obsidian vault.

## What This Package Contains

```text
docs/
  execution-plan.md
  prd.md
  crm-housekeeping-agent.md
  viaim-transcript-automation-validation.md
  wechat-contact-ingestion.md
scripts/
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

## Quick Start

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
- [VIAIM Automation Validation](docs/viaim-transcript-automation-validation.md)
- [WeChat Contact Ingestion](docs/wechat-contact-ingestion.md)
