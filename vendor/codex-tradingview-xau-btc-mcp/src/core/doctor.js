import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { execFileSync, execSync } from "node:child_process";
import http from "node:http";
import { healthCheck } from "./health.js";

function ok(name, details = {}) {
  return { name, ok: true, ...details };
}

function fail(name, error, details = {}) {
  return { name, ok: false, error: String(error?.message || error), ...details };
}

function commandExists(command) {
  try {
    const cmd = process.platform === "win32" ? "where" : "which";
    execFileSync(cmd, [command], { timeout: 3000, stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

function codexCliCandidates() {
  const localAppData = process.env.LOCALAPPDATA || "";
  const appDataCli = join(localAppData, "OpenAI", "Codex", "bin", "codex.exe");
  return [
    process.env.CODEX_CLI_PATH,
    appDataCli,
    "codex",
  ].filter(Boolean);
}

function codexHomeCandidates() {
  const userProfile = process.env.USERPROFILE || process.env.HOME || "";
  return [
    process.env.CODEX_HOME,
    userProfile ? join(userProfile, ".codex") : null,
  ].filter(Boolean);
}

function configHasTradingViewMcp(codexHome) {
  const configPath = join(codexHome, "config.toml");
  if (!existsSync(configPath)) return null;
  const content = readFileSync(configPath, "utf8");
  return /\[mcp_servers\.tradingview\]/i.test(content)
    ? { ok: true, source: "config_toml", config_path: configPath }
    : { ok: false, source: "config_toml", config_path: configPath };
}

function detectCodexCli() {
  for (const cli of codexCliCandidates()) {
    try {
      const env = { ...process.env };
      if (cli !== "codex") {
        env.PATH = `${dirname(cli)};${env.PATH || ""}`;
      }
      const output = execFileSync(cli, ["--version"], { timeout: 7000, env }).toString().trim();
      return { ok: true, command: cli, version: output };
    } catch {}
  }
  return { ok: false };
}

function detectMcpRegistered() {
  const cli = detectCodexCli();
  for (const codexHome of codexHomeCandidates()) {
    if (cli.ok) {
      try {
        const env = { ...process.env, CODEX_HOME: codexHome };
        if (cli.command !== "codex") {
          env.PATH = `${dirname(cli.command)};${env.PATH || ""}`;
        }
        const output = execFileSync(cli.command, ["mcp", "list"], { timeout: 10000, env }).toString();
        if (/tradingview/i.test(output)) {
          return ok("mcp_registered", {
            source: "codex_cli",
            codex_cli: cli.command,
            codex_home: codexHome,
            output: output.trim(),
          });
        }
      } catch {}
    }

    const config = configHasTradingViewMcp(codexHome);
    if (config?.ok) {
      return ok("mcp_registered", {
        ...config,
        codex_home: codexHome,
        note: "Verified directly from config.toml because the WindowsApps codex launcher can be inaccessible from shell.",
      });
    }
  }

  return fail("mcp_registered", "No tradingview MCP entry found via Codex CLI or config.toml");
}

function cdpVersion(host, port) {
  return new Promise((resolve) => {
    const req = http.get(`http://${host}:${port}/json/version`, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          resolve({ ok: true, statusCode: res.statusCode, data: JSON.parse(data) });
        } catch {
          resolve({ ok: true, statusCode: res.statusCode, data: null });
        }
      });
    });
    req.setTimeout(1000, () => {
      req.destroy();
      resolve({ ok: false, error: "timeout" });
    });
    req.on("error", (err) => resolve({ ok: false, error: err.message }));
  });
}

function tradingViewInstallCandidates() {
  const local = process.env.LOCALAPPDATA || "";
  const programFiles = process.env.PROGRAMFILES || "C:\\Program Files";
  return [
    process.env.TRADINGVIEW_EXE_PATH,
    join(local, "Programs", "TradingView", "TradingView.exe"),
    join(local, "TradingView", "TradingView.exe"),
    join(programFiles, "TradingView", "TradingView.exe"),
  ].filter(Boolean);
}

function isTradingViewRunning() {
  if (process.platform !== "win32") return null;
  try {
    const output = execSync('tasklist /FI "IMAGENAME eq TradingView.exe" /NH', { timeout: 3000 }).toString();
    return /TradingView\.exe/i.test(output);
  } catch {
    try {
      execSync('powershell.exe -NoProfile -Command "if (Get-Process TradingView -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"', { timeout: 3000, stdio: "ignore" });
      return true;
    } catch {
      return false;
    }
  }
}

export async function runDoctor({ host = process.env.TRADINGVIEW_CDP_HOST || "127.0.0.1", port = Number(process.env.TRADINGVIEW_CDP_PORT || 9222) } = {}) {
  const checks = [];

  checks.push(ok("node_version", { version: process.version, supported: Number(process.versions.node.split(".")[0]) >= 18 }));
  checks.push(existsSync(join(process.cwd(), "node_modules")) ? ok("npm_install", { node_modules: true }) : fail("npm_install", "node_modules missing; run npm install"));
  checks.push(existsSync(join(process.cwd(), "rules.json")) || existsSync(join(process.cwd(), "rules.xau-btc.json")) ? ok("rules_file") : fail("rules_file", "No rules.json or rules.xau-btc.json found"));
  const codexCli = detectCodexCli();
  checks.push(codexCli.ok ? ok("codex_cli", codexCli) : commandExists("codex") ? ok("codex_cli") : fail("codex_cli", "Codex CLI not found"));
  checks.push(detectMcpRegistered());

  const candidates = tradingViewInstallCandidates();
  const foundPath = candidates.find((p) => existsSync(p));
  checks.push(foundPath ? ok("tradingview_installed", { path: foundPath }) : fail("tradingview_installed", "TradingView.exe not found in common Windows locations", { candidates }));

  const running = isTradingViewRunning();
  checks.push(running === null ? ok("tradingview_running", { skipped: "non-windows" }) : running ? ok("tradingview_running") : fail("tradingview_running", "TradingView.exe is not running"));

  const cdp = await cdpVersion(host, port);
  checks.push(cdp.ok ? ok("cdp_port", { host, port, version: cdp.data }) : fail("cdp_port", cdp.error, { host, port }));

  if (cdp.ok) {
    try {
      checks.push(ok("tv_health_check", await healthCheck()));
    } catch (err) {
      checks.push(fail("tv_health_check", err));
    }
  } else {
    checks.push(fail("tv_health_check", "Skipped because CDP port is unavailable"));
  }

  const required = ["node_version", "npm_install", "rules_file", "cdp_port", "tv_health_check"];
  const ready = required.every((name) => checks.find((c) => c.name === name)?.ok);

  return {
    success: true,
    ready,
    host,
    port,
    checks,
    next_actions: ready
      ? ["Codex can use tv_health_check and session_start.", "Verify Paper Trading mode before any order."]
      : ["Run npm install if needed.", "Launch TradingView Desktop with CDP.", "Run npm run tv -- status, then npm run tv -- doctor."],
  };
}
