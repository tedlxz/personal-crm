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

## Installable Skills

| Skill Package | Purpose |
| --- | --- |
| `personal-crm-bootstrap.skill` | Create vault folders, templates, and config. |
| `viaim-note-sync.skill` | Extract VIAIM transcripts and import VIAIM exports. |
| `personal-feishu-minutes-reader.skill` | Read Feishu Minutes through personal OAuth where available. |
| `personal-outlook-calendar-matcher.skill` | Match recordings to Outlook/Gmail/Google Calendar/ICS events. |
| `personal-obsidian-crm-archiver.skill` | Write meeting notes and CRM updates into Obsidian. |

## Scripts

| Script | Purpose |
| --- | --- |
| `scripts/setup_personal_crm_vault.py` | Bootstrap a local Obsidian vault. |
| `skills-src/viaim-note-sync/scripts/import_viaim_exports.py` | Import exported VIAIM files into the vault inbox. |
| `skills-src/personal-feishu-minutes-reader/scripts/feishu_minutes_reader.py` | Feishu OAuth and Minutes transcript reader. |

## Validation Performed

- Verified Chrome plugin can read the logged-in VIAIM cloud page.
- Verified VIAIM recording list and transcript tab are DOM-readable.
- Verified target transcript can be extracted directly from DOM.
- Verified Python scripts compile.

