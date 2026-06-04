---
name: viaim-note-sync
description: Sync VIAIM/iFLYTEK meeting notes, transcripts, and audio from the VIAIM web platform into a personal Obsidian CRM inbox. Use when asked to pull notes from VIAIM, export VIAIM transcripts, download VIAIM audio, batch process VIAIM exports, or optionally upload VIAIM audio into Feishu Minutes through browser automation.
---

# VIAIM Note Sync

Use this skill for VIAIM / iFLYTEK web-platform notes.

## Goal

Get new VIAIM note data into:

```text
00_Inbox/VIAIM/Transcripts/
00_Inbox/VIAIM/Audio/
00_Inbox/VIAIM/Exports/
```

Then hand off to `personal-outlook-calendar-matcher` and `personal-obsidian-crm-archiver`.

## Strategy

Prefer in this order:

1. **DOM transcript extraction**: after user logs in, select the target note, switch to `转写`, and read the visible transcript text from the page DOM.
2. **Copy button**: click the bottom `复制` control and read clipboard if clipboard access works.
3. **Direct transcript export/import**: use VIAIM's export feature or batch export, then import files.
4. **Network API discovery**: inspect authenticated web requests for notes/transcript/audio endpoints, then script them.
5. **Audio-to-Feishu upload**: only if the user specifically needs Feishu Minutes processing.

## Why transcript-first

If VIAIM already has transcript text, send that directly to CRM. This is shorter and more reliable than:

```text
VIAIM audio -> Feishu upload -> Feishu transcription -> CRM
```

Use Feishu upload only when Feishu's Minutes summarization is required.

## Browser automation rules

- Use the user's logged-in browser session.
- Do not collect or store account passwords.
- Download only the user's own notes/audio.
- Save all downloads into the vault inbox.
- Record source URL and export time in metadata.

## Observed VIAIM web workflow

The VIAIM cloud page at `https://cloud.viaim.cn/cloud` exposes enough DOM for Chrome automation:

1. The recording list contains visible note title, summary, recorded time, location, and duration.
2. A target note can be selected by visible time/title, for example `June 03, 14:13`.
3. The detail panel has tabs: `摘要`, `转写`, `待办`, `思维导图`.
4. In `转写`, the full timestamped transcript appears in the DOM.
5. The bottom footer contains `编辑`, `复制`, `查找`.

Prefer extracting transcript directly from DOM because the `复制` control may not update the automation-visible clipboard in every browser/plugin environment.

### DOM extraction recipe

After claiming the logged-in Chrome tab:

```js
await tab.playwright.getByText(targetVisibleTitle, { exact: true }).click();
await tab.playwright.waitForTimeout(1000);
await tab.cua.click({ x: 910, y: 218 }); // fallback coordinate for 转写 tab on a 2560px-wide window
await tab.playwright.waitForTimeout(1000);

const transcript = await tab.playwright.evaluate(() => {
  const candidates = [...document.querySelectorAll('*')].map((el) => {
    const cls = String(el.className || '');
    const text = (el.innerText || el.textContent || '').trim();
    const r = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return { cls, text, visible: r.width > 0 && r.height > 0 && style.display !== 'none' && style.visibility !== 'hidden' };
  });
  const detail = candidates.find(e =>
    e.cls.includes('detail-content') &&
    e.text.includes('00:00') &&
    (e.text.includes('编辑') || e.text.includes('复制') || e.text.length > 1000)
  );
  let text = detail ? detail.text : document.body.innerText;
  const start = text.indexOf('00:00');
  const endMarkers = ['编辑\n复制\n查找', '新对话\nviaim AI'];
  let end = text.length;
  for (const marker of endMarkers) {
    const idx = text.indexOf(marker, start > -1 ? start : 0);
    if (idx > -1) end = Math.min(end, idx);
  }
  return start > -1 ? text.slice(start, end).trim() : text.trim();
});
```

Save the transcript to:

```text
00_Inbox/VIAIM/Transcripts/YYYY-MM-DD_HH-mm_<safe-title>.md
```

Then hand it to `personal-obsidian-crm-archiver`.

## Import existing downloads

If files have already been exported, run:

```bash
python <skill_path>/scripts/import_viaim_exports.py \
  --vault "<absolute_vault_path>" \
  --source-dir "<download_or_export_folder>"
```

## Optional Feishu upload path

If uploading VIAIM audio to Feishu Minutes is required:

1. Download audio to `00_Inbox/VIAIM/Audio`.
2. Open Feishu Minutes upload page in a logged-in browser.
3. Upload the local audio file through the product UI.
4. Wait for Minutes generation.
5. Pass generated Minutes link to `personal-feishu-minutes-reader`.

If the UI changes or automation fails, keep the audio and transcript in Obsidian; do not block CRM archiving.
