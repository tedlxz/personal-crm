---
name: personal-crm-bootstrap
description: Bootstrap a personal Obsidian CRM vault for meeting-note and recording management. Use when asked to initialize the CRM system, create the vault structure, install templates, or prepare a folder so Claude Code can archive Feishu, VIAIM, Outlook, and transcript data into Markdown.
---

# Personal CRM Bootstrap

Use this skill before any archiving work.

## Required input

The user must provide an absolute Obsidian vault path. If absent, ask for it.

## Action

Run:

```bash
python <skill_path>/scripts/setup_personal_crm_vault.py --vault "<absolute_vault_path>"
```

Do not ask the user to manually create folders or copy templates.

## Verify

Confirm these exist:

- `00_Inbox/VIAIM/Audio`
- `00_Inbox/VIAIM/Transcripts`
- `10_CRM/Contacts`
- `10_CRM/Companies`
- `20_Meetings`
- `30_Insights/Weekly`
- `80_Templates/crm-contact-template.md`
- `80_Templates/meeting-note-template.md`
- `.crm-system/config.json`

## Response

Report the vault path and the initialized folders.

