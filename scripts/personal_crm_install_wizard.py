#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_VAULT = Path.home() / "Documents" / "Obsidian" / "Personal CRM"


def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default or ""


def ask_yes_no(prompt, default=False):
    default_text = "Y/n" if default else "y/N"
    value = input(f"{prompt} [{default_text}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "是", "好", "可以"}


def run(cmd, cwd):
    print("\n正在执行：")
    print(" ".join(str(part) for part in cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def write_env(repo, values):
    env_path = repo / ".env"
    existing = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                existing[key.strip()] = value.strip()

    existing.update({key: value for key, value in values.items() if value})
    lines = [
        "# Personal CRM local config. Do not commit this file.",
        f"PERSONAL_CRM_VAULT={existing.get('PERSONAL_CRM_VAULT', '')}",
        f"FEISHU_APP_ID={existing.get('FEISHU_APP_ID', '')}",
        f"FEISHU_APP_SECRET={existing.get('FEISHU_APP_SECRET', '')}",
        f"FEISHU_VERIFICATION_TOKEN={existing.get('FEISHU_VERIFICATION_TOKEN', '')}",
        f"FEISHU_ENCRYPT_KEY={existing.get('FEISHU_ENCRYPT_KEY', '')}",
        "",
    ]
    env_path.write_text("\n".join(lines), encoding="utf-8")
    env_path.chmod(0o600)
    print(f"\n已写入本地配置：{env_path}")


def print_feishu_hint():
    print(
        """
飞书配置提示：

1. 打开飞书开放平台：https://open.feishu.cn/
2. 创建“企业自建应用”。
3. 在“凭证与基础信息”复制 App ID 和 App Secret。
4. 在“安全设置”添加重定向 URL：
   http://localhost:9876/callback
5. 在“事件与回调”里使用长连接接收事件/回调。
6. 至少开通这些权限后发布应用：
   - im:message:send_as_bot
   - im:message
   - minutes:minutes.search:read
   - minutes:minutes:readonly
   - minutes:minutes.transcript:export
   - calendar:calendar:readonly
   - contact:user.base:readonly
   - offline_access

如果你现在还没有 App ID / App Secret，可以先跳过。之后重新运行本安装向导即可。
"""
    )


def main():
    parser = argparse.ArgumentParser(description="Personal CRM 中文安装向导")
    parser.add_argument("--vault", default="")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--install-services", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    vault = Path(args.vault).expanduser() if args.vault else DEFAULT_VAULT

    print("\nPersonal CRM 安装向导")
    print("====================")
    print("这个向导会初始化 Obsidian vault，并把本地配置写到 .env。")
    print("敏感信息只保存在本机 .env，不会提交到 Git。\n")

    if not args.non_interactive:
        vault = Path(ask("Obsidian vault 路径", str(vault))).expanduser()

    vault = vault.resolve()
    run([sys.executable, str(repo / "scripts" / "setup_personal_crm_vault.py"), "--vault", str(vault)], repo)

    env_values = {"PERSONAL_CRM_VAULT": str(vault)}
    configure_feishu = False if args.non_interactive else ask_yes_no("现在配置飞书 App ID / App Secret 吗？", False)
    app_id = ""
    app_secret = ""
    if configure_feishu:
        print_feishu_hint()
        app_id = ask("FEISHU_APP_ID（例如 cli_xxx，可以留空稍后再填）")
        app_secret = ask("FEISHU_APP_SECRET（会写入本地 .env，可以留空稍后再填）")
        verification_token = ask("FEISHU_VERIFICATION_TOKEN（可选，没有就留空）")
        encrypt_key = ask("FEISHU_ENCRYPT_KEY（可选，没有就留空）")
        env_values.update({
            "FEISHU_APP_ID": app_id,
            "FEISHU_APP_SECRET": app_secret,
            "FEISHU_VERIFICATION_TOKEN": verification_token,
            "FEISHU_ENCRYPT_KEY": encrypt_key,
        })

    write_env(repo, env_values)

    install_services = args.install_services
    if not args.non_interactive:
        install_services = ask_yes_no("要安装 macOS 常驻服务吗？Feishu bot / Lark Codex bridge 会在后台保持在线", False)

    if install_services:
        run([sys.executable, str(repo / "scripts" / "install_lark_codex_bridge_launchd.py"), "--vault", str(vault), "--load"], repo)
        if app_id and app_secret:
            run([sys.executable, str(repo / "scripts" / "install_feishu_bot_agent_launchd.py"), "--vault", str(vault), "--load"], repo)
        else:
            print("已跳过 Feishu bot 后端服务：缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET。")

    print(
        f"""
安装完成。

下一步：

1. 打开 Obsidian，选择 Open folder as vault，路径：
   {vault}

2. 如果你配置了飞书，发送消息给 bot 测试：
   帮我搜索一下最近的 CRM 会议记录

3. 检查服务状态：
   lark-cli event status --json
   tail -n 100 ~/Library/Logs/PersonalCRM/lark_codex_bridge.launchd.err.log

4. 如果还没有配置飞书，重新运行：
   python3 scripts/personal_crm_install_wizard.py
"""
    )


if __name__ == "__main__":
    main()
