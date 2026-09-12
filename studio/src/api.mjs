const KEYS = { operator: "certarig.operatorKey", name: "certarig.operatorName" };

export const store = {
  get operatorKey() {
    return sessionStorage.getItem(KEYS.operator) || "";
  },
  get name() {
    return sessionStorage.getItem(KEYS.name) || "studio-operator";
  },
  set(key, name) {
    sessionStorage.setItem(KEYS.operator, key);
    sessionStorage.setItem(KEYS.name, name);
  },
  clear() {
    sessionStorage.removeItem(KEYS.operator);
    sessionStorage.removeItem(KEYS.name);
  },
};

let contractHash = "";

export function headers(mutating = false) {
  const out = { Accept: "application/json" };
  if (store.operatorKey) {
    out["X-CertaRig-Operator-Key"] = store.operatorKey;
    out["X-CertaRig-Operator"] = store.name;
  }
  if (mutating && contractHash) out["X-CertaRig-Contract"] = contractHash;
  return out;
}

export async function api(method, path, body) {
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
    const error = new Error(data.error || response.statusText);
    error.status = response.status;
    error.payload = data;
    throw error;
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

export function downloadUrl(path) {
  return path;
}
