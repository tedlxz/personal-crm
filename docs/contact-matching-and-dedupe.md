# Contact Matching And Dedupe

## Objective

Archive transcripts accurately without misfiling meetings under the wrong person. The system should ask a narrow confirmation question when evidence is weak.

## Evidence Sources

Use all available sources:

- transcript title;
- transcript body;
- recording timestamp;
- location;
- Feishu Minutes metadata;
- VIAIM metadata;
- calendar event title and attendees;
- Gmail meeting invitations / `.ics`;
- existing CRM contacts;
- WeChat contact aliases, if available;
- user confirmations from prior runs.

## Matching Score

Score each candidate contact out of 100:

| Evidence | Score |
| --- | ---: |
| Calendar attendee exact email/name match | +35 |
| Calendar title contains contact/company | +20 |
| Transcript contains exact contact name | +25 |
| Transcript contains known alias / WeChat remark | +20 |
| Phone number exact match | +35 |
| Company exact match | +15 |
| Same project/deal tag | +10 |
| Same recurring meeting pattern | +10 |
| Name fuzzy match only | +8 to +15 |
| Conflicting company or role | -25 |
| Two candidates within 10 points | require confirmation |

## Fuzzy Name Matching

Chinese ASR often mishears names. Normalize before matching:

- remove honorifics: 总、老师、董、博士、先生、女士;
- normalize spaces and punctuation;
- compare simplified/traditional variants where needed;
- compare pinyin initials for short Chinese names;
- compare common homophones only as weak evidence;
- use WeChat remarks and aliases as stronger evidence than ASR text.

Examples:

```text
张雷 / 张磊 / 张蕾 -> fuzzy candidate, ask if no calendar support
陆总 -> match contact with surname 陆 only if calendar/company also supports it
手机号 -> strongest identity evidence if exact
```

## Decision Thresholds

- `>= 80`: archive automatically.
- `60-79`: create/update meeting note but ask before contact update.
- `< 60`: write `Unknown` meeting note and ask user.
- multiple candidates within 10 points: ask user.
- any merge of existing contacts: ask user.

## Local Matcher

Use the helper script for a first-pass candidate list:

```bash
python3 scripts/contact_matcher.py \
  --vault "/Users/tedliu/Documents/Obsidian/Personal CRM" \
  --title "2026-06-04 日本泰澳投资布局" \
  --transcript-file "/path/to/transcript.txt" \
  --participant "张三" \
  --company "公司A"
```

The script returns:

```json
{
  "decision": "auto_archive|needs_user_confirmation",
  "candidates": []
}
```

The script is intentionally conservative. Its output is evidence for the housekeeping agent, not permission to merge contacts.

## New Contact Creation

Create a new contact automatically only when at least two strong identifiers exist:

- full name + company;
- full name + calendar email;
- phone number + meeting context;
- WeChat remark + transcript/calendar context.

If only a nickname, surname, or title exists, create `Unknown` meeting note and ask.

## Dedupe And Merge

Possible duplicate if:

- same email or phone;
- same WeChat alias;
- same name and company;
- fuzzy Chinese name and same company/project;
- repeated calendar attendee with similar display name.

Never auto-merge existing contacts. Instead write a merge proposal:

```text
.crm-system/merge-proposals/YYYY-MM-DD_contact-a_contact-b.md
```

Proposal should include:

- why they may be the same person;
- conflicting fields;
- meetings attached to each;
- recommended canonical name;
- exact user command needed to merge.

## Feishu Confirmation Commands

Use concise commands:

```text
/archive 1
/archive 2
/new 姓名 公司 Title
/merge A B canonical=姓名
/skip
```

All confirmations should be logged in:

```text
.crm-system/confirmation-log.md
```
