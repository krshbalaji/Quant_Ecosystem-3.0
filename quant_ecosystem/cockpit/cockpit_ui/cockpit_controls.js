const conn = document.getElementById("conn");
const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");

function log(line) {
  const ts = new Date().toLocaleTimeString();
  logEl.textContent = `[${ts}] ${line}\n` + logEl.textContent;
}

function payloadFrom(dataPayload) {
  const payload = {};
  if (!dataPayload) return payload;
  dataPayload.split(",").map(s => s.trim()).forEach((key) => {
    const el = document.getElementById(key);
    if (!el) return;
    const raw = el.value;
    const num = Number(raw);
    payload[key] = Number.isFinite(num) && raw !== "" ? num : raw;
  });
  return payload;
}

async function sendCommand(command, payload) {
  const token = localStorage.getItem("cockpit_token") || "";
  const resp = await fetch("/command", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Operator-Token": token,
    },
    body: JSON.stringify({ command, payload }),
  });
  const data = await resp.json();
  log(`${command} -> ${JSON.stringify(data.result)}`);
}

document.querySelectorAll("button[data-cmd]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const cmd = btn.dataset.cmd;
    const payload = payloadFrom(btn.dataset.payload || "");
    await sendCommand(cmd, payload);
  });
});

function connectWs() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => {
    conn.textContent = "live";
    ws.send("ping");
  };
  ws.onclose = () => {
    conn.textContent = "offline";
    setTimeout(connectWs, 1500);
  };
  ws.onmessage = (m) => {
    try {
      const msg = JSON.parse(m.data);
      if (msg.type === "system_state") {
        statusEl.textContent = JSON.stringify(msg.data, null, 2);
      }
    } catch (e) {
      log(`ws parse error: ${e}`);
    }
  };
}

connectWs();
if (!localStorage.getItem("cockpit_token")) {
  const t = prompt("Enter cockpit operator token (stored in browser):", "");
  if (t !== null) localStorage.setItem("cockpit_token", t);
}

