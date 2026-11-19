const CLASS = { HIGH: 'high', MEDIUM: 'med', FAIL: 'high', REJECTED: 'high', PASS: '', OK: '', NOT_RUN: 'neutral', SKIPPED: 'neutral' };

export default function StatusPill({ value, children }) {
  const key = String(value ?? '').toUpperCase();
  return <span className={`pill ${CLASS[key] ?? 'neutral'}`}>{children ?? key}</span>;
}
