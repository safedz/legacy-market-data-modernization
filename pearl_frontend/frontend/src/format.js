// Small, dependency-free helpers shared by the pages. Covered by src/format.test.js.

export function formatNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString('en-US') : '-';
}

/** 0.904 -> "90.4%" */
export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || value === '') return '-';
  const n = Number(value);
  return Number.isFinite(n) ? `${(n * 100).toFixed(digits)}%` : '-';
}

/** Seconds after midnight ("34200.004241176") -> "09:30:00.004241". Exchange local time, not UTC. */
export function formatClock(secondsText) {
  const seconds = Number(secondsText);
  if (secondsText === '' || secondsText === null || !Number.isFinite(seconds) || seconds < 0) return '';
  const whole = Math.floor(seconds);
  const micro = Math.floor((seconds - whole) * 1e6);
  const pad = (n, width = 2) => String(n).padStart(width, '0');
  const h = Math.floor(whole / 3600) % 24;
  const m = Math.floor((whole % 3600) / 60);
  const s = whole % 60;
  return `${pad(h)}:${pad(m)}:${pad(s)}.${pad(micro, 6)}`;
}

/** ISO or PostgreSQL timestamp text -> "14 Nov 2026, 19:47". Anything unparseable is returned unchanged. */
export function formatDateTime(text) {
  if (!text) return '';
  const date = new Date(String(text).replace(' ', 'T'));
  if (Number.isNaN(date.getTime())) return String(text);
  return date.toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

/** Order IDs are whole numbers of 1 to 20 digits (same rule as the backend). */
export function isOrderId(text) {
  return /^\d{1,20}$/.test(String(text ?? '').trim());
}

/** "EXECUTE_VISIBLE" -> "Execute visible" */
export function humanize(code) {
  const text = String(code ?? '').replace(/_/g, ' ').toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function countBy(items, keyFn) {
  const counts = {};
  for (const item of items) {
    const key = keyFn(item);
    counts[key] = (counts[key] || 0) + 1;
  }
  return counts;
}

/** Page numbers start at 1. The page is clamped into range. */
export function paginate(items, page, size) {
  const pages = Math.max(1, Math.ceil(items.length / size));
  const current = Math.min(Math.max(1, page), pages);
  return { slice: items.slice((current - 1) * size, current * size), pages, current };
}

export const PIPELINE_NOT_READY = ['pipeline not run yet', 'database not loaded yet'];

export function isPipelineReady(lastRun) {
  return !PIPELINE_NOT_READY.includes(lastRun);
}
