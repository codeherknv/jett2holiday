/**
 * Jett 2 Holiday - Backend API Client
 * Wraps all 4 core endpoints with fetch requests, error handling, and mock fallbacks.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchJSON(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || `API error: ${res.status} ${res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    console.warn(`[API Client Warning] Failed to reach ${url}:`, err.message);
    throw err;
  }
}

/**
 * 1. POST /pricing/calculate
 * @param {string} entityId - e.g. "htl_sng_001_deluxe"
 * @param {string} targetDate - e.g. "2026-10-15"
 */
export async function calculatePricing(entityId, targetDate) {
  return fetchJSON('/pricing/calculate', {
    method: 'POST',
    body: JSON.stringify({
      entity_id: entityId,
      target_date: targetDate,
    }),
  });
}

/**
 * 2. GET /pricing/explain?entity_id=&date=
 * @param {string} entityId - e.g. "htl_sng_001_deluxe"
 * @param {string} date - e.g. "2026-10-15"
 */
export async function explainPricing(entityId, date) {
  const query = new URLSearchParams({ entity_id: entityId, date }).toString();
  return fetchJSON(`/pricing/explain?${query}`, {
    method: 'GET',
  });
}

/**
 * 3. POST /pricing/simulate
 * @param {string} entityId - e.g. "htl_sng_001_deluxe"
 * @param {number} baseMultiplier - e.g. 1.15
 * @param {number} dailyMoveLimit - e.g. 0.20
 */
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

/**
 * 4. POST /events
 * @param {string} entityId
 * @param {string} eventType - "search" | "view" | "booking" | "cancellation" | "abandon"
 * @param {string} timestamp - ISO string
 * @param {number} leadTimeDays
 */
export async function logEvent(entityId, eventType, timestamp = new Date().toISOString(), leadTimeDays = 14) {
  return fetchJSON('/events', {
    method: 'POST',
    body: JSON.stringify({
      entity_id: entityId,
      event_type: eventType,
      timestamp,
      lead_time_days: parseInt(leadTimeDays, 10),
    }),
  });
}

/**
 * Health check & Metadata helpers
 */
export async function checkBackendHealth() {
  return fetchJSON('/health', { method: 'GET' });
}

export async function fetchEntities() {
  return fetchJSON('/entities', { method: 'GET' }).catch(() => [
    {
      entity_id: 'htl_sng_001_deluxe',
      entity_name: 'Dal Lake Luxury Heritage Resort (Deluxe)',
      entity_type: 'hotel_room',
      floor_price: 3500.0,
      ceiling_price: 7000.0,
      max_daily_move_pct: 0.15,
    },
    {
      entity_id: 'flt_del_srx_101_eco',
      entity_name: 'DEL -> SXR Express (Economy)',
      entity_type: 'flight_fare',
      floor_price: 4200.0,
      ceiling_price: 11500.0,
      max_daily_move_pct: 0.20,
    },
  ]);
}
