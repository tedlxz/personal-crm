# Personal CRM 安装入口：请把这个文件拖给 Codex

如果另一个中文文件名在你的系统里显示乱码，请使用这个文件。内容和 `START_HERE_拖给Codex安装.md` 的用途相同。

## Codex 的任务

你现在是 Personal CRM 的安装助手。请不要只解释方案，要一步步帮用户完成本地安装。

请先运行：

```bash
python3 scripts/personal_crm_install_wizard.py
```

如果用户希望少交互，则运行：

```bash
python3 scripts/personal_crm_install_wizard.py \
  --vault "$HOME/Documents/Obsidian/Personal CRM"
```

## 只问用户这些问题

1. Obsidian vault 想放在哪里？
   - 默认：`~/Documents/Obsidian/Personal CRM`
2. 是否现在配置飞书？
3. 如果配置飞书，请让用户提供：
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - `FEISHU_VERIFICATION_TOKEN`（可选）
   - `FEISHU_ENCRYPT_KEY`（可选）
4. 是否安装 macOS 常驻服务？

## 飞书 App ID / App Secret 在哪里

请用中文指引用户：

1. 打开飞书开放平台：https://open.feishu.cn/
2. 进入「开发者后台」。
3. 创建或打开「企业自建应用」。
4. 进入「凭证与基础信息」复制 App ID 和 App Secret。
5. 进入「安全设置」，添加 OAuth 重定向 URL：

```text
http://localhost:9876/callback
```

6. 进入「事件与回调」：
   - 事件配置：使用长连接接收事件
   - 回调配置：使用长连接接收回调

7. 进入「权限管理」，至少开通并发布：

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

提醒用户：权限变更后需要发布应用，可能需要管理员审核。

## 安装完成后检查

```bash
python3 -m py_compile scripts/*.py
node --check scripts/lark_codex_bridge.mjs
lark-cli event status --json
```

如果飞书 bot 没有回复：

```bash
lark-cli event status --json
tail -n 100 ~/Library/Logs/PersonalCRM/lark_codex_bridge.launchd.err.log
```

如果 Codex 读不到 Obsidian：

1. 检查 `.env` 里的 `PERSONAL_CRM_VAULT`。
2. 检查 bridge 是否用 `--add-dir <vault>`。
3. 如果 vault 在 `~/Documents` 下，必要时给 Codex/Terminal Full Disk Access。
