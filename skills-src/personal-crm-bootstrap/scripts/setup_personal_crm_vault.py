#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


CONTACT_TEMPLATE = """---
type: crm_contact
name: ""
title: ""
company: ""
company_file: ""
status: active
relationship_strength: unknown
first_met_date: ""
first_met_place: ""
introduced_by: ""
last_contact_date: ""
next_follow_up_date: ""
sensitivity: external_ok
tags: [crm]
---

# {{name}}

## 基础信息

- 姓名：
- Title：
- 公司：
- 公司简介：
- 所在城市/地区：
- 联系方式：
- 主要标签：

## 建立联系的背景

- 何时建立联系：
- 何地建立联系：
- 通过谁认识：
- 当时场景：
- 初始印象：
- 对方认识的人：
- 与使用者/团队的关系：

## 公司与角色

- 公司名称：
- 公司做什么：
- 对方在公司的角色：
- 对方负责的业务/资源：
- 公司与使用者关注领域的关系：

## 关系网络

- 介绍人：
- 共同认识的人：
- 可能影响的人：
- 对方重视的关系：

## 当前画像

- 关注点：
- 需求/痛点：
- 能提供的资源：
- 可能合作方向：
- 沟通偏好：
- 注意事项：

## 对话记录更新

| 日期 | 场景 | 会议/对话 | 核心内容 | 后续动作 |
| --- | --- | --- | --- | --- |

## 待办与跟进

- [ ] 

## 关键洞察

- 

## 相关链接

- 公司：
- 相关会议：
- 相关项目：
- 相关 insight：
"""


MEETING_TEMPLATE = """---
type: meeting_note
date: ""
time: ""
title: ""
topic: ""
participants: []
primary_people: []
contacts: []
companies: []
source: ""
source_link: ""
audio_file: ""
transcript_file: ""
calendar_event_id: ""
match_confidence: ""
model_summary: true
sensitivity: external_ok
crm_updated: false
tags: [meeting]
---

# {{date}}_{{primary_people}}_{{topic}}

## 会议基本信息

- 时间：
- 地点/形式：
- 参与人：
- 来源：飞书妙记 / VIAIM / 讯飞转写 / 手动记录 / 音频
- 标题命名：`YYYY-MM-DD_主要人物_主题.md`
- 关联联系人：
- 关联公司：
- Outlook 日历匹配：
- 匹配置信度：

## 一句话摘要

- 

## Interviewee / Source Background

- 受访者/信息源身份：
- 信息源价值：
- Source Quality：S / A / B / Unknown
- Source bias / interest position：management / supplier / customer / competitor / investor / broker / unknown

## 详细会议纪要

> 由 Codex / Claude 根据 transcript 整理；尽量保留准确数据、金额、时间、比例、产品名、人名、公司名和承诺事项。不要只写泛泛总结。

### 1. 背景与会议目的

- 

### 2. 关键讨论与事实细节

- 

### 3. 数据、价格、时间线和数量

- 

### 4. 各方观点与判断

- 

### 5. Q&A / 主题化详细内容

- Q：
- A：

## 对方表达的需求/关切

- 

## 使用者表达的观点/承诺

- 

## 新增背景信息

- 

## 重要原话/高价值片段

- 

## 行动项

- [ ] 负责人：事项，截止时间：

## 应更新到 CRM 的内容

- 联系人：
- 需要新增/更新的信息：

## 可沉淀为 insight 的内容

- 

## Cross-Verification

- Confirmed：
- Contradicted：
- New information：
- Needs follow-up：

## Follow-Up Questions

- 

## Annotations & Discrepancies

- 

## 原始 transcript 位置

- `transcript_file`：
- `source_link`：
"""


COMPANY_TEMPLATE = """---
type: crm_company
name: ""
industry: ""
website: ""
sensitivity: external_ok
tags: [company]
---

# {{name}}

## 公司基础信息

- 公司名称：
- 公司做什么：
- 所在行业：
- 官网：
- 地区：

## 关键联系人

- 

## 关系概况

- 

## 历次互动

| 日期 | 联系人 | 会议 | 摘要 |
| --- | --- | --- | --- |

## 合作机会

- 

## 风险与注意事项

- 
"""


WEEKLY_TEMPLATE = """---
type: crm_weekly_review
week: ""
sensitivity: confidential
tags: [weekly-review]
---

# {{week}} CRM 周报

## 本周新增联系人

- 

## 本周重要对话

- 

## 待跟进事项

- [ ] 

## 关系变化

- 

## 可沉淀洞察

- 
"""


INDEX_NOTE = """# Personal CRM

## Inbox

- [[00_Inbox/Transcripts]]
- [[00_Inbox/VIAIM/Transcripts]]
- [[00_Inbox/FeishuLinks]]

## CRM

- [[10_CRM/Contacts]]
- [[10_CRM/Companies]]
- [[10_CRM/Networks]]

## Meetings

- [[20_Meetings]]

## Insights

- [[30_Insights/Weekly]]

## System

- [[70_Prompts/transcript-to-detailed-notes]]
- [[80_Templates/meeting-note-template]]
- [[80_Templates/crm-contact-template]]

## Operating Rules

- Every transcript must be summarized by Codex / Claude into detailed Markdown notes before CRM updates.
- Meeting note filenames use `YYYY-MM-DD_主要人物_主题.md`.
- Full transcripts stay in `90_Attachments/Transcripts`; contact files only keep stable facts and interaction rows.
- If identity or calendar matching is uncertain, mark `needs_user_confirmation` and ask before updating contacts.
"""


TRANSCRIPT_TO_NOTES_PROMPT = """# Transcript to Detailed Meeting Notes Prompt

Use this prompt whenever a Feishu Minutes, VIAIM, iFlytek, or manually pasted transcript is archived into CRM.

## Goal And Quality Bar

Turn the raw transcript into a detailed Markdown meeting note, not a shallow summary. Preserve concrete information that will matter later: people, companies, titles, products, numbers, dates, amounts, valuation multiples, deadlines, ownership, constraints, risks, promises, and next steps.

The note is a research record. Lost detail means lost value. Prefer a longer, complete note over a short summary.

## Core Principles

### 1. Anchor the timeline

- Establish the call date before writing.
- Convert relative dates into absolute dates when possible.
- If timing is unclear, preserve the original wording and add `[exact timing unclear from transcript]`.

### 2. Preserve completeness

- Include every substantive topic, data point, rationale, caveat, and follow-up.
- Keep background context and why a question was asked.
- Omit only filler and social pleasantries that carry no substance.

### 3. Preserve speaker nuance and uncertainty

- Keep uncertainty such as "I think", "not sure", "maybe", and "needs verification".
- If the speaker deflects, hesitates, or gives an incomplete answer, note it neutrally in brackets.
- Do not turn a tentative view into a confident conclusion.

### 4. Correct transcript errors carefully

- Fix obvious ASR errors silently when the correction is certain.
- For uncertain corrections, write `[transcript says X, likely Y]`.
- Flag questionable names, figures, tickers, project codes, and dates for user confirmation.

### 5. Present data clearly

- Use tables when 3+ comparable data points appear.
- Always keep units and periods with numbers.
- Mark quantitative claims with source confidence when possible.

### 6. PE research intelligence layer

- If the call is an expert / management / deal discussion, add:
  - interviewee or source background, if known;
  - source quality rating `S/A/B/Unknown` with rationale;
  - source bias / interest position, such as management, supplier, customer, competitor, investor, broker, or unknown;
  - cross-verification: `Confirmed`, `Contradicted`, `New information`, `Needs follow-up`;
  - follow-up questions that need another source.

### 7. Terminology layer

- For technical terms in AI infra, optical communications, semiconductors, data centers, or similar domains, explain them only when needed for understanding.
- Explain terms in investment context: value-chain position, why it matters, who benefits, who is threatened, and related confusing concepts.
- Keep term explanations concise and integrated into the note, not as generic encyclopedia entries.

## Output File

Create one meeting file:

```text
20_Meetings/YYYY/YYYY-MM-DD_主要人物_主题.md
```

Naming rules:

- `YYYY-MM-DD` comes from transcript metadata, source timestamp, or calendar match.
- `主要人物` should be the main external contact or most important participant. If uncertain, use `Unknown`.
- `主题` should be a short Chinese or English topic, max 16 characters when possible.
- Use ASCII hyphens and underscores in the filename; avoid slashes and punctuation that break file paths.

## Required Markdown Structure

Use `80_Templates/meeting-note-template.md`. Fill every section that has evidence. Prefer bullet points.

Required style:

- Detailed bullets, grouped by topic.
- Keep exact data where available.
- Attribute important opinions or commitments to speakers when clear.
- Separate facts, views, risks, decisions, and follow-ups.
- For expert calls, organize detailed content by topic, not necessarily transcript order.
- Use Q&A format when the call is interview-like: `Q:` for the question/prompt and `A:` for the detailed response.
- Do not invent missing data.
- If a contact/company cannot be identified confidently, mark it as `needs_user_confirmation`.
- Keep full transcript in `90_Attachments/Transcripts` or source link; meeting note should contain high-value excerpts only.

## CRM Updates

After creating the meeting note:

1. Update existing contact files under `10_CRM/Contacts`.
2. Create new contact files only when identity is clear or user confirms.
3. Append one row to each relevant contact's `对话记录更新`.
4. Update company files under `10_CRM/Companies` when company-level facts appear.
5. Add follow-ups as Markdown task checkboxes.
6. Add durable insights only when useful beyond this meeting.

## Knowledge Base Update

For durable research findings, create or update an insight entry using:

```text
Entry ID: [Industry]-[YYMMDD]-[Sequence]
Topic:
Source Quality:
Date:
Core View:
Supporting Data/Evidence:
Change from Prior Understanding:
Information Source:
Durability: structural / cyclical / time-sensitive
```

Keep global industry knowledge separate from deal-specific information.
"""


def write_if_missing(path: Path, content: str):
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True, help="Absolute path to Obsidian vault")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    dirs = [
        "00_Inbox/Audio",
        "00_Inbox/Transcripts",
        "00_Inbox/FeishuLinks",
        "00_Inbox/VIAIM/Audio",
        "00_Inbox/VIAIM/Transcripts",
        "00_Inbox/VIAIM/Exports",
        "10_CRM/Contacts",
        "10_CRM/Companies",
        "10_CRM/Networks",
        "20_Meetings",
        "30_Insights/Weekly",
        "40_Projects",
        "70_Prompts",
        "80_Templates",
        "90_Attachments/Audio",
        "90_Attachments/Transcripts",
        ".crm-system",
        ".crm-system/merge-proposals",
        ".crm-system/wechat",
    ]
    for rel in dirs:
        (vault / rel).mkdir(parents=True, exist_ok=True)

    write_if_missing(vault / "80_Templates/crm-contact-template.md", CONTACT_TEMPLATE)
    write_if_missing(vault / "80_Templates/meeting-note-template.md", MEETING_TEMPLATE)
    write_if_missing(vault / "80_Templates/company-template.md", COMPANY_TEMPLATE)
    write_if_missing(vault / "80_Templates/weekly-review-template.md", WEEKLY_TEMPLATE)
    write_if_missing(vault / "70_Prompts/transcript-to-detailed-notes.md", TRANSCRIPT_TO_NOTES_PROMPT)
    write_if_missing(vault / "00_Index.md", INDEX_NOTE)

    config_path = vault / ".crm-system/config.json"
    if not config_path.exists():
        config = {
            "version": 1,
            "sources": {
                "feishu_minutes": {"enabled": True},
                "viaim": {"enabled": True},
                "outlook_calendar": {"enabled": True}
            },
            "sensitivity_default": "confidential",
            "calendar_match": {
                "window_minutes": 30,
                "high_confidence": 70,
                "medium_confidence": 45
            }
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    run_log = vault / ".crm-system/run-log.md"
    write_if_missing(run_log, "# CRM System Run Log\n\n")
    write_if_missing(vault / ".crm-system/pending-confirmations.md", "# Pending Confirmations\n\n")
    write_if_missing(vault / ".crm-system/confirmation-log.md", "# Confirmation Log\n\n")

    print(json.dumps({
        "ok": True,
        "vault": str(vault),
        "message": "Personal CRM vault initialized.",
        "created_or_verified_dirs": dirs
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
