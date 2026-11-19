export default function Pager({ current, pages, total, size, onChange }) {
  if (total <= size) return null;
  const from = (current - 1) * size + 1;
  const to = Math.min(current * size, total);
  return (
    <div className="pager">
      <span className="small muted">{from}–{to} of {total}</span>
      <div className="chips">
        <button type="button" className="btn secondary small" disabled={current <= 1} onClick={() => onChange(current - 1)}>Previous</button>
        <span className="small muted" style={{ alignSelf: 'center' }}>Page {current} of {pages}</span>
        <button type="button" className="btn secondary small" disabled={current >= pages} onClick={() => onChange(current + 1)}>Next</button>
      </div>
    </div>
  );
}
