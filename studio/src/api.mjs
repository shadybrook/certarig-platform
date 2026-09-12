const KEYS = {
  operator: "certarig.operatorKey",
  name: "certarig.operatorName",
  session: "certarig.sessionToken",
  view: "certarig.view",
  run: "certarig.runId",
  agent: "certarig.agentSession",
};

export const store = {
  get operatorKey() {
    return sessionStorage.getItem(KEYS.operator) || "";
  },
  get name() {
    return sessionStorage.getItem(KEYS.name) || "studio-operator";
  },
  get sessionToken() {
    return sessionStorage.getItem(KEYS.session) || "";
  },
  get view() {
    return localStorage.getItem(KEYS.view) || "";
  },
  get runId() {
    return localStorage.getItem(KEYS.run) || "";
  },
  get agentSession() {
    return localStorage.getItem(KEYS.agent) || "";
  },
  set(key, name) {
    sessionStorage.setItem(KEYS.operator, key);
    sessionStorage.setItem(KEYS.name, name);
  },
  setSession(token) {
    if (token) sessionStorage.setItem(KEYS.session, token);
    else sessionStorage.removeItem(KEYS.session);
  },
  setView(name) {
    localStorage.setItem(KEYS.view, name);
  },
  setRunId(id) {
    if (id) localStorage.setItem(KEYS.run, id);
    else localStorage.removeItem(KEYS.run);
  },
  setAgentSession(id) {
    if (id) localStorage.setItem(KEYS.agent, id);
    else localStorage.removeItem(KEYS.agent);
  },
  clear() {
    sessionStorage.removeItem(KEYS.operator);
    sessionStorage.removeItem(KEYS.name);
    sessionStorage.removeItem(KEYS.session);
  },
};

let contractHash = "";

export function headers(mutating = false) {
  const out = { Accept: "application/json" };
  if (store.sessionToken) out["X-CertaRig-Session"] = store.sessionToken;
  if (store.operatorKey) {
    out["X-CertaRig-Operator-Key"] = store.operatorKey;
    out["X-CertaRig-Operator"] = store.name;
  }
  if (mutating && contractHash) out["X-CertaRig-Contract"] = contractHash;
  return out;
}

function asError(response, data) {
  const error = new Error(data.title || data.error || response.statusText);
  error.status = response.status;
  error.payload = data;
  error.code = data.code;
  return error;
}

export async function api(method, path, body, { retry = true } = {}) {
  const mutating = method !== "GET";
  const response = await fetch(path, {
    method,
    headers: { ...headers(mutating), ...(body ? { "Content-Type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { error: text };
  }
  if (!response.ok) {
    if (retry && response.status === 409 && data.code === "stale_contract") {
      await refreshContract();
      return api(method, path, body, { retry: false });
    }
    throw asError(response, data);
  }
  if (data.contract_hash) contractHash = data.contract_hash;
  return data;
}

export const get = (path) => api("GET", path);
export const post = (path, body = {}) => api("POST", path, body);

export async function refreshContract() {
  const rig = await get("/v1/rig");
  contractHash = rig.contract_hash;
  return rig;
}

export function toastText(error) {
  const payload = error.payload || {};
  const title = payload.title || error.message;
  const next = payload.next || "";
  return next ? `${title} — ${next}` : title;
}

export function downloadUrl(path) {
  return path;
}
