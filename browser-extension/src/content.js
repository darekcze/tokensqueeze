/* TokenSqueeze content script.
 *
 * Locates the prompt input on supported LLM sites and injects a "Squeeze"
 * button that POSTs the current prompt to the local FastAPI server and
 * replaces it with the compressed version.
 */

const ENDPOINT_DEFAULT = "http://127.0.0.1:8765/compress";

const SELECTORS = [
    // ChatGPT
    "#prompt-textarea",
    'textarea[data-id="root"]',
    // Claude
    'div[contenteditable="true"][data-testid="chat-input"]',
    'div[contenteditable="true"].ProseMirror',
    // Perplexity
    'textarea[placeholder*="Ask anything"]',
    'textarea[placeholder*="Ask"]',
    // Gemini
    'rich-textarea div[contenteditable="true"]',
    // Generic fallbacks
    'textarea[role="textbox"]',
];

function findInput() {
    for (const sel of SELECTORS) {
        const el = document.querySelector(sel);
        if (el) return el;
    }
    return null;
}

function getText(el) {
    if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
        return el.value;
    }
    return el.innerText;
}

function setText(el, text) {
    if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
        setter.call(el, text);
        el.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
        // contenteditable
        el.innerText = text;
        el.dispatchEvent(new InputEvent("input", { bubbles: true }));
    }
}

async function getEndpoint() {
    return new Promise((resolve) => {
        try {
            chrome.storage?.local.get(["endpoint", "strategy"], (res) => {
                resolve({
                    endpoint: res?.endpoint || ENDPOINT_DEFAULT,
                    strategy: res?.strategy || "auto",
                });
            });
        } catch {
            resolve({ endpoint: ENDPOINT_DEFAULT, strategy: "auto" });
        }
    });
}

async function squeeze(input, button) {
    const text = getText(input);
    if (!text || !text.trim()) return;
    const original = button.textContent;
    button.textContent = "…";
    button.disabled = true;

    try {
        const { endpoint, strategy } = await getEndpoint();
        const r = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: text, strategy }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        setText(input, data.compressed);

        const pct = (data.tokens.reduction * 100).toFixed(1);
        toast(`-${pct}% (${data.tokens.original} → ${data.tokens.compressed} tok, ${data.strategy})`, "ok");
    } catch (e) {
        console.error("[TokenSqueeze]", e);
        toast(`Failed: ${e.message}. Is the server running on 127.0.0.1:8765?`, "err");
    } finally {
        button.textContent = original;
        button.disabled = false;
    }
}

function toast(msg, kind) {
    const t = document.createElement("div");
    t.className = `tsq-toast ${kind === "err" ? "tsq-err" : "tsq-ok"}`;
    t.textContent = `TokenSqueeze: ${msg}`;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}

function injectButton() {
    if (document.querySelector(".tsq-btn")) return;
    const input = findInput();
    if (!input) return;
    const btn = document.createElement("button");
    btn.className = "tsq-btn";
    btn.textContent = "⚡ Squeeze";
    btn.title = "Compress this prompt with TokenSqueeze";
    btn.type = "button";
    btn.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        squeeze(input, btn);
    });

    // Position the button as a fixed overlay relative to the input.
    document.body.appendChild(btn);
    const reposition = () => {
        const rect = input.getBoundingClientRect();
        if (!rect) return;
        btn.style.top = `${rect.top + window.scrollY + 8}px`;
        btn.style.left = `${rect.right + window.scrollX - 110}px`;
    };
    reposition();
    window.addEventListener("scroll", reposition, { passive: true });
    window.addEventListener("resize", reposition, { passive: true });
}

const observer = new MutationObserver(() => injectButton());
observer.observe(document.documentElement, { childList: true, subtree: true });
injectButton();
