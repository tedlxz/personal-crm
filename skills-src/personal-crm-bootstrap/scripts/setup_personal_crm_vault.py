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
title: ""
participants: []
contacts: []
companies: []
source: ""
source_link: ""
audio_file: ""
transcript_file: ""
calendar_event_id: ""
match_confidence: ""
sensitivity: external_ok
crm_updated: false
tags: [meeting]
---

# {{date}} {{title}}

## 会议基本信息

- 时间：
- 地点/形式：
- 参与人：
- 来源：飞书妙记 / VIAIM / 讯飞转写 / 手动记录 / 音频
- 关联联系人：
- 关联公司：
- Outlook 日历匹配：
- 匹配置信度：

## 一句话摘要


## 关键讨论

1. 

## 对方表达的需求/关切

- 

## 使用者表达的观点/承诺

- 

## 新增背景信息

- 

## 行动项

- [ ] 负责人：事项，截止时间：

## 应更新到 CRM 的内容

- 联系人：
- 需要新增/更新的信息：

## 可沉淀为 insight 的内容

- 

## 原始转写摘录

> 只保留关键原文片段。全文 transcript 放附件、源链接或 source file。
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
        "80_Templates",
        "90_Attachments/Audio",
        "90_Attachments/Transcripts",
        ".crm-system",
    ]
    for rel in dirs:
        (vault / rel).mkdir(parents=True, exist_ok=True)

    write_if_missing(vault / "80_Templates/crm-contact-template.md", CONTACT_TEMPLATE)
    write_if_missing(vault / "80_Templates/meeting-note-template.md", MEETING_TEMPLATE)
    write_if_missing(vault / "80_Templates/company-template.md", COMPANY_TEMPLATE)
    write_if_missing(vault / "80_Templates/weekly-review-template.md", WEEKLY_TEMPLATE)

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

    print(json.dumps({
        "ok": True,
        "vault": str(vault),
        "message": "Personal CRM vault initialized.",
        "created_or_verified_dirs": dirs
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

