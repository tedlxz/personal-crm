#!/usr/bin/env python3
import argparse
import os
import plistlib
import subprocess
from pathlib import Path


DEFAULT_LABEL = "com.personalcrm.feishu-bot"
DEFAULT_VAULT = "/Users/tedliu/Documents/Obsidian/Personal CRM"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--vault", default=DEFAULT_VAULT)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--python", default="/usr/bin/python3")
    parser.add_argument("--load", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    log_dir = Path.home() / "Library" / "Logs" / "PersonalCRM"
    log_dir.mkdir(parents=True, exist_ok=True)

    env = {
        "PATH": os.environ.get("PATH", ""),
        "PERSONAL_CRM_VAULT": str(Path(args.vault).expanduser().resolve()),
    }
    for key in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_VERIFICATION_TOKEN", "FEISHU_ENCRYPT_KEY"):
        value = os.environ.get(key, "")
        if value:
            env[key] = value

    plist = {
        "Label": args.label,
        "ProgramArguments": [
            args.python,
            str(repo / "scripts" / "feishu_bot_agent.py"),
            "--transport",
            "websocket",
        ],
        "WorkingDirectory": str(repo),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(log_dir / "feishu_bot_agent.launchd.out.log"),
        "StandardErrorPath": str(log_dir / "feishu_bot_agent.launchd.err.log"),
        "EnvironmentVariables": env,
    }

    plist_path = launch_agents / f"{args.label}.plist"
    with plist_path.open("wb") as f:
        plistlib.dump(plist, f)
    plist_path.chmod(0o600)

    print(f"Wrote {plist_path}")
    print(f"Logs: {log_dir}")
    print(f"Load: launchctl bootstrap gui/{os.getuid()} {plist_path}")
    print(f"Unload: launchctl bootout gui/{os.getuid()} {plist_path}")

    if args.load:
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(plist_path)], check=False)
        subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)], check=True)
        subprocess.run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{args.label}"], check=True)
        print("Loaded and started.")


if __name__ == "__main__":
    main()
