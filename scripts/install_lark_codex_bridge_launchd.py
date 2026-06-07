#!/usr/bin/env python3
import argparse
import os
import plistlib
import shutil
import subprocess
from pathlib import Path


DEFAULT_LABEL = "com.personalcrm.lark-codex-bridge"
DEFAULT_VAULT = "/Users/tedliu/Documents/Obsidian/Personal CRM"


def find_binary(name, fallback):
    return shutil.which(name) or fallback


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--vault", default=DEFAULT_VAULT)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--node", default=find_binary("node", "/opt/homebrew/bin/node"))
    parser.add_argument("--codex", default=find_binary("codex", "codex"))
    parser.add_argument("--lark-cli", default=find_binary("lark-cli", "lark-cli"))
    parser.add_argument("--bridge-home", default=str(Path.home() / ".personalcrm"))
    parser.add_argument("--timeout-ms", default="300000")
    parser.add_argument("--load", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    vault = Path(args.vault).expanduser().resolve()
    bridge_home = Path(args.bridge_home).expanduser().resolve()
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    log_dir = Path.home() / "Library" / "Logs" / "PersonalCRM"

    bridge_home.mkdir(parents=True, exist_ok=True)
    launch_agents.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    source = repo / "scripts" / "lark_codex_bridge.mjs"
    target = bridge_home / "lark_codex_bridge.mjs"
    shutil.copy2(source, target)
    target.chmod(0o700)

    stable_paths = [
        str(Path(args.node).expanduser().resolve().parent) if "/" in args.node else "",
        str(Path(args.codex).expanduser().resolve().parent) if "/" in args.codex else "",
        str(Path(args.lark_cli).expanduser().resolve().parent) if "/" in args.lark_cli else "",
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ]
    path = ":".join(dict.fromkeys(p for p in stable_paths if p))

    env = {
        "HOME": str(Path.home()),
        "PATH": path,
        "LARK_CODEX_BRIDGE_CWD": str(bridge_home),
        "CODEX_WORKDIR": str(repo),
        "PERSONAL_CRM_VAULT": str(vault),
        "LARK_CODEX_SANDBOX": "workspace-write",
        "LARK_CODEX_TIMEOUT_MS": str(args.timeout_ms),
        "CODEX_BIN": args.codex,
        "LARK_CLI_BIN": args.lark_cli,
    }

    plist = {
        "Label": args.label,
        "ProgramArguments": [
            args.node,
            str(target),
        ],
        "WorkingDirectory": str(bridge_home),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 10,
        "StandardOutPath": str(log_dir / "lark_codex_bridge.launchd.out.log"),
        "StandardErrorPath": str(log_dir / "lark_codex_bridge.launchd.err.log"),
        "EnvironmentVariables": env,
    }

    plist_path = launch_agents / f"{args.label}.plist"
    with plist_path.open("wb") as f:
        plistlib.dump(plist, f)
    plist_path.chmod(0o600)

    print(f"Wrote {plist_path}")
    print(f"Copied bridge script to {target}")
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
