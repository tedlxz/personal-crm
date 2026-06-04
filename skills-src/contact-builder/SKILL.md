---
name: contact-builder
description: Create or update personal CRM contact files from transcripts, WeChat contact exports, calendar attendees, email invitations, or user-provided context. Use when a new contact needs to be created, a contact candidate needs confirmation, or identity/background fields should be inferred and written to Obsidian.
---

# Contact Builder

Use this skill when the system discovers a person who is not yet represented in `10_CRM/Contacts/`.

## Inputs

Possible sources:

- transcript text;
- calendar attendees;
- Gmail meeting invitations;
- WeChat contact/session export;
- user-provided name/title/company;
- existing company files.

## Required Fields

Create a contact only when at least one reliable identifier exists:

- name or display name;
- company;
- title;
- phone/email/WeChat alias;
- meeting context.

If the person cannot be reliably identified, ask the user.

## Contact Creation Workflow

1. Normalize name and aliases.
2. Search existing contact files for duplicates.
3. Search company files for the company.
4. Infer background fields from evidence.
5. Set `sensitivity: confidential` unless clearly external/public.
6. Create contact file from `80_Templates/crm-contact-template.md`.
7. Link the source meeting and any relevant company.

## WeChat Data Handling

When WeChat export is available:

- use remark name and alias as aliases;
- use recent session context as weak evidence;
- do not copy full chat history into the contact file;
- do not send or modify WeChat messages;
- ask before merging contacts.

## User Confirmation

Ask a narrow question:

```text
我发现这个联系人可能是「张三 / 某公司」。是否新建联系人文件？
```

If multiple candidates:

```text
这条 transcript 可能对应 A、B 或新联系人。请选择归档对象。
```

## Output

Report:

- contact file created or updated;
- aliases added;
- evidence used;
- uncertainty remaining.

