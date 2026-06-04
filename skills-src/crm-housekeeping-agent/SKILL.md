---
name: crm-housekeeping-agent
description: Run recurring CRM housekeeping for a personal Obsidian CRM. Use when asked to scan unarchived transcripts, auto-archive inbox items, generate insights, create weekly CRM reviews, detect stale follow-ups, or ask the user for confirmation when transcripts cannot be confidently archived.
---

# CRM Housekeeping Agent

Use this skill as a recurring sub-agent for CRM maintenance.

## Goals

- Scan unarchived transcripts and source links.
- Match each item to calendar events and contacts.
- Trigger contact creation when a contact is new.
- Generate meeting notes.
- Generate reusable insights.
- Ask for user confirmation when confidence is low.
- Maintain an audit log.

## Inbox

Scan:

```text
00_Inbox/VIAIM/Transcripts/
00_Inbox/Transcripts/
00_Inbox/FeishuLinks/
00_Inbox/Audio/
```

## Decision States

Use exactly one:

- `archived`
- `needs_user_confirmation`
- `needs_contact_creation`
- `blocked`

## Workflow

1. List inbox items.
2. For each transcript, extract title, timestamp, names, companies, phone numbers, and action items.
3. Match calendar source using `personal-outlook-calendar-matcher`.
4. Search existing contacts and companies.
5. If one contact is high confidence, archive with `personal-obsidian-crm-archiver`.
6. If no contact exists but identity is sufficiently clear, trigger `contact-builder`.
7. If multiple contacts are plausible, ask the user one concise confirmation question.
8. Generate reusable insights only when content is useful beyond this meeting.
9. Append results to `.crm-system/run-log.md`.

## Confidence Rules

High confidence:

- calendar event and transcript agree on person or company; or
- transcript includes a unique phone/name already in CRM.

Medium confidence:

- title and transcript indicate a likely person/company but no existing CRM file.

Low confidence:

- no title, no calendar match, or multiple plausible contacts.

Never create or merge contacts on low confidence.

## Output

Report:

- archived items;
- new contact candidates;
- insights created;
- follow-ups found;
- questions for the user;
- blocked items.

