import * as vscode from "vscode";
import { spawn } from "child_process";

interface CompressResponse {
    original: string;
    compressed: string;
    strategy: string;
    classified_as: string | null;
    warning: string | null;
    tokens: {
        encoding: string;
        original: number;
        compressed: number;
        saved: number;
        reduction: number;
    };
    rules_applied: Array<{ id: string; category: string; before: string; after: string }>;
}

let statusBar: vscode.StatusBarItem | undefined;

export function activate(context: vscode.ExtensionContext) {
    statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBar.command = "tokensqueeze.compress";
    context.subscriptions.push(statusBar);

    context.subscriptions.push(
        vscode.commands.registerCommand("tokensqueeze.compress", () => compressSelection(false)),
        vscode.commands.registerCommand("tokensqueeze.explain", () => compressSelection(true)),
        vscode.commands.registerCommand("tokensqueeze.toggleStatusBar", toggleStatusBar),
        vscode.window.onDidChangeTextEditorSelection(updateStatusBar),
        vscode.workspace.onDidChangeConfiguration((e) => {
            if (e.affectsConfiguration("tokensqueeze")) {
                updateStatusBar();
            }
        })
    );

    updateStatusBar();
}

export function deactivate() {
    statusBar?.dispose();
}

function getConfig() {
    const c = vscode.workspace.getConfiguration("tokensqueeze");
    return {
        pythonPath: c.get<string>("pythonPath", "python"),
        strategy: c.get<string>("strategy", "auto"),
        encoding: c.get<string>("encoding", "cl100k_base"),
        statusBarEnabled: c.get<boolean>("statusBar", true),
    };
}

async function compressSelection(showExplain: boolean) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage("TokenSqueeze: open an editor first.");
        return;
    }
    const selection = editor.selection;
    const text = editor.document.getText(selection);
    if (!text) {
        vscode.window.showWarningMessage("TokenSqueeze: select text to compress.");
        return;
    }

    try {
        const result = await runCli(text);
        if (showExplain) {
            await openExplainView(result);
        }
        await editor.edit((edit) => edit.replace(selection, result.compressed));
        const pct = (result.tokens.reduction * 100).toFixed(1);
        const msg = `TokenSqueeze: ${result.tokens.original} → ${result.tokens.compressed} tokens (-${pct}%) [${result.strategy}]`;
        if (result.warning) {
            vscode.window.showWarningMessage(`${msg} — ${result.warning}`);
        } else {
            vscode.window.showInformationMessage(msg);
        }
    } catch (err: any) {
        vscode.window.showErrorMessage(`TokenSqueeze failed: ${err?.message ?? err}`);
    }
}

function runCli(text: string): Promise<CompressResponse> {
    const cfg = getConfig();
    return new Promise((resolve, reject) => {
        const proc = spawn(
            cfg.pythonPath,
            [
                "-m",
                "tokensqueeze.cli",
                "--json",
                "--strategy",
                cfg.strategy,
                "--encoding",
                cfg.encoding,
            ],
            { stdio: ["pipe", "pipe", "pipe"] }
        );
        let stdout = "";
        let stderr = "";
        proc.stdout.on("data", (d) => (stdout += d.toString()));
        proc.stderr.on("data", (d) => (stderr += d.toString()));
        proc.on("error", (e) => reject(e));
        proc.on("close", (code) => {
            if (code !== 0) {
                reject(new Error(stderr || `exit ${code}`));
                return;
            }
            try {
                resolve(JSON.parse(stdout));
            } catch (e) {
                reject(new Error(`Could not parse CLI JSON: ${e}`));
            }
        });
        proc.stdin.write(text);
        proc.stdin.end();
    });
}

function updateStatusBar() {
    if (!statusBar) return;
    const cfg = getConfig();
    if (!cfg.statusBarEnabled) {
        statusBar.hide();
        return;
    }
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.selection.isEmpty) {
        statusBar.hide();
        return;
    }
    const text = editor.document.getText(editor.selection);
    const approx = approximateTokens(text);
    statusBar.text = `$(zap) ~${approx} tok`;
    statusBar.tooltip = `TokenSqueeze: approximate ${cfg.encoding} tokens for selection. Click to compress.`;
    statusBar.show();
}

function approximateTokens(s: string): number {
    if (!s) return 0;
    const matches = s.match(/[\w]+|[^\s\w]/gu) ?? [];
    return Math.max(1, Math.round(matches.length * 1.3));
}

function toggleStatusBar() {
    const c = vscode.workspace.getConfiguration("tokensqueeze");
    const cur = c.get<boolean>("statusBar", true);
    c.update("statusBar", !cur, vscode.ConfigurationTarget.Global);
}

async function openExplainView(r: CompressResponse) {
    const panel = vscode.window.createWebviewPanel(
        "tokensqueezeExplain",
        "TokenSqueeze: Explain",
        vscode.ViewColumn.Beside,
        { enableScripts: false }
    );
    panel.webview.html = renderExplain(r);
}

function escapeHtml(s: string): string {
    return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
}

function renderExplain(r: CompressResponse): string {
    const rows = r.rules_applied
        .map(
            (rule) => `<tr>
            <td><code>${escapeHtml(rule.category)}</code></td>
            <td><code>${escapeHtml(rule.id)}</code></td>
            <td><pre>${escapeHtml(rule.before)}</pre></td>
            <td><pre>${escapeHtml(rule.after)}</pre></td>
          </tr>`
        )
        .join("\n");
    const pct = (r.tokens.reduction * 100).toFixed(1);
    return `<!doctype html>
<html><head><meta charset="utf-8" />
<style>
body { font-family: var(--vscode-font-family); padding: 12px; }
h1 { font-size: 1.1em; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.col pre { white-space: pre-wrap; word-break: break-word; padding: 8px; background: var(--vscode-textCodeBlock-background); border-radius: 4px; }
table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.9em; }
td, th { border-bottom: 1px solid var(--vscode-panel-border); padding: 4px 6px; vertical-align: top; }
td pre { margin: 0; white-space: pre-wrap; word-break: break-word; }
.warn { color: var(--vscode-editorWarning-foreground); }
</style></head>
<body>
<h1>TokenSqueeze — ${r.tokens.original} → ${r.tokens.compressed} tokens (-${pct}%)</h1>
<p>Strategy: <b>${escapeHtml(r.strategy)}</b>${r.classified_as ? ` (classified as <i>${escapeHtml(r.classified_as)}</i>)` : ""}</p>
${r.warning ? `<p class="warn">⚠ ${escapeHtml(r.warning)}</p>` : ""}
<div class="cols">
  <div class="col"><h3>Original</h3><pre>${escapeHtml(r.original)}</pre></div>
  <div class="col"><h3>Compressed</h3><pre>${escapeHtml(r.compressed)}</pre></div>
</div>
<h3>Rules applied (${r.rules_applied.length})</h3>
<table><thead><tr><th>Category</th><th>Rule</th><th>Before</th><th>After</th></tr></thead><tbody>${rows}</tbody></table>
</body></html>`;
}
