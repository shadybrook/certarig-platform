const baselineChannels = [
  {
    id: "AI0",
    device: "Pressure sensor P1",
    kind: "pressure",
    unit: "bar",
    validRange: [0, 5],
    safeRange: [0, 4.2],
    calibration: "CAL-P1-2026-04",
    confidence: 0.98,
    evidence: "wiring register and calibration record"
  },
  {
    id: "AI1",
    device: "Flow sensor F1",
    kind: "flow",
    unit: "L/min",
    validRange: [0, 20],
    safeRange: [0, 18],
    calibration: "CAL-F1-2026-03",
    confidence: 0.96,
    evidence: "channel configuration and response signature"
  },
  {
    id: "DI0",
    device: "Valve limit switch LS1",
    kind: "position",
    unit: "state",
    validRange: [0, 1],
    safeRange: [0, 1],
    calibration: "not required",
    confidence: 1,
    evidence: "digital input register"
  },
  {
    id: "DO0",
    device: "Normally closed valve V1",
    kind: "command",
    unit: "state",
    validRange: [0, 1],
    safeRange: [0, 1],
    calibration: "not required",
    confidence: 1,
    evidence: "approved output configuration"
  }
];

const scenarioDefinitions = {
  normal: {
    title: "Case 1: Approved baseline",
    summary: "All mappings and records agree. The bounded valve response test completes.",
    mutations: [],
    telemetryMode: "normal"
  },
  swapped: {
    title: "Case 2: Swapped analog channels",
    summary: "Pressure and flow channel assignments are reversed in the proposed configuration.",
    mutations: [
      { type: "swap", first: "AI0", second: "AI1" }
    ],
    telemetryMode: "swapped"
  },
  missingCalibration: {
    title: "Case 3: Missing calibration evidence",
    summary: "The pressure sensor has no current calibration reference, so the plan must stop.",
    mutations: [
      { type: "calibration", id: "AI0", value: null }
    ],
    telemetryMode: "normal"
  },
  safetyLimit: {
    title: "Case 4: Pressure safety limit breach",
    summary: "Measured pressure crosses the approved limit and the deterministic runtime aborts.",
    mutations: [],
    telemetryMode: "overpressure"
  }
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function applyMutations(channels, mutations) {
  const updated = clone(channels);
  for (const mutation of mutations) {
    if (mutation.type === "swap") {
      const firstIndex = updated.findIndex(channel => channel.id === mutation.first);
      const secondIndex = updated.findIndex(channel => channel.id === mutation.second);
      const first = updated[firstIndex];
      const second = updated[secondIndex];
      [first.device, second.device] = [second.device, first.device];
      [first.kind, second.kind] = [second.kind, first.kind];
      [first.unit, second.unit] = [second.unit, first.unit];
      [first.validRange, second.validRange] = [second.validRange, first.validRange];
      [first.safeRange, second.safeRange] = [second.safeRange, first.safeRange];
      [first.calibration, second.calibration] = [second.calibration, first.calibration];
      [first.evidence, second.evidence] = [second.evidence, first.evidence];
    }
    if (mutation.type === "calibration") {
      const channel = updated.find(item => item.id === mutation.id);
      channel.calibration = mutation.value;
      channel.confidence = 0.62;
    }
  }
  return updated;
}

function compareChannels(baseline, proposed) {
  const changes = [];
  for (const expected of baseline) {
    const actual = proposed.find(channel => channel.id === expected.id);
    if (!actual) {
      changes.push({
        code: "CHANNEL_MISSING",
        severity: "stop",
        channel: expected.id,
        message: `${expected.id} is missing from the proposed model.`
      });
      continue;
    }
    if (expected.kind !== actual.kind || expected.device !== actual.device) {
      changes.push({
        code: "MAPPING_CHANGED",
        severity: "review",
        channel: expected.id,
        message: `${expected.id} changed from ${expected.device} to ${actual.device}.`
      });
    }
    if (!actual.calibration && actual.kind !== "position" && actual.kind !== "command") {
      changes.push({
        code: "CALIBRATION_MISSING",
        severity: "stop",
        channel: expected.id,
        message: `${expected.id} has no current calibration evidence.`
      });
    }
    if (expected.unit !== actual.unit) {
      changes.push({
        code: "UNIT_CHANGED",
        severity: "review",
        channel: expected.id,
        message: `${expected.id} changed unit from ${expected.unit} to ${actual.unit}.`
      });
    }
  }
  return changes;
}

function makeTelemetry(mode) {
  return Array.from({ length: 25 }, (_, index) => {
    const time = index * 0.5;
    const valve = index >= 5 && index < 19 ? 1 : 0;
    let pressure = valve ? 1.05 + (index - 5) * 0.1 : Math.max(0.22, 0.7 - index * 0.02);
    let flow = valve ? 5.4 + Math.sin(index / 2) * 0.35 : 0.2;
    if (mode === "overpressure" && index >= 12) {
      pressure = 3.4 + (index - 12) * 0.22;
    }
    if (mode === "swapped") {
      [pressure, flow] = [flow, pressure];
    }
    return {
      time,
      pressure: Number(pressure.toFixed(2)),
      flow: Number(flow.toFixed(2)),
      valve
    };
  });
}

function diagnoseTelemetry(telemetry, channels, changes) {
  const findings = [...changes];
  const pressureChannel = channels.find(channel => channel.kind === "pressure");
  const maxPressure = Math.max(...telemetry.map(row => row.pressure));
  const mappingIsResolved = !changes.some(change => change.code === "MAPPING_CHANGED");
  if (mappingIsResolved && pressureChannel && maxPressure > pressureChannel.safeRange[1]) {
    findings.push({
      code: "SAFE_LIMIT_EXCEEDED",
      severity: "abort",
      channel: pressureChannel.id,
      message: `Pressure reached ${maxPressure.toFixed(2)} bar against a ${pressureChannel.safeRange[1].toFixed(1)} bar limit.`
    });
  }
  if (changes.some(change => change.code === "MAPPING_CHANGED")) {
    findings.push({
      code: "SIGNATURE_CONFLICT",
      severity: "review",
      channel: "AI0/AI1",
      message: "Observed response signatures do not agree with the proposed pressure and flow labels."
    });
  }
  return findings;
}

function makePlan(findings) {
  const mappingReview = findings.some(finding => finding.code === "MAPPING_CHANGED");
  const hasStop = mappingReview || findings.some(finding => ["stop", "abort"].includes(finding.severity));
  const steps = [
    { id: "P01", action: "Validate model schema and approved safety limits", status: "complete" },
    { id: "P02", action: "Check evidence and confidence for every material channel", status: hasStop ? "blocked" : "complete" },
    { id: "P03", action: "Arm bounded simulator plan for valve V1", status: hasStop ? "not run" : "complete" },
    { id: "P04", action: "Compare predicted and measured pressure and flow response", status: hasStop ? "not run" : "complete" },
    { id: "P05", action: mappingReview ? "Request confirmation of AI0 and AI1 wiring" : "Accept evidence bundle and version baseline", status: mappingReview ? "review" : hasStop ? "not run" : "complete" }
  ];
  return {
    allowedToRun: !hasStop,
    steps,
    abortRule: "Close V1 and record the event if pressure exceeds 4.2 bar, evidence is missing, or the model is unresolved."
  };
}

function statusFromFindings(findings) {
  if (findings.some(finding => finding.severity === "abort")) {
    return { key: "aborted", label: "Safe abort", tone: "danger" };
  }
  if (findings.some(finding => finding.severity === "stop")) {
    return { key: "stopped", label: "Human evidence required", tone: "danger" };
  }
  if (findings.some(finding => finding.severity === "review")) {
    return { key: "review", label: "Review required", tone: "warning" };
  }
  return { key: "accepted", label: "Accepted", tone: "success" };
}

export function listScenarios() {
  return Object.entries(scenarioDefinitions).map(([id, scenario]) => ({
    id,
    title: scenario.title,
    summary: scenario.summary
  }));
}

export function evaluateScenario(id) {
  const scenario = scenarioDefinitions[id];
  if (!scenario) {
    throw new Error(`Unknown scenario: ${id}`);
  }
  const proposedChannels = applyMutations(baselineChannels, scenario.mutations);
  const changes = compareChannels(baselineChannels, proposedChannels);
  const telemetry = makeTelemetry(scenario.telemetryMode);
  const findings = diagnoseTelemetry(telemetry, proposedChannels, changes);
  const plan = makePlan(findings);
  const status = statusFromFindings(findings);
  const confidence = Math.round(
    proposedChannels.reduce((sum, channel) => sum + channel.confidence, 0) /
      proposedChannels.length *
      100
  );
  return {
    id,
    title: scenario.title,
    summary: scenario.summary,
    generatedAt: "2026-08-24T15:30:00.000Z",
    baselineVersion: "rig-graph-v1.4",
    proposedVersion: `rig-graph-v1.5-${id}`,
    channels: proposedChannels,
    changes,
    telemetry,
    findings,
    plan,
    status,
    metrics: {
      channels: proposedChannels.length,
      confidence,
      findings: findings.length,
      maxPressure: Math.max(...telemetry.map(row => row.pressure))
    },
    evidenceBundle: {
      inputs: ["rig_configuration.json", "calibration_register.json", "test_plan.json"],
      records: telemetry.length + findings.length + plan.steps.length,
      checksum: `CERTARIG-${id.toUpperCase()}-20260824`
    }
  };
}

export const safetyPolicy = Object.freeze({
  pressureLimitBar: 4.2,
  defaultOutputState: "closed",
  cloudLossBehaviour: "local stop remains available",
  controlAuthority: "deterministic runtime only"
});
