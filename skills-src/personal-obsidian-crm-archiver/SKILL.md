---
name: personal-obsidian-crm-archiver
description: Archive Feishu Minutes, VIAIM notes, iFlytek transcripts, Outlook-matched meetings, and pasted conversation notes into a personal Obsidian CRM. Use when asked to update a contact, create a meeting note, summarize prior interactions, generate follow-ups, or maintain CRM/company/insight Markdown files.
---

# Personal Obsidian CRM Archiver

Use this skill as the final write layer.

## Core rules

- One person = one contact Markdown file.
- One meeting = one meeting Markdown file.
- Contact files hold stable profile and interaction timeline.
- Meeting files hold meeting-specific detail.
- Do not paste full transcript into a contact file.
- Use Obsidian wiki links.
- Preserve user-written content.

## Vault structure

Use the structure created by `personal-crm-bootstrap`.

## Sensitivity

Every new file must include:

```yaml
sensitivity: external_ok
```

Allowed:

- `external_ok`
- `confidential`
- `internal_only`

If unclear, use `confidential`.

## Workflow

1. Read source data from Feishu, VIAIM, transcript, or manual input.
2. Read calendar match if available.
3. Extract participants, companies, date, topic, follow-ups, and durable insights.
4. Search existing contact files.
5. Create missing contacts from `80_Templates/crm-contact-template.md`.
6. Create meeting note from `80_Templates/meeting-note-template.md`.
7. Append one interaction row to each contact.
8. Update company file if needed.
9. Move processed transcript/audio to `90_Attachments`.

## File names

```text
10_CRM/Contacts/姓名.md
10_CRM/Companies/公司名.md
20_Meetings/YYYY/MM/YYYY-MM-DD_主要联系人_主题.md
```

## Completion response

Report created/updated files, follow-up tasks, calendar confidence, and unresolved ambiguities.

