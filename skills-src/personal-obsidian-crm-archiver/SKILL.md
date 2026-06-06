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
- Always turn transcripts into detailed model-written Markdown notes before CRM updates. Do not write shallow summaries.

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

## Transcript Summarization Standard

Before writing a meeting note, summarize the raw transcript with `70_Prompts/transcript-to-detailed-notes.md`.

The output must:

- use Markdown bullets grouped by topic;
- preserve accurate names, companies, titles, products, amounts, percentages, dates, time ranges, quantities, valuation multiples, risks, and promised next steps;
- distinguish facts, speaker opinions, decisions, risks, and action items;
- attribute important points to speakers when the transcript makes this clear;
- keep high-value original wording only as short excerpts;
- keep the full transcript in `90_Attachments/Transcripts` or as a source link;
- avoid generic summaries such as "discussed cooperation" without concrete details.

## File names

```text
10_CRM/Contacts/姓名.md
10_CRM/Companies/公司名.md
20_Meetings/YYYY/YYYY-MM-DD_HHMM_主要人物_主题.md
```

The meeting title must include time, people, and topic:

```text
# YYYY-MM-DD HH:MM 主要人物 - 主题
```

If a person or topic cannot be identified confidently, use `Unknown` in the filename and ask the user one concise confirmation question before creating/updating contact files.

## Completion response

Report created/updated files, follow-up tasks, calendar confidence, and unresolved ambiguities.
