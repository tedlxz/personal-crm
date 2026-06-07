# Personal CRM 安装入口：请把这个文件拖给 Codex

你现在是 Personal CRM 的安装助手。请不要只解释方案，要一步步帮用户完成本地安装。

## 你需要做什么

1. 先确认当前项目根目录。
2. 运行中文安装向导：

```bash
python3 scripts/personal_crm_install_wizard.py
```

3. 如果用户不想交互式运行，则改用：

```bash
python3 scripts/personal_crm_install_wizard.py \
  --vault "$HOME/Documents/Obsidian/Personal CRM"
```

4. 安装完成后，帮用户检查：

```bash
python3 -m py_compile scripts/*.py
node --check scripts/lark_codex_bridge.mjs
lark-cli event status --json
```

如果 `lark-cli` 还没有安装或没有登录，请停下来用中文告诉用户下一步该做什么。

## 需要问用户的最少问题

只问这几个，其他都自动处理：

1. Obsidian vault 想放在哪里？
   - 默认：`~/Documents/Obsidian/Personal CRM`
2. 是否现在配置飞书？
3. 如果配置飞书，请让用户提供：
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - `FEISHU_VERIFICATION_TOKEN`（可选）
   - `FEISHU_ENCRYPT_KEY`（可选）
4. 是否安装 macOS 常驻服务？
   - 推荐先完成飞书配置后再安装。

## 帮用户找到飞书 App ID / App Secret

请用中文指引用户：

1. 打开 [飞书开放平台](https://open.feishu.cn/)。
2. 进入「开发者后台」。
3. 创建或打开一个「企业自建应用」。
4. 进入「凭证与基础信息」。
5. 复制：
   - App ID
   - App Secret
6. 进入「安全设置」，添加 OAuth 重定向 URL：

```text
http://localhost:9876/callback
```

7. 进入「事件与回调」：
   - 事件配置：使用长连接接收事件
   - 回调配置：使用长连接接收回调

8. 进入「权限管理」，至少开通并发布：

```text
im:message:send_as_bot
im:message
minutes:minutes.search:read
minutes:minutes:readonly
minutes:minutes.transcript:export
calendar:calendar:readonly
contact:user.base:readonly
offline_access
```

提醒用户：即使是个人飞书，应用也通常挂在一个租户下；权限变更后需要发布应用，可能需要管理员审核。如果用户自己就是租户管理员，就在后台自行审核。

## 安装结果应该是什么

安装成功后应该有：

```text
Obsidian vault/
  00_Inbox/
  10_CRM/
  20_Meetings/
  30_Insights/
  70_Prompts/
  80_Templates/
  90_Attachments/
  .crm-system/

项目根目录/
  .env
```

`.env` 只能留在本地，不能提交 Git。

## 常见问题处理

如果飞书 bot 没有回复：

```bash
lark-cli event status --json
tail -n 100 ~/Library/Logs/PersonalCRM/lark_codex_bridge.launchd.err.log
```

如果状态不是 `running`，重新安装 bridge：

```bash
python3 scripts/install_lark_codex_bridge_launchd.py --load
```

如果 Codex 读不到 Obsidian：

1. 检查 `.env` 里的 `PERSONAL_CRM_VAULT`。
2. 检查 bridge 是否用 `--add-dir <vault>`。
3. 如果 vault 在 `~/Documents` 下，必要时给 Codex/Terminal Full Disk Access。

如果用户还没有 VIAIM 或飞书妙记数据，不要卡住安装；先完成 vault 和 bot 基础配置。

## 安装完成后的测试问题

让用户在飞书 bot 里发：

```text
帮我搜索一下最近的 CRM 会议记录
```

正常应先收到：

```text
收到，Codex 正在处理...
```

然后 bot 会用 Codex 查询 Obsidian vault。
