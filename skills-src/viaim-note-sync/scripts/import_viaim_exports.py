#!/usr/bin/env python3
import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"}
TEXT_EXTS = {".txt", ".md", ".docx", ".pdf"}


def safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in name).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True)
    parser.add_argument("--source-dir", required=True)
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    source = Path(args.source_dir).expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"source dir not found: {source}")

    audio_dir = vault / "00_Inbox/VIAIM/Audio"
    transcript_dir = vault / "00_Inbox/VIAIM/Transcripts"
    export_dir = vault / "00_Inbox/VIAIM/Exports"
    for d in (audio_dir, transcript_dir, export_dir):
        d.mkdir(parents=True, exist_ok=True)

    imported = []
    for item in source.iterdir():
        if not item.is_file():
            continue
        ext = item.suffix.lower()
        if ext in AUDIO_EXTS:
            dest_dir = audio_dir
        elif ext in TEXT_EXTS:
            dest_dir = transcript_dir
        else:
            dest_dir = export_dir
        dest = dest_dir / safe_name(item.name)
        if dest.exists():
            stem = dest.stem
            dest = dest.with_name(f"{stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}{dest.suffix}")
        shutil.copy2(item, dest)
        imported.append({"source": str(item), "dest": str(dest), "type": "audio" if ext in AUDIO_EXTS else "text" if ext in TEXT_EXTS else "export"})

    manifest = vault / "00_Inbox/VIAIM/Exports/import_manifest.json"
    manifest.write_text(json.dumps({
        "imported_at": datetime.now().isoformat(),
        "source_dir": str(source),
        "items": imported,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "count": len(imported), "manifest": str(manifest), "items": imported}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

