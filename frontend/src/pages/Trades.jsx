import { useMemo, useState } from 'react';
import { useApi } from '../useApi.js';
import DataState from '../components/DataState.jsx';
import StatusPill from '../components/StatusPill.jsx';
import { Link } from '../router.jsx';
import { formatClock, formatNumber, humanize, isOrderId } from '../format.js';

const PILL = { SUBMIT: 'PASS', DELETE: 'MEDIUM', CANCEL_PARTIAL: 'MEDIUM', EXECUTE_VISIBLE: 'PASS', EXECUTE_HIDDEN: 'PASS' };

export default function Trades() {
  const [input, setInput] = useState('');
  const [orderId, setOrderId] = useState('');
  const [event, setEvent] = useState('ALL');
  const [formError, setFormError] = useState('');

  const path = orderId ? `/api/trades?orderId=${encodeURIComponent(orderId)}` : '/api/trades';
  const { data, loading, error, reload } = useApi(path);
  const rows = data ?? [];
  const events = useMemo(() => [...new Set(rows.map((r) => r.eventType))].sort(), [rows]);
  const shown = event === 'ALL' ? rows : rows.filter((r) => r.eventType === event);

  function search(e) {
    e.preventDefault();
    const text = input.trim();
    if (text && !isOrderId(text)) {
      setFormError('An order ID is a whole number, for example 16120456.');
      return;
    }
    setFormError('');
    setEvent('ALL');
    setOrderId(text);
  }

  return (
    <>
      <div className="pagehead">
        <h1>Trade search</h1>
        <p>Look up every message for an order, or browse the valid messages in the order they arrived.</p>
      </div>
      <form className="card" onSubmit={search} style={{ flexDirection: 'row', flexWrap: 'wrap', alignItems: 'flex-end' }} noValidate>
        <div className="field" style={{ flex: '1 1 280px' }}>
          <label htmlFor="oid">Order ID</label>
          <input id="oid" className="input" inputMode="numeric" placeholder="For example 16120456" value={input} onChange={(e) => setInput(e.target.value)} aria-invalid={!!formError} />
        </div>
        <div className="field" style={{ flex: '0 0 220px' }}>
          <label htmlFor="evt">Event type</label>
          <select id="evt" className="input" value={event} onChange={(e) => setEvent(e.target.value)}>
            <option value="ALL">All events</option>
            {events.map((ev) => <option key={ev} value={ev}>{humanize(ev)}</option>)}
          </select>
        </div>
        <button className="btn" type="submit">Search</button>
        {formError && <span role="alert" style={{ flexBasis: '100%', color: 'var(--high)', fontSize: 14 }}>{formError}</span>}
      </form>

      <section className="card">
        <div className="cardhead">
          <h2>{orderId ? `Messages for order ${orderId}` : 'All valid messages'}</h2>
          {!loading && !error && (
            <span className="small muted">
              {orderId ? `${formatNumber(shown.length)} messages` : `Showing the first ${formatNumber(rows.length)} loaded (the backend returns at most 1,000)`}
            </span>
          )}
        </div>
        <DataState loading={loading} error={error} onRetry={reload}>
          {shown.length === 0 ? (
            <div className="state">{orderId ? 'No messages found for this order.' : 'No messages loaded yet. Run the pipeline first.'}</div>
          ) : (
            <div className="tablewrap">
              <table>
                <thead><tr><th>Order ID</th><th>Time (seconds)</th><th>Event</th><th className="num">Size</th><th className="num">Price</th><th>Side</th><th /></tr></thead>
                <tbody>
                  {shown.map((r, i) => (
                    <tr key={`${r.orderId}-${r.time}-${i}`}>
                      <td className="strong">{r.orderId}</td>
                      <td><div>{r.time}</div><div className="small muted">{formatClock(r.time)}</div></td>
                      <td><StatusPill value={PILL[r.eventType] ?? 'NOT_RUN'}>{String(r.eventType).replace(/_/g, ' ')}</StatusPill></td>
                      <td className="num">{formatNumber(r.size)}</td>
                      <td className="num">${Number(r.price).toFixed(2)}</td>
                      <td className={r.direction === 'BUY' ? 'buy' : 'sell'}>{r.direction}</td>
                      <td className="num"><Link to={`/lineage/${r.orderId}`} className="rowlink">View lineage</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <span className="small muted">Prices are in dollars. Time is seconds after midnight, exchange local time, not UTC.</span>
        </DataState>
      </section>
    </>
  );
}
