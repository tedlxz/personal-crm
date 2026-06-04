# WeChat Contact Ingestion Options

## Goal

Use WeChat as a contact-context source for CRM:

- identify who a meeting/contact is;
- map aliases, nicknames, phone numbers, group names, and conversation context;
- create contact files with less manual input;
- improve transcript-to-contact matching.

This should be local-first and read-only whenever possible.

## Recommended Approach

Use WeChat-derived data only as supporting evidence. Do not let WeChat automation send messages or modify contacts in the MVP.

Preferred flow:

```text
WeChat local contact/session export
  → JSON/CSV local file
  → contact-builder skill
  → Obsidian CRM contact file
```

## GitHub Project Shortlist

### 1. wechat-cli

Repository: https://github.com/huohuoer/wechat-cli

Best fit for this project.

Why:

- local WeChat data access;
- command-line interface;
- JSON output;
- designed for AI agent workflows;
- can export contacts, sessions, history, and files;
- lower risk than live WeChat hook/robot frameworks.

Use case:

```text
Export contacts and recent sessions
  → match transcript names/phone numbers
  → create CRM contact candidates
```

Caveat:

- version support depends on macOS and WeChat versions;
- should be tested on the user's exact machine and WeChat client.

### 2. WeChatFerry

Repository: https://github.com/lich0821/WeChatFerry

Powerful but not recommended for MVP.

Why:

- can access messages, contacts, rooms, and automate WeChat;
- useful for advanced automation.

Risks:

- hook/robot-style integration;
- higher maintenance risk when WeChat updates;
- more sensitive from privacy and account-safety perspectives;
- overpowered for read-only CRM contact ingestion.

Use only if:

- local read-only export is insufficient;
- the user accepts higher operational risk;
- no message sending is enabled by default.

### 3. WeChatExporter / wxdump-style tools

These projects can export historical WeChat chat data, often by reading local databases.

Potential use:

```text
Export historical chats
  → build contact aliases and relationship context
  → enrich CRM background
```

Caveats:

- many are version-specific;
- database decryption can be brittle;
- some repositories become stale quickly;
- must avoid committing exported chats to GitHub.

## Recommended MVP

1. Start with `wechat-cli`.
2. Export contact list and recent session metadata only.
3. Store output locally under:

```text
.crm-system/wechat/
```

4. Use contact builder to create suggested CRM files.
5. Ask user before creating or merging contacts.

## Contact Candidate Schema

```json
{
  "source": "wechat",
  "display_name": "",
  "remark_name": "",
  "alias": "",
  "phone": "",
  "company_guess": "",
  "recent_session_titles": [],
  "confidence": "high|medium|low",
  "suggested_contact_file": ""
}
```

## Safety Rules

- Do not send WeChat messages.
- Do not modify WeChat contacts.
- Do not upload chat history to external services.
- Do not commit WeChat exports to GitHub.
- Treat WeChat-derived data as `confidential` by default.

