#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


HONORIFICS = ("总", "老师", "董", "博士", "先生", "女士", "经理", "主任")


def normalize_text(value):
    value = value or ""
    value = value.strip().lower()
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[，。、“”\"'：:；;（）()\[\]{}<>《》/\\|_-]", "", value)
    for honorific in HONORIFICS:
        if value.endswith(honorific.lower()):
            value = value[: -len(honorific)]
    return value


def read_contacts(vault):
    contacts_dir = vault / "10_CRM" / "Contacts"
    contacts = []
    if not contacts_dir.exists():
        return contacts
    for path in sorted(contacts_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        name = path.stem
        company = extract_field(text, "company") or extract_bullet_value(text, "公司")
        title = extract_field(text, "title") or extract_bullet_value(text, "Title")
        aliases = extract_aliases(text)
        contacts.append({
            "name": name,
            "path": str(path),
            "company": company,
            "title": title,
            "aliases": aliases,
            "normalized": normalize_text(name),
        })
    return contacts


def extract_field(text, field):
    match = re.search(rf"^{re.escape(field)}:\s*\"?([^\"\n]*)\"?", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def extract_bullet_value(text, label):
    match = re.search(rf"[-*]\s*{re.escape(label)}[：:]\s*(.+)", text)
    return match.group(1).strip() if match else ""


def extract_aliases(text):
    aliases = set()
    for label in ("别名", "微信", "WeChat", "alias", "aliases", "联系方式"):
        for match in re.finditer(rf"{label}[：:]\s*(.+)", text, re.IGNORECASE):
            for part in re.split(r"[,，/、;；\s]+", match.group(1)):
                part = part.strip()
                if part:
                    aliases.add(part)
    return sorted(aliases)


def score_contact(contact, context):
    score = 0
    reasons = []
    strong_identity = False
    haystack = normalize_text(" ".join([
        context.get("title", ""),
        context.get("transcript", ""),
        " ".join(context.get("participants", [])),
        " ".join(context.get("companies", [])),
    ]))

    name_norm = contact["normalized"]
    if name_norm and name_norm in haystack:
        score += 25
        reasons.append("transcript_or_title_exact_name")
        strong_identity = True

    for participant in context.get("participants", []):
        if normalize_text(participant) == name_norm and name_norm:
            score += 35
            reasons.append("calendar_or_input_participant_exact_name")
            strong_identity = True
            break

    for alias in contact["aliases"]:
        alias_norm = normalize_text(alias)
        if alias_norm and alias_norm in haystack:
            score += 20
            reasons.append(f"alias_match:{alias}")
            strong_identity = True
            break

    company_norm = normalize_text(contact.get("company", ""))
    if company_norm:
        input_companies = [normalize_text(c) for c in context.get("companies", [])]
        if company_norm in input_companies:
            score += 15
            reasons.append("company_exact_match")
        elif company_norm in haystack:
            score += 10
            reasons.append("company_text_match")

    fuzzy_points = 0 if strong_identity else fuzzy_name_points(name_norm, haystack, context.get("participants", []))
    if fuzzy_points:
        score += fuzzy_points
        reasons.append(f"weak_fuzzy_name_match:{fuzzy_points}")

    return score, reasons


def fuzzy_name_points(name_norm, haystack, participants):
    if len(name_norm) < 2:
        return 0
    if name_norm[:1] in haystack and len(name_norm) <= 3:
        return 8
    for participant in participants:
        participant_norm = normalize_text(participant)
        if not participant_norm:
            continue
        if participant_norm[:1] == name_norm[:1] and abs(len(participant_norm) - len(name_norm)) <= 1:
            return 12
    return 0


def decision(candidates):
    if not candidates:
        return "needs_user_confirmation"
    strong = [
        item for item in candidates
        if item["score"] >= 80 and any(
            reason in item["reasons"]
            for reason in ("calendar_or_input_participant_exact_name", "transcript_or_title_exact_name")
        )
    ]
    if strong:
        return "auto_archive"
    top = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    if runner_up and top["score"] - runner_up["score"] <= 10:
        return "needs_user_confirmation"
    if top["score"] >= 80:
        return "auto_archive"
    if top["score"] >= 60:
        return "needs_user_confirmation"
    return "needs_user_confirmation"


def load_transcript(path):
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--transcript-file", default="")
    parser.add_argument("--participant", action="append", default=[])
    parser.add_argument("--company", action="append", default=[])
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    vault = Path(args.vault).expanduser()
    context = {
        "title": args.title,
        "transcript": load_transcript(args.transcript_file),
        "participants": args.participant,
        "companies": args.company,
    }
    candidates = []
    for contact in read_contacts(vault):
        score, reasons = score_contact(contact, context)
        if score:
            candidates.append({
                "name": contact["name"],
                "path": contact["path"],
                "company": contact.get("company", ""),
                "title": contact.get("title", ""),
                "score": score,
                "reasons": reasons,
            })
    candidates.sort(key=lambda item: item["score"], reverse=True)
    print(json.dumps({
        "decision": decision(candidates),
        "candidates": candidates[: args.top],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
