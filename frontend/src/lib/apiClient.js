const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TOKEN_KEY = "dha_auth_token";
const USER_KEY = "dha_auth_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function getCurrentUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setAuthSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuthSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Request failed.");
  }
  return data;
}

export function signup(payload) {
  return request("/api/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function login(payload) {
  return request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function fetchMe() {
  return request("/api/auth/me");
}

export function fetchMyHistory(params = "") {
  return request(`/api/history/my${params}`);
}

export function fetchRecordByUser(userId) {
  return request(`/api/records/by-user/${encodeURIComponent(userId)}`);
}

export function fetchRecordByAnalysis(analysisId) {
  return request(`/api/records/by-analysis/${encodeURIComponent(analysisId)}`);
}

export function fetchRecordByReport(reportId) {
  return request(`/api/records/by-report/${encodeURIComponent(reportId)}`);
}

export function fetchRecordBySession(sessionId) {
  return request(`/api/records/by-session/${encodeURIComponent(sessionId)}`);
}

export function fetchMyChatLogs() {
  return request("/api/chat/logs/my");
}

export function fetchMyReportMetadata() {
  return request("/api/reports/meta/my");
}
