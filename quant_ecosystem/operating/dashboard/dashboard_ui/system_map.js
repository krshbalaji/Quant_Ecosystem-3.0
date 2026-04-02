const statusPill = document.getElementById("status-pill");
const systemMap = document.getElementById("system-map");
const strategyPanel = document.getElementById("strategy-panel");
const marketPanel = document.getElementById("market-panel");
const eventStream = document.getElementById("event-stream");

const pushEvent = (text) => {
  const row = document.createElement("div");
  row.className = "event-line";
  row.textContent = text;
  eventStream.prepend(row);
  while (eventStream.children.length > 120) {
    eventStream.removeChild(eventStream.lastChild);
  }
};

const renderNodes = (engines) => {
  systemMap.innerHTML = "";
  Object.entries(engines || {}).forEach(([name, info]) => {
    const div = document.createElement("div");
    div.className = "node";
    const statusClass = String(info.status || "OFF").toUpperCase() === "ON" ? "status-on" : "status-off";
    div.innerHTML = `
      <div class="title">${name}</div>
      <div class="meta ${statusClass}">status=${info.status || "OFF"}</div>
      <div class="meta">activity=${info.activity_level ?? 0}</div>
      <div class="meta">last=${info.last_event_ts || "-"}</div>
    `;
    systemMap.appendChild(div);
  });
};

const renderMarket = (state) => {
  const m = state.market || {};
  const p = state.portfolio || {};
  marketPanel.textContent =
    `regime=${m.regime || "UNKNOWN"}\n` +
    `volatility=${m.volatility ?? 0}\n` +
    `trend_direction=${m.trend_direction ?? 0}\n` +
    `equity=${p.equity ?? 0}\n` +
    `realized=${p.realized_pnl ?? 0} unrealized=${p.unrealized_pnl ?? 0}\n` +
    `drawdown=${p.drawdown_pct ?? 0}% open_positions=${p.open_positions ?? 0}`;
};

const refreshStrategies = async () => {
  try {
    const resp = await fetch("/strategies");
    const data = await resp.json();
    const active = data.active_strategies || [];
    const rows = (data.strategy_rows || []).slice(0, 8);
    const top = rows.map((r) =>
      `${r.id || "?"} | stage=${r.stage || "NA"} | active=${Boolean(r.active)} | alloc=${r.allocation_pct ?? 0}%`
    );
    strategyPanel.textContent =
      `active=${JSON.stringify(active)}\n` +
      top.join("\n");
  } catch (err) {
    strategyPanel.textContent = `strategy error: ${err}`;
  }
};

const connect = () => {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => {
    statusPill.textContent = "Live";
    pushEvent(`${new Date().toLocaleTimeString()} websocket connected`);
    ws.send("hello");
  };
  ws.onclose = () => {
    statusPill.textContent = "Disconnected - retrying";
    setTimeout(connect, 1500);
  };
  ws.onerror = () => {
    statusPill.textContent = "Error - retrying";
    ws.close();
  };
  ws.onmessage = async (msg) => {
    try {
      const payload = JSON.parse(msg.data);
      if (payload.type === "system_state") {
        renderNodes(payload.data.engines || {});
        renderMarket(payload.data || {});
      }
      await refreshStrategies();
    } catch (err) {
      pushEvent(`${new Date().toLocaleTimeString()} parse_error ${err}`);
    }
  };
};

connect();
setInterval(refreshStrategies, 2000);

