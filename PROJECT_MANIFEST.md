# Project Manifest

## Deliverable Name

Personal CRM

## Purpose

Package a reusable automation system for personal CRM and recording management:

- Initialize an Obsidian vault.
- Pull VIAIM transcripts.
- Read Feishu Minutes where available.
- Match meetings against calendar sources.
- Archive structured notes into Obsidian.
- Ask low-confidence archive questions through Feishu bot.
- Search and answer from the local Obsidian knowledge base through a bot backend.

## Installable Skills

| Skill Package | Purpose |
| --- | --- |
| `personal-crm-bootstrap.skill` | Create vault folders, templates, and config. |
| `crm-housekeeping-agent.skill` | Scan inbox, archive transcripts, generate insights, and ask for confirmation when needed. |
| `contact-builder.skill` | Create or update CRM contact files from transcripts, calendar, email, or WeChat context. |
| `wechat-contact-reader.skill` | Read local WeChat contact/session exports into contact candidate data. |
| `viaim-note-sync.skill` | Extract VIAIM transcripts and import VIAIM exports. |
| `personal-feishu-minutes-reader.skill` | Read Feishu Minutes through personal OAuth where available. |
| `personal-outlook-calendar-matcher.skill` | Match recordings to Outlook/Gmail/Google Calendar/ICS events. |
| `personal-obsidian-crm-archiver.skill` | Write meeting notes and CRM updates into Obsidian. |

## Scripts

| Script | Purpose |
| --- | --- |
| `scripts/setup_personal_crm_vault.py` | Bootstrap a local Obsidian vault. |
| `scripts/contact_matcher.py` | Score contact candidates for conservative CRM archiving. |
| `scripts/feishu_bot_agent.py` | Local Feishu event backend for confirmation commands and knowledge-base search. |
| `scripts/install_housekeeping_launchd.py` | Generate a macOS daily housekeeping LaunchAgent. |
| `skills-src/viaim-note-sync/scripts/import_viaim_exports.py` | Import exported VIAIM files into the vault inbox. |
| `skills-src/personal-feishu-minutes-reader/scripts/feishu_minutes_reader.py` | Feishu OAuth and Minutes transcript reader. |

## Validation Performed

- Verified Chrome plugin can read the logged-in VIAIM cloud page.
- Verified VIAIM recording list and transcript tab are DOM-readable.
- Verified target transcript can be extracted directly from DOM.
- Verified Python scripts compile.
- Added CRM housekeeping, contact-building, and WeChat contact ingestion design.
- Verified Feishu bot can send low-confidence archive questions.
- Verified local Feishu bot backend handles `/pending`, `/search`, and `/archive` simulation events.
