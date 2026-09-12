const section = document.querySelector("#live-bench");

if (section) {
  const byId = id => document.querySelector(`#${id}`);
  const connection = byId("live-connection");
  const message = byId("live-message");
  const operatorKey = byId("live-operator-key");
  const recordButton = byId("live-record");
  const downloadButton = byId("live-download");
  let online = false;
  let recording = false;
  let latestFilename = null;

  function endpoint(path) {
    return new URL(`./${path.replace(/^\//, "")}`, document.baseURI).toString();
  }

  function setMessage(text, tone = "") {
    message.textContent = text;
    message.dataset.tone = tone;
  }

  function channel(state, unit) {
    return (state.guardrail?.channels ?? []).find(item => item.unit.toLowerCase() === unit.toLowerCase());
  }

  function rawSample(state, channelId) {
    return (state.samples ?? []).find(item => item.channel_id === channelId);
  }

  function fixed(value, places = 2) {
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(places) : "—";
  }

  function stateLabel(reason) {
    return String(reason || "unknown").replaceAll("_", " ").toUpperCase();
  }

  function renderSensor(card, status, valueNode, voltageNode, stateNode, meterNode, meterMax) {
    const sensorState = status?.state ?? "invalid";
    card.dataset.sensorState = sensorState;
    stateNode.textContent = sensorState.toUpperCase();
    valueNode.textContent = fixed(status?.value);
    const raw = rawSample(window.certarigLiveState, status?.channel_id);
    voltageNode.textContent = `${fixed(raw?.raw_value, 3)} V`;
    const width = Math.max(0, Math.min(100, Number(status?.value ?? 0) / meterMax * 100));
    meterNode.style.width = `${width}%`;
  }

  function chartPath(values, valueKey, width, left, right, top, bottom, max) {
    const finite = values.filter(item => Number.isFinite(Number(item[valueKey])));
    if (finite.length < 2) return "";
    const firstTime = Number(finite[0].elapsed_s);
    const lastTime = Math.max(firstTime + 0.1, Number(finite.at(-1).elapsed_s));
    return finite.map((item, index) => {
      const x = left + (Number(item.elapsed_s) - firstTime) / (lastTime - firstTime) * (width - left - right);
      const y = bottom - Math.max(0, Math.min(max, Number(item[valueKey]))) / max * (bottom - top);
      return `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
  }

  function renderChart(history) {
    const container = byId("live-chart");
    if (!history || history.length < 2) {
      container.innerHTML = "<span>Waiting for a rolling telemetry window…</span>";
      return;
    }
    const values = history.slice(-300);
    const width = 920;
    const left = 48;
    const right = 22;
    const pressureTop = 25;
    const pressureBottom = 112;
    const flowTop = 154;
    const flowBottom = 241;
    const pressureLimitY = pressureBottom - 4.2 / 10 * (pressureBottom - pressureTop);
    const flowLimitY = flowBottom - 15 / 20 * (flowBottom - flowTop);
    const pressurePath = chartPath(values, "pressure_bar", width, left, right, pressureTop, pressureBottom, 10);
    const flowPath = chartPath(values, "flow_l_min", width, left, right, flowTop, flowBottom, 20);
    container.innerHTML = `
      <svg viewBox="0 0 ${width} 270" role="img" aria-label="Live pressure and flow telemetry with guardrail limits">
        <line x1="${left}" x2="${width - right}" y1="${pressureTop}" y2="${pressureTop}" class="grid-line" />
        <line x1="${left}" x2="${width - right}" y1="${pressureBottom}" y2="${pressureBottom}" class="grid-line" />
        <text x="${left}" y="15" class="axis-title">Pressure · 0–10 bar</text>
        <line x1="${left}" x2="${width - right}" y1="${pressureLimitY}" y2="${pressureLimitY}" class="limit-line" />
        <text x="${left + 8}" y="${pressureLimitY - 6}" class="limit-label">4.2 bar guardrail</text>
        <path d="${pressurePath}" class="series pressure" />
        <line x1="${left}" x2="${width - right}" y1="${flowTop}" y2="${flowTop}" class="grid-line" />
        <line x1="${left}" x2="${width - right}" y1="${flowBottom}" y2="${flowBottom}" class="grid-line" />
        <text x="${left}" y="144" class="axis-title">Flow · 0–20 L/min</text>
        <line x1="${left}" x2="${width - right}" y1="${flowLimitY}" y2="${flowLimitY}" class="limit-line" />
        <text x="${left + 8}" y="${flowLimitY - 6}" class="limit-label">15 L/min guardrail</text>
        <path d="${flowPath}" class="series flow" />
        <text x="${left}" y="263" class="axis-label">rolling window</text>
        <text x="${width - right}" y="263" text-anchor="end" class="axis-label">latest sample</text>
      </svg>`;
  }

  function render(state) {
    window.certarigLiveState = state;
    online = true;
    connection.dataset.state = "online";
    byId("live-connection-label").textContent = "Pi service online";
    byId("live-connection-detail").textContent = `${state.rig_id} · sample ${state.sample_index}`;
    byId("live-guardrail-state").textContent = stateLabel(state.guardrail?.reason);
    byId("live-last-event").textContent = `Last event · ${state.last_event || "none"}`;
    byId("live-mode").textContent = state.actuation_enabled ? "ARMED DRY BENCH" : "MONITOR ONLY";

    const pressure = channel(state, "bar");
    const flow = channel(state, "L/min");
    renderSensor(section.querySelectorAll(".sensor-card")[0], pressure, byId("live-pressure"), byId("live-pressure-voltage"), byId("live-pressure-state"), byId("live-pressure-meter"), 10);
    renderSensor(section.querySelectorAll(".sensor-card")[1], flow, byId("live-flow"), byId("live-flow-voltage"), byId("live-flow-state"), byId("live-flow-meter"), 20);

    const estopActive = Boolean(state.guardrail?.estop_active);
    const tripLatched = Boolean(state.guardrail?.trip_latched);
    const gpioHigh = Boolean(state.outputs?.gpio23_command_high);
    const relayOn = Boolean(state.outputs?.relay_energized_expected);
    byId("live-estop").textContent = estopActive ? "ACTIVE / OPEN" : "RELEASED / CLOSED";
    byId("live-estop").dataset.state = estopActive ? "danger" : "safe";
    byId("live-trip").textContent = tripLatched ? "LATCHED" : "RESET";
    byId("live-trip").dataset.state = tripLatched ? "danger" : "safe";
    byId("live-gpio23").textContent = gpioHigh ? "HIGH" : "LOW";
    byId("live-gpio23").dataset.state = gpioHigh ? "safe" : "danger";
    byId("live-relay").textContent = relayOn ? "EXPECTED ON" : "EXPECTED OFF";
    byId("live-relay").dataset.state = relayOn ? "safe" : "danger";
    byId("live-red-lamp").dataset.on = String(Boolean(state.outputs?.red_indicator_expected));
    byId("live-green-lamp").dataset.on = String(Boolean(state.outputs?.green_indicator_expected));

    recording = Boolean(state.recording?.active);
    latestFilename = state.recording?.filename || state.completed_recording?.filename || latestFilename;
    recordButton.textContent = recording ? `Stop CSV (${state.recording.samples})` : "Start CSV";
    recordButton.classList.toggle("danger", recording);
    downloadButton.disabled = !latestFilename;
    renderChart(state.history);
  }

  async function request(path, options = {}) {
    const response = await fetch(endpoint(path), { cache: "no-store", ...options });
    const type = response.headers.get("content-type") || "";
    const payload = type.includes("application/json") ? await response.json() : null;
    if (!response.ok) throw new Error(payload?.error || `HTTP ${response.status}`);
    return payload;
  }

  function authHeaders() {
    return {
      "Content-Type": "application/json",
      "X-CertaRig-Operator-Key": operatorKey.value,
    };
  }

  async function poll() {
    try {
      const state = await request("v1/live/state");
      render(state);
      if (state.status === "error") setMessage(`Fail-safe runtime error: ${state.error}`, "error");
    } catch (error) {
      online = false;
      connection.dataset.state = "offline";
      byId("live-connection-label").textContent = "Live Pi unavailable";
      byId("live-connection-detail").textContent = "Static Phase 2 preview only";
      setMessage("Open the website from the Pi-hosted live-dashboard service to receive physical data.");
    }
  }

  async function sendCommand(command) {
    if (!online) return setMessage("The Pi live service is not connected.", "error");
    try {
      const state = await request(`v1/live/commands/${command}`, {
        method: "POST",
        headers: authHeaders(),
        body: "{}",
      });
      render(state);
      setMessage(`Command result: ${state.guardrail.event}`, state.guardrail.event.includes("accepted") ? "success" : "");
    } catch (error) {
      setMessage(error.message, "error");
    }
  }

  byId("live-safe").addEventListener("click", () => sendCommand("safe"));
  byId("live-reset").addEventListener("click", () => sendCommand("reset"));
  byId("live-permit").addEventListener("click", () => sendCommand("permit"));

  recordButton.addEventListener("click", async () => {
    if (!online) return setMessage("The Pi live service is not connected.", "error");
    try {
      const path = recording ? "v1/live/recordings/stop" : "v1/live/recordings/start";
      const body = recording ? {} : { label: byId("live-record-label").value };
      const state = await request(path, { method: "POST", headers: authHeaders(), body: JSON.stringify(body) });
      render(state);
      setMessage(recording ? "CSV recording is active." : `CSV saved: ${state.completed_recording.filename} · SHA256 ${state.completed_recording.sha256}`, "success");
    } catch (error) {
      setMessage(error.message, "error");
    }
  });

  downloadButton.addEventListener("click", async () => {
    try {
      const response = await fetch(endpoint("v1/live/recordings/latest.csv"), { headers: { "X-CertaRig-Operator-Key": operatorKey.value } });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.error || `HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = latestFilename || "certarig-live-evidence.csv";
      link.click();
      URL.revokeObjectURL(url);
      setMessage(`Downloaded ${link.download}`, "success");
    } catch (error) {
      setMessage(error.message, "error");
    }
  });

  poll();
  window.setInterval(poll, 500);
}
