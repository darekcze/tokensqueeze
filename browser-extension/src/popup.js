const $ = (id) => document.getElementById(id);
const status = $("status");

function load() {
    chrome.storage.local.get(["endpoint", "strategy"], (r) => {
        $("endpoint").value = r.endpoint || "http://127.0.0.1:8765/compress";
        $("strategy").value = r.strategy || "auto";
    });
}

$("save").addEventListener("click", () => {
    const endpoint = $("endpoint").value.trim() || "http://127.0.0.1:8765/compress";
    const strategy = $("strategy").value;
    chrome.storage.local.set({ endpoint, strategy }, () => {
        status.textContent = "Saved.";
        status.className = "ok";
    });
});

$("ping").addEventListener("click", async () => {
    const endpoint = $("endpoint").value.trim() || "http://127.0.0.1:8765/compress";
    const health = endpoint.replace(/\/compress$/, "/health");
    try {
        const r = await fetch(health);
        const j = await r.json();
        status.textContent = `OK: ${JSON.stringify(j)}`;
        status.className = "ok";
    } catch (e) {
        status.textContent = `Error: ${e.message}`;
        status.className = "err";
    }
});

load();
