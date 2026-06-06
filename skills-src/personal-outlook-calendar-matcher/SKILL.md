---
name: personal-outlook-calendar-matcher
description: Match recordings, Feishu Minutes, VIAIM notes, iFlytek transcripts, or meeting text to calendar events by time, title, attendees, location, and names mentioned in transcript. Prefer Outlook Calendar when available; fall back to Gmail meeting invitations, Google Calendar data, local .ics files, or pasted agenda. Use when asked to identify which meeting a recording belongs to or enrich CRM archiving with calendar context.
---

# Personal Calendar Matcher

Use this skill before writing a meeting to CRM whenever calendar context is available.

## Sources

Prefer:

1. Outlook Calendar connector or MCP when the Codex/Claude environment exposes it.
2. Microsoft Graph OAuth with a supported work/school account.
3. Gmail connector: search/read meeting invitations and `.ics` attachments forwarded from Outlook or created through Gmail/Google Calendar.
4. Google Calendar source when available.
5. Exported `.ics` file.
6. User-pasted agenda.

## Account routing

If Outlook connector rejects the account because it requires a work or school account:

1. Do not keep retrying the same personal Microsoft account.
2. Ask whether a work/school Outlook account can be connected.
3. If not, use Gmail as the readable calendar intake:
   - Work Outlook can forward meeting invites to Gmail if company policy allows it.
   - For future scheduling, create or receive meetings through Gmail/Google Calendar and add the work email as an attendee so the work Outlook calendar is blocked too.
   - If Outlook subscribes to Google Calendar via iCal URL, treat it as read-only and potentially delayed.

When using Gmail, extract:

- meeting title
- organizer
- attendees
- start/end time
- location/meeting link
- `.ics` attachment content when available

## Matching score

```text
+50 time overlap
+20 participant name appears in transcript/title
+15 company name appears in transcript/title
+10 location or online meeting clue matches
+10 title semantic match
-30 private event with no other supporting evidence
```

Confidence:

- `high`: score >= 70
- `medium`: score 45-69
- `low`: score < 45

If confidence is low or two candidates are close, ask the user to confirm before updating CRM.

## Matching To CRM Contacts

After selecting candidate calendar events, pass attendee/title/company evidence into `scripts/contact_matcher.py` when available.

Do not treat a fuzzy name alone as enough for CRM update. Calendar attendee, company, email, phone, or WeChat alias support is required for auto-archive.

## Output

```json
{
  "calendar_source": "outlook",
  "event_id": "",
  "title": "",
  "start_time": "",
  "end_time": "",
  "attendees": [],
  "organizer": "",
  "location": "",
  "matched_contacts": [],
  "matched_companies": [],
  "match_confidence": "high|medium|low",
  "match_reason": ""
}
```
