#!/usr/bin/env python3
import argparse
import os
import plistlib
from pathlib import Path


DEFAULT_PROMPT = """Run crm-housekeeping-agent for the Personal CRM vault.
Process today's Feishu Minutes and VIAIM transcripts.
Use calendar matching when available.
Create detailed Markdown notes before CRM updates.
Do not update contacts on low confidence; write pending questions to .crm-system/pending-confirmations.md.
Append an audit entry to .crm-system/run-log.md.
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True)
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--time", default="20:30")
    parser.add_argument("--label", default="com.personalcrm.housekeeping")
    parser.add_argument("--codex-command", default="codex")
    args = parser.parse_args()

    hour, minute = [int(part) for part in args.time.split(":", 1)]
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    prompt_path = Path(args.repo) / ".crm-housekeeping-prompt.txt"
    prompt_path.write_text(DEFAULT_PROMPT, encoding="utf-8")

    plist = {
        "Label": args.label,
        "ProgramArguments": [
            args.codex_command,
            "exec",
            "--cwd",
            str(Path(args.repo).resolve()),
            "--",
            f"{DEFAULT_PROMPT}\nVault path: {Path(args.vault).expanduser().resolve()}",
        ],
        "StartCalendarInterval": {
            "Hour": hour,
            "Minute": minute,
        },
        "StandardOutPath": str(Path(args.repo) / ".crm-system-housekeeping.out.log"),
        "StandardErrorPath": str(Path(args.repo) / ".crm-system-housekeeping.err.log"),
        "WorkingDirectory": str(Path(args.repo).resolve()),
        "EnvironmentVariables": {
            "PATH": os.environ.get("PATH", ""),
        },
    }

    plist_path = launch_agents / f"{args.label}.plist"
    with plist_path.open("wb") as f:
        plistlib.dump(plist, f)

    print(f"Wrote {plist_path}")
    print(f"Load with: launchctl load {plist_path}")
    print(f"Unload with: launchctl unload {plist_path}")


if __name__ == "__main__":
    main()
