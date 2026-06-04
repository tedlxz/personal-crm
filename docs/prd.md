# PRD：个人 CRM + 录音管理系统

## 1. 产品定位

本产品是一个本地优先的个人关系记忆系统。它通过 Claude Code 自动处理飞书妙记、VIAIM/讯飞听见、可用日历来源和 Obsidian vault，实现联系人 CRM、会议纪要、公司档案、待办和洞察的持续更新。

## 2. 用户与系统角色

| 角色 | 描述 |
| --- | --- |
| 最终用户 | 查看 Obsidian，发出查询或归档指令 |
| Claude Code | 执行初始化、读取数据源、匹配日历、更新 Markdown |
| Obsidian | 本地知识库前端 |
| 飞书 | 线下会议记录和妙记来源 |
| VIAIM / 讯飞听见 | 线上会议 transcript 和音频来源 |
| Calendar Source | Outlook / Gmail / Google Calendar / `.ics`，用于提供会议上下文 |

## 3. MVP 范围

### F1. Vault 自动初始化

Claude Code 可运行脚本自动创建目录、模板和配置文件。

验收：

- 用户只提供 vault 路径。
- 脚本创建 `00_Inbox`、`10_CRM`、`20_Meetings`、`30_Insights`、`80_Templates`、`90_Attachments`。
- 模板自动写入。

### F2. VIAIM Notes 同步

系统能从 VIAIM 网页端或导出文件中获取 transcript 和音频。

验收：

- transcript 保存到 `00_Inbox/VIAIM/Transcripts`。
- audio 保存到 `00_Inbox/VIAIM/Audio`。
- 每条 note 生成 metadata，包含标题、时间、来源。

### F3. 飞书妙记读取

系统能通过用户授权读取已有妙记 transcript，或在权限不足时接受用户导出的 transcript。

验收：

- 输入飞书妙记链接或 token，返回 transcript 或明确 fallback。
- source link 保存在会议文件。

### F4. 日历匹配

系统能根据录音/转写时间匹配日历 block。

验收：

- 输出匹配事件、参与人、公司、置信度。
- 低置信度时不自动写 CRM，先请求确认。
- 优先使用工作 Outlook connector。
- Outlook 不可用时，可从 Gmail 会议邀请或 `.ics` 附件解析日历事件。
- 对外预约会议时，可用个人 Gmail/Google Calendar 作为 Codex 可读入口，同时邀请工作邮箱以同步到工作 Outlook。

### F5. Obsidian CRM 归档

系统能自动更新联系人、公司和会议文件。

验收：

- 新联系人自动创建。
- 老联系人追加互动记录。
- 每次会议单独建会议文件。
- 联系人文件和会议文件互相链接。

## 4. 数据结构

### Contact

```yaml
type: crm_contact
name: ""
title: ""
company: ""
first_met_date: ""
first_met_place: ""
introduced_by: ""
last_contact_date: ""
next_follow_up_date: ""
sensitivity: external_ok
```

### Meeting

```yaml
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
```

### VIAIM Note

```yaml
type: viaim_note
title: ""
recorded_at: ""
source_url: ""
audio_file: ""
transcript_file: ""
sync_status: pending
```

## 5. 自动化路线

### 路线 A：VIAIM transcript 直归档

```text
VIAIM Note → transcript → calendar 匹配 → Obsidian CRM
```

这是默认路线。

### 路线 B：VIAIM 音频上传飞书妙记

```text
VIAIM Note → audio → 飞书妙记上传 → transcript → Obsidian CRM
```

这是可选增强路线，依赖浏览器自动化或 RPA。

### 路线 C：独立 ASR

```text
VIAIM audio → ASR → transcript → Obsidian CRM
```

当飞书上传链路不稳定时使用。

## 6. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| VIAIM 无公开 API | 无法纯脚本同步 | 用浏览器自动化导出或监听网页请求 |
| 飞书音频上传无稳定公开 API | 不能纯 API 生成妙记 | 用飞书产品 UI/RPA，或跳过飞书直接归档 VIAIM transcript |
| Outlook 授权失败 | 会议匹配弱 | 改用 Gmail 会议邀请、Google Calendar、`.ics` 导出或当天日程文本 |
| 同时段多场会议 | 归档错误 | 置信度机制和人工确认 |
| transcript 太长 | CRM 文件膨胀 | 原文入附件，联系人只写摘要和链接 |

## 7. 里程碑

| 阶段 | 目标 |
| --- | --- |
| M1 | Claude Code 自动初始化 vault |
| M2 | 手动输入 transcript 可归档 CRM |
| M3 | 日历匹配可用，支持 Outlook 优先、Gmail/ICS 兜底 |
| M4 | VIAIM Notes 可自动或半自动同步 |
| M5 | 飞书妙记读取可用 |
| M6 | 可选实现 VIAIM 音频自动上传飞书妙记 |
