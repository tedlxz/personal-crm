# VIAIM 转写直归档自动化验证

## 验证结论

Codex Chrome 插件可以读取 `https://cloud.viaim.cn/cloud` 中已登录的 VIAIM 页面内容，并可操作页面：

- 可以读取录音列表。
- 可以按可见标题/时间定位录音，例如 `June 03, 14:13`。
- 可以切换到 `转写` tab。
- 可以读取完整逐句 transcript。
- 页面底部存在 `复制` 控件，但本次验证中点击后未能让自动化环境读取到剪贴板变化。

因此，推荐自动化方案是：

```text
选择录音 → 切换转写 tab → 直接从 DOM 抽取 transcript → Claude Code 整理 notes → 写入 Obsidian
```

而不是依赖：

```text
点击复制 → 读取剪贴板
```

## 已验证的页面结构

VIAIM 页面包含：

- 录音列表：标题、摘要、时间、地点、时长。
- 详情页 tabs：`摘要`、`转写`、`待办`、`思维导图`。
- 转写页：时间戳 + 原文逐句内容。
- 底部工具栏：`编辑`、`复制`、`查找`。

## 推荐链路

```text
VIAIM Chrome tab
  → 按时间找到目标录音
  → 切换到转写
  → DOM 抽取 transcript
  → 保存到 00_Inbox/VIAIM/Transcripts/
  → Claude Code 整理会议 notes
  → personal-obsidian-crm-archiver 更新 CRM
```

## 对飞书妙记方案的判断

音频上传飞书妙记仍可作为增强路径，但不应作为主链路：

```text
VIAIM 音频 → 下载 → 上传飞书妙记 → 等待生成 → 再读 transcript
```

这条链路多了下载、上传、等待、飞书权限和 UI 变化等不稳定因素。

更稳的第一版是：

```text
VIAIM transcript → Claude Code notes → Obsidian CRM
```

## 需要用户提供的信息

要真正写入 Obsidian，需要提供 vault 的绝对路径，例如：

```text
/Users/<name>/Documents/Obsidian/PersonalCRM
```

拿到路径后，Claude Code 可以自动：

1. 初始化 vault 目录和模板。
2. 保存 VIAIM transcript。
3. 生成会议 notes。
4. 更新联系人 CRM。
