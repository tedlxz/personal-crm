# CRM Housekeeping Agent

## Purpose

The CRM system needs a recurring housekeeping agent, not just one-off note generation.

The agent should:

- scan unarchived transcripts;
- match each transcript to calendar context;
- create or update meeting notes;
- create or update contact CRM files;
- generate reusable insights;
- ask the user when the evidence is insufficient;
- keep an audit trail of what was archived and why.

## Inbox Sources

```text
00_Inbox/VIAIM/Transcripts/
00_Inbox/Transcripts/
00_Inbox/FeishuLinks/
00_Inbox/Audio/
```

## Processing States

Every transcript should end in one of four states:

| State | Meaning | Action |
| --- | --- | --- |
| `archived` | Contact and meeting were identified confidently | Create/update CRM and move transcript to attachments |
| `needs_user_confirmation` | Multiple possible contacts/events | Ask one concise question |
| `needs_contact_creation` | Person is new or identity unclear | Trigger contact builder |
| `blocked` | Missing transcript, corrupted file, inaccessible source | Log blocker and leave in inbox |

## Matching Logic

Use evidence in this order:

1. Calendar event at the transcript time.
2. VIAIM / Feishu note title and timestamp.
3. Names, phone numbers, company names, and locations inside transcript.
4. Existing contact aliases and company files.
5. WeChat contact/session context when available.

## User Confirmation Policy

Ask the user only when the next write could be wrong:

```text
这份 transcript 可能对应以下两个联系人：A / B。请确认归档到哪一个？
```

Do not ask open-ended questions when a narrow choice is enough.

## Insight Generation

Generate insights separately from meeting notes. A meeting note captures what happened; an insight captures what remains useful later.

Create or update insight files under:

```text
30_Insights/
  People/
  Market/
  Company/
  Weekly/
```

Insight candidates:

- repeated relationship pattern;
- market view useful beyond one meeting;
- company or sector update;
- new follow-up risk;
- meaningful change in contact priority.

Do not create an insight for every meeting. Only create one when it is reusable.

## Weekly Housekeeping

Run weekly:

```text
Scan all meetings from this week.
Find unclosed follow-ups.
Summarize new contacts.
Summarize relationship changes.
Generate reusable insights.
Identify transcripts still unarchived.
```

Expected output:

```text
30_Insights/Weekly/YYYY-WW_CRM周报.md
```

## Audit Log

Append every run to:

```text
.crm-system/run-log.md
```

Include:

- timestamp;
- transcripts scanned;
- files created/updated;
- user confirmations needed;
- blocked items.

