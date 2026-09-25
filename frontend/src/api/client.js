/**
 * Jett 2 Holiday - Backend API Client & Token Management
 * Wraps all endpoints with fetch requests, automatic Bearer auth headers,
 * error handling, and session persistence in sessionStorage.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const TOKEN_KEY = 'jett_auth_token';
const ROLE_KEY = 'jett_auth_role';
const USER_KEY = 'jett_auth_user';

// ==========================================
// Session & Token Helpers (sessionStorage)
// ==========================================
export function getAuthToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function getAuthRole() {
  return sessionStorage.getItem(ROLE_KEY);
}

export function getAuthUser() {
  try {
    const raw = sessionStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setAuthSession(token, role, user) {
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  if (role) sessionStorage.setItem(ROLE_KEY, role);
  if (user) sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  window.dispatchEvent(new Event('auth_state_changed'));
}

export function clearAuthSession() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(ROLE_KEY);
  sessionStorage.removeItem(USER_KEY);
  window.dispatchEvent(new Event('auth_state_changed'));
}

// ==========================================
// Central Fetch Wrapper with Auth Header
// ==========================================
async function fetchJSON(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = getAuthToken();
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
        ...options.headers,
      },
    });

    if (res.status === 401 || res.status === 403) {
      const errorData = await res.json().catch(() => ({}));
      const err = new Error(errorData.detail || `Auth error: ${res.status}`);
      err.status = res.status;
      throw err;
    }

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      const err = new Error(errorData.detail || `API error: ${res.status} ${res.statusText}`);
      err.status = res.status;
      throw err;
    }

    return await res.json();
  } catch (err) {
    console.warn(`[API Client Warning] Failed to reach ${url}:`, err.message);
    throw err;
  }
}

// ==========================================
// Authentication Endpoints
// ==========================================
export async function adminLogin(username, password) {
  const data = await fetchJSON('/auth/admin/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  setAuthSession(data.access_token, data.role, {
    user_id: data.user_id,
    display_name: data.display_name,
    email: data.email,
  });
  return data;
}

export async function travellerSignup(email, password, displayName) {
  const data = await fetchJSON('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
      display_name: displayName,
    }),
  });
  setAuthSession(data.access_token, data.role, {
    user_id: data.user_id,
    display_name: data.display_name,
    email: data.email,
  });
  return data;
}

export async function travellerLogin(email, password) {
  const data = await fetchJSON('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setAuthSession(data.access_token, data.role, {
    user_id: data.user_id,
    display_name: data.display_name,
    email: data.email,
  });
  return data;
}

// ==========================================
// Admin Dynamic Pricing & Simulation Endpoints
// ==========================================
export async function calculatePricing(entityId, targetDate) {
  return fetchJSON('/pricing/calculate', {
    method: 'POST',
    body: JSON.stringify({
      entity_id: entityId,
      target_date: targetDate,
    }),
  });
}

export async function explainPricing(entityId, date) {
  const query = new URLSearchParams({ entity_id: entityId, date }).toString();
  return fetchJSON(`/pricing/explain?${query}`, {
    method: 'GET',
  });
}

export async function simulatePricing(entityId, baseMultiplier, dailyMoveLimit) {
  return fetchJSON('/pricing/simulate', {
    method: 'POST',
    body: JSON.stringify({
      entity_id: entityId,
      base_multiplier: parseFloat(baseMultiplier),
      daily_move_limit: parseFloat(dailyMoveLimit),
    }),
  });
}

export async function fetchForecastHorizon(entityId) {
  const query = new URLSearchParams({ entity_id: entityId }).toString();
  return fetchJSON(`/pricing/horizon?${query}`, { method: 'GET' });
}

export async function fetchForecasterMetrics() {
  return fetchJSON('/pricing/forecaster/metrics', { method: 'GET' });
}

export async function setPriceOverride(entityId, date, overridePrice, reason = '') {
  return fetchJSON('/pricing/override', {
    method: 'POST',
    body: JSON.stringify({
      entity_id: entityId,
      date,
      override_price: parseFloat(overridePrice),
      reason,
    }),
  });
}

export async function fetchOverrides(entityId) {
  const query = entityId ? `?entity_id=${entityId}` : '';
  return fetchJSON(`/pricing/overrides${query}`, { method: 'GET' });
}

export async function fetchEntities() {
  return fetchJSON('/entities', { method: 'GET' }).catch(() => [
    {
      entity_id: 'rmt_ca391f47',
      entity_name: 'Villa Mahal Resort Deluxe Room (rmt_ca391f47)',
      entity_type: 'room_type',
      floor_price: 2485.41,
      ceiling_price: 6130.68,
      max_daily_move_pct: 0.15,
    },
    {
      entity_id: 'far_5a8bce18',
      entity_name: 'UL-9879 Saver Economy Fare (far_5a8bce18)',
      entity_type: 'flight_fare',
      floor_price: 3200.0,
      ceiling_price: 9500.0,
      max_daily_move_pct: 0.20,
    },
  ]);
}

// ==========================================
// Traveller & Shared Endpoints
// ==========================================
export async function fetchTravellerSearch(date) {
  const query = new URLSearchParams({ date }).toString();
  return fetchJSON(`/traveller/search?${query}`, { method: 'GET' });
}

export async function logEvent(entityId, eventType, timestamp = new Date().toISOString(), leadTimeDays = 14, forDate = null) {
  return fetchJSON('/events', {
    method: 'POST',
    body: JSON.stringify({
      entity_id: entityId,
      event_type: eventType,
      timestamp,
      lead_time_days: parseInt(leadTimeDays, 10),
      for_date: forDate || undefined,
    }),
  });
}


export async function checkBackendHealth() {
  return fetchJSON('/health', { method: 'GET' });
}
