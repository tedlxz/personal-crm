#!/usr/bin/env node
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname, "..");

const config = {
  larkCli: process.env.LARK_CLI_BIN || "lark-cli",
  codexBin: process.env.CODEX_BIN || "codex",
  bridgeCwd: resolve(process.env.LARK_CODEX_BRIDGE_CWD || rootDir),
  workdir: resolve(process.env.CODEX_WORKDIR || "/Users/tedliu/Documents/Codex/2026-06-03/files-mentioned-by-the-user-june/outputs/Personal-CRM"),
  vaultDir: resolve(process.env.PERSONAL_CRM_VAULT || "/Users/tedliu/Documents/Obsidian/Personal CRM"),
  sandbox: process.env.LARK_CODEX_SANDBOX || "workspace-write",
  trigger: process.env.LARK_CODEX_TRIGGER || "/codex",
  maxReplyChars: Number(process.env.LARK_CODEX_MAX_REPLY_CHARS || 12000),
  commandTimeoutMs: Number(process.env.LARK_CODEX_TIMEOUT_MS || 300000),
  sendAs: process.env.LARK_CODEX_SEND_AS || "bot",
  eventAs: process.env.LARK_CODEX_EVENT_AS || "bot",
};

const seen = new Set();
const queue = [];
let busy = false;
let shuttingDown = false;
let consumer = null;

function log(...args) {
  console.error(new Date().toISOString(), ...args);
}

function remember(id) {
  if (!id) return false;
  if (seen.has(id)) return true;
  seen.add(id);
  if (seen.size > 1000) {
    const first = seen.values().next().value;
    seen.delete(first);
  }
  return false;
}

function shouldHandle(event) {
  const text = String(event.content || "").trim();
  if (!text) return { ok: false };

  if (event.chat_type === "p2p") {
    return { ok: true, prompt: text };
  }

  if (text === config.trigger) {
    return { ok: true, prompt: "打个招呼，并简短说明你是 Codex，可以帮我处理代码、文档和飞书任务。" };
  }

  if (text.startsWith(`${config.trigger} `)) {
    return { ok: true, prompt: text.slice(config.trigger.length).trim() };
  }

  return { ok: false };
}

function runCommand(cmd, args, options = {}) {
  return new Promise((resolvePromise) => {
    const child = spawn(cmd, args, {
      cwd: options.cwd || config.bridgeCwd,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    const timeoutMs = options.timeoutMs || config.commandTimeoutMs;
    const timer = timeoutMs > 0
      ? setTimeout(() => {
          stderr += `\nCommand timed out after ${timeoutMs}ms.`;
          child.kill("SIGTERM");
        }, timeoutMs)
      : null;

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", (error) => {
      resolvePromise({ ok: false, code: -1, stdout, stderr: String(error) });
    });
    child.on("close", (code) => {
      if (timer) clearTimeout(timer);
      resolvePromise({ ok: code === 0, code, stdout, stderr });
    });
  });
}

async function sendMessage(chatId, text) {
  const clipped = text.length > config.maxReplyChars
    ? `${text.slice(0, config.maxReplyChars)}\n\n[回复过长，已截断]`
    : text;

  const result = await runCommand(config.larkCli, [
    "im",
    "+messages-send",
    "--as",
    config.sendAs,
    "--chat-id",
    chatId,
    "--text",
    clipped,
  ]);

  if (!result.ok) {
    log("send failed", result.code, result.stderr || result.stdout);
  }
}

async function runCodex(prompt) {
  const enrichedPrompt = [
    "你是 Personal CRM 的飞书 bot 后端 agent。",
    `Obsidian vault 路径：${config.vaultDir}`,
    "回答用户问题时，优先搜索并引用这个 Obsidian vault 里的 CRM、会议纪要和 transcript。",
    "如果 vault 里没有足够信息，再使用 web search 或明确说明缺少证据。",
    "回复要简洁，但需要说明信息来源：来自 Obsidian、来自 web，或两者都有。",
    "",
    "用户问题：",
    prompt,
  ].join("\n");

  const args = [
    "exec",
    "--skip-git-repo-check",
    "--sandbox",
    config.sandbox,
    "-C",
    config.workdir,
    "--add-dir",
    config.vaultDir,
    enrichedPrompt,
  ];

  const result = await runCommand(config.codexBin, args, { cwd: config.bridgeCwd });
  if (result.ok) return result.stdout.trim() || "Codex 已完成，但没有返回文本。";

  const detail = (result.stderr || result.stdout || "").trim();
  return `Codex 执行失败，退出码 ${result.code}。\n${detail.slice(0, 4000)}`;
}

async function handleEvent(event) {
  if (remember(event.event_id || event.message_id)) return;

  const decision = shouldHandle(event);
  if (!decision.ok) return;

  log("handling", {
    chat_id: event.chat_id,
    chat_type: event.chat_type,
    message_id: event.message_id,
  });

  await sendMessage(event.chat_id, "收到，Codex 正在处理...");
  const answer = await runCodex(decision.prompt);
  await sendMessage(event.chat_id, answer || "Codex 没有生成回复。");
}

function pumpQueue() {
  if (busy) return;
  const event = queue.shift();
  if (!event) return;
  busy = true;
  handleEvent(event)
    .catch((error) => log("handler error", error))
    .finally(() => {
      busy = false;
      pumpQueue();
    });
}

function start() {
  mkdirSync(config.bridgeCwd, { recursive: true });
  mkdirSync(resolve(rootDir, "work"), { recursive: true });

  log("starting lark-codex bridge", {
    workdir: config.workdir,
    vaultDir: config.vaultDir,
    bridgeCwd: config.bridgeCwd,
    sandbox: config.sandbox,
    trigger: config.trigger,
    commandTimeoutMs: config.commandTimeoutMs,
  });

  consumer = spawn(config.larkCli, [
    "event",
    "consume",
    "im.message.receive_v1",
    "--as",
    config.eventAs,
  ], {
    cwd: config.bridgeCwd,
    env: process.env,
    stdio: ["pipe", "pipe", "pipe"],
  });

  consumer.stdin.write("\n");

  let buffer = "";
  consumer.stdout.on("data", (chunk) => {
    buffer += chunk.toString();
    let index;
    while ((index = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, index).trim();
      buffer = buffer.slice(index + 1);
      if (!line) continue;
      try {
        const event = JSON.parse(line);
        queue.push(event);
        pumpQueue();
      } catch {
        log("non-json stdout", line);
      }
    }
  });

  consumer.stderr.on("data", (chunk) => {
    for (const line of chunk.toString().split(/\r?\n/)) {
      if (line.trim()) log("[lark-cli]", line);
    }
  });

  consumer.on("close", (code) => {
    log("event consumer exited", code);
    consumer = null;
    if (shuttingDown) {
      process.exit(code || 0);
      return;
    }
    log("restarting event consumer in 5s");
    setTimeout(start, 5000).unref();
  });

}

function shutdown() {
  shuttingDown = true;
  log("shutting down");
  if (consumer) consumer.kill("SIGTERM");
  setTimeout(() => process.exit(0), 1500).unref();
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

start();
