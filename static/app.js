const state = {
  events: [],
  stats: {
    total_events: 0,
    connections: 0,
    by_event_type: {},
    by_project: {},
    by_author: {},
    by_source: {},
  },
};

const ui = {
  connection: document.getElementById("connection-state"),
  totalEvents: document.getElementById("total-events"),
  liveConnections: document.getElementById("live-connections"),
  topEvent: document.getElementById("top-event"),
  topSource: document.getElementById("top-source"),
  eventBars: document.getElementById("event-bars"),
  sourceBars: document.getElementById("source-bars"),
  eventLog: document.getElementById("event-log"),
  logTemplate: document.getElementById("log-item-template"),
};

function entriesSorted(counterObj) {
  return Object.entries(counterObj).sort((a, b) => b[1] - a[1]);
}

function topLabel(counterObj) {
  const top = entriesSorted(counterObj)[0];
  if (!top) {
    return "-";
  }
  return `${top[0]} (${top[1]})`;
}

function setConnectionState(text, isOk = true) {
  ui.connection.textContent = text;
  ui.connection.style.color = isOk ? "#0f766e" : "#be123c";
  ui.connection.style.borderColor = isOk ? "rgba(15,118,110,.35)" : "rgba(190,18,60,.35)";
}

function renderBars(target, data, maxRows = 8) {
  target.innerHTML = "";
  const sorted = entriesSorted(data).slice(0, maxRows);

  if (!sorted.length) {
    const p = document.createElement("p");
    p.textContent = "No data yet";
    p.style.color = "#5f6875";
    target.appendChild(p);
    return;
  }

  const maxValue = sorted[0][1] || 1;

  for (const [label, count] of sorted) {
    const row = document.createElement("div");
    row.className = "bar-row";

    const name = document.createElement("div");
    name.className = "bar-label";
    name.textContent = label;

    const track = document.createElement("div");
    track.className = "bar-track";

    const value = document.createElement("div");
    value.className = "bar-value";
    value.style.width = `${Math.max(6, (count / maxValue) * 100)}%`;

    const countEl = document.createElement("div");
    countEl.className = "bar-count";
    countEl.textContent = String(count);

    track.appendChild(value);
    row.append(name, track, countEl);
    target.appendChild(row);
  }
}

function renderLog(events) {
  ui.eventLog.innerHTML = "";

  for (const event of events.slice(0, 50)) {
    const fragment = ui.logTemplate.content.cloneNode(true);
    const item = fragment.querySelector(".log-item");
    const eventType = fragment.querySelector(".event-type");
    const timestamp = fragment.querySelector(".timestamp");
    const title = fragment.querySelector(".log-title");
    const meta = fragment.querySelector(".log-meta");

    eventType.textContent = event.event_type;
    const time = new Date(event.received_at);
    timestamp.textContent = Number.isNaN(time.valueOf())
      ? event.received_at
      : `${time.toLocaleDateString()} ${time.toLocaleTimeString()}`;

    title.textContent = `${event.summary} by ${event.author}`;
    meta.textContent = `${event.project} | source: ${event.source}`;

    item.style.animation = "fade-up 260ms ease-out";
    ui.eventLog.appendChild(fragment);
  }
}

function render() {
  ui.totalEvents.textContent = String(state.stats.total_events || 0);
  ui.liveConnections.textContent = String(state.stats.connections || 0);
  ui.topEvent.textContent = topLabel(state.stats.by_event_type || {});
  ui.topSource.textContent = topLabel(state.stats.by_source || {});

  renderBars(ui.eventBars, state.stats.by_event_type || {});
  renderBars(ui.sourceBars, state.stats.by_source || {});
  renderLog(state.events || []);
}

async function loadInitialData() {
  try {
    const res = await fetch("/api/logs");
    if (!res.ok) {
      throw new Error("Failed to load logs");
    }
    const data = await res.json();
    state.events = data.events || [];
    state.stats = data.stats || state.stats;
    render();
  } catch {
    setConnectionState("Initial load failed", false);
  }
}

function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${location.host}/ws`);

  ws.onopen = () => {
    setConnectionState("Live stream connected", true);
  };

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.type === "snapshot") {
        state.events = message.events || [];
        state.stats = message.stats || state.stats;
      }

      if (message.type === "new_event") {
        if (message.event) {
          state.events = [message.event, ...state.events].slice(0, 1000);
        }
        if (message.stats) {
          state.stats = message.stats;
        }
      }

      render();
    } catch {
      setConnectionState("Stream parse error", false);
    }
  };

  ws.onclose = () => {
    setConnectionState("Disconnected, retrying...", false);
    setTimeout(connectWebSocket, 1200);
  };

  ws.onerror = () => {
    ws.close();
  };

  return ws;
}

loadInitialData();
connectWebSocket();
