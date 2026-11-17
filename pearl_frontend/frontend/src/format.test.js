import test from 'node:test';
import assert from 'node:assert/strict';
import {
  countBy, formatClock, formatDateTime, formatNumber, formatPercent, humanize,
  isOrderId, isPipelineReady, paginate,
} from './format.js';

test('formatNumber adds thousands separators', () => {
  assert.equal(formatNumber(118497), '118,497');
  assert.equal(formatNumber('107164'), '107,164');
  assert.equal(formatNumber(undefined), '-');
});

test('formatPercent', () => {
  assert.equal(formatPercent(1), '100.0%');
  assert.equal(formatPercent(0.9043, 1), '90.4%');
  assert.equal(formatPercent(null), '-');
});

test('formatClock converts seconds after midnight', () => {
  assert.equal(formatClock('34200.004241176'), '09:30:00.004241');
  assert.equal(formatClock(34200), '09:30:00.000000');
  assert.equal(formatClock('34200.201743336'), '09:30:00.201743');
  assert.equal(formatClock(''), '');
  assert.equal(formatClock('abc'), '');
  assert.equal(formatClock(-1), '');
});

test('formatDateTime keeps unparseable text and formats real dates', () => {
  assert.equal(formatDateTime('pipeline not run yet'), 'pipeline not run yet');
  assert.equal(formatDateTime(''), '');
  assert.match(formatDateTime('2026-11-14 19:47:39.84735+05:30'), /Nov 2026/);
});

test('isOrderId matches the backend rule', () => {
  assert.equal(isOrderId('16120456'), true);
  assert.equal(isOrderId(' 16120456 '), true);
  assert.equal(isOrderId('12ab'), false);
  assert.equal(isOrderId(''), false);
  assert.equal(isOrderId('1'.repeat(21)), false);
});

test('humanize', () => {
  assert.equal(humanize('EXECUTE_VISIBLE'), 'Execute visible');
  assert.equal(humanize('SPOOFING'), 'Spoofing');
});

test('countBy', () => {
  assert.deepEqual(countBy([{ s: 'HIGH' }, { s: 'HIGH' }, { s: 'MEDIUM' }], (x) => x.s), { HIGH: 2, MEDIUM: 1 });
});

test('paginate clamps the page', () => {
  const items = Array.from({ length: 53 }, (_, i) => i);
  assert.equal(paginate(items, 1, 25).slice.length, 25);
  assert.equal(paginate(items, 3, 25).slice.length, 3);
  assert.equal(paginate(items, 99, 25).current, 3);
  assert.equal(paginate(items, 0, 25).current, 1);
  assert.equal(paginate([], 1, 25).pages, 1);
});

test('isPipelineReady', () => {
  assert.equal(isPipelineReady('pipeline not run yet'), false);
  assert.equal(isPipelineReady('database not loaded yet'), false);
  assert.equal(isPipelineReady('2026-11-14T14:17:39Z'), true);
});
