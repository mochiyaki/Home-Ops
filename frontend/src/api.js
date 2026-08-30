export async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }
  if (!res.ok) {
    const err = new Error(humanError(data, res.status));
    err.payload = data;
    err.status = res.status;
    throw err;
  }
  return data;
}

function humanError(data, status) {
  if (typeof data?.detail === "string") return data.detail;
  if (data?.error === "VendorNotConfigured") {
    return `${data.vendor} is not configured (${data.missing}). Set the key or HOMEOPS_MOCK=1.`;
  }
  if (data?.error) return data.detail || data.error;
  return `Request failed (${status})`;
}

export function health() {
  return api("/health");
}

export function mintLiveSession() {
  return api("/api/live/session", { method: "POST", body: {} });
}

export function mintVoiceSession(houseSnapshot) {
  return api("/api/voice/web", {
    method: "POST",
    body: { house_snapshot: houseSnapshot || "" },
  });
}

export function lookupModel(query) {
  return api("/api/tools/exa", { method: "POST", body: { query } });
}

export function findProviders(trade, address) {
  return api("/api/tools/providers", { method: "POST", body: { trade, address } });
}

export function placeCall(phone, brief, tryAnother = false, shopName = "") {
  return api("/api/tools/call", {
    method: "POST",
    body: { phone, brief, try_another: tryAnother, shop_name: shopName },
  });
}

export function getCall(id) {
  return api(`/api/calls/${id}`);
}

// Everything below reads the server's copy of the house and its call history.
// The voice agent writes to the same records, which is what lets the UI show
// work it did not start itself.
export function getHouse() {
  return api("/api/house");
}

export function patchHouse(patch) {
  return api("/api/house", { method: "PATCH", body: patch });
}

export function listCalls(limit = 20) {
  return api(`/api/calls?limit=${limit}`);
}

export function getCallDetail(id) {
  return api(`/api/calls/${id}/detail`);
}

export function getTranscript(id) {
  return api(`/api/calls/${id}/transcript`);
}
