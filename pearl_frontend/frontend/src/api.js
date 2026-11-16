// Talks to the Spring Boot backend. Endpoints (all GET, HTTP Basic auth, role ANALYST or ADMIN):
//   /api/pipeline/summary      -> { sourceRecords, loadedRecords, rejectedRecords, reconciled, lastRun }
//   /api/quality               -> { batchId, generatedAt, orderBookStatus, checked, matched, mismatched,
//                                   matchRate, coverage, lifecyclePass, orphanEvents,
//                                   lifecycleViolations{}, overallPass }
//   /api/surveillance/alerts   -> [{ id, type, orderId, severity, description, detectedAt }]
//   /api/trades[?orderId=]     -> [{ orderId, time, eventType, size, price, direction }]
//   /api/rejected-records      -> [{ id, orderId, reason, sourceFile, lineNumber }]
//   /api/lineage/{orderId}     -> [{ step, stage, description, status, timestamp }]

export const API_BASE = (import.meta.env?.VITE_API_URL || 'http://localhost:8080').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** HTTP Basic header. Works for non-Latin-1 characters too. */
export function basicHeader(username, password) {
  const bytes = new TextEncoder().encode(`${username}:${password}`);
  let binary = '';
  bytes.forEach((b) => { binary += String.fromCharCode(b); });
  return `Basic ${btoa(binary)}`;
}

function messageFor(status) {
  if (status === 401) return 'Incorrect username or password.';
  if (status === 403) return 'Your account is not allowed to see this.';
  if (status === 400) return 'The request was not valid. Check the order ID.';
  if (status >= 500) return 'The backend reported an error. Check its console.';
  return `Unexpected response (${status}).`;
}

export async function apiGet(path, authHeader, signal) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { Authorization: authHeader, Accept: 'application/json' },
      signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError(0, `Cannot reach the backend at ${API_BASE}. Is it running?`);
  }
  if (!response.ok) throw new ApiError(response.status, messageFor(response.status));
  return response.json();
}
