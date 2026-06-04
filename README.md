# Personal CRM

Personal CRM is a local-first meeting memory and relationship management system for Obsidian, Claude Code, and Codex.

It connects meeting transcripts from VIAIM / iFLYTEK, Feishu Minutes, and calendar context from Outlook/Gmail/Google Calendar/ICS, then writes structured contact files, meeting notes, company profiles, follow-ups, and insights into an Obsidian vault.

## What This Package Contains

```text
docs/
  execution-plan.md
  prd.md
  viaim-transcript-automation-validation.md
scripts/
  setup_personal_crm_vault.py
skills/
  personal-crm-bootstrap.skill
  personal-feishu-minutes-reader.skill
  personal-obsidian-crm-archiver.skill
  personal-outlook-calendar-matcher.skill
  viaim-note-sync.skill
skills-src/
  personal-crm-bootstrap/
  personal-feishu-minutes-reader/
  personal-obsidian-crm-archiver/
  personal-outlook-calendar-matcher/
  viaim-note-sync/
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
- [VIAIM Automation Validation](docs/viaim-transcript-automation-validation.md)

