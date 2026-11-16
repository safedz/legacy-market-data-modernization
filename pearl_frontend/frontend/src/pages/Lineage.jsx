import { useState } from 'react';
import { useApi } from '../useApi.js';
import DataState from '../components/DataState.jsx';
import StatusPill from '../components/StatusPill.jsx';
import { Link, navigate } from '../router.jsx';
import { formatDateTime, humanize, isOrderId } from '../format.js';

export default function Lineage({ orderId = '' }) {
  const [input, setInput] = useState(orderId);
  const [formError, setFormError] = useState('');
  const valid = isOrderId(orderId);
  const { data, loading, error, reload } = useApi(`/api/lineage/${encodeURIComponent(orderId)}`, valid);

  function submit(e) {
    e.preventDefault();
    const text = input.trim();
    if (!isOrderId(text)) {
      setFormError('An order ID is a whole number, for example 16120456.');
      return;
    }
    setFormError('');
    navigate(`/lineage/${text}`);
  }

  return (
    <>
      <div className="pagehead">
        <h1>Order lineage</h1>
        <p>The journey of one order through ingestion, transformation, validation and loading.</p>
      </div>
      <form className="card" onSubmit={submit} style={{ flexDirection: 'row', flexWrap: 'wrap', alignItems: 'flex-end' }} noValidate>
        <div className="field" style={{ flex: '1 1 280px' }}>
          <label htmlFor="lid">Order ID</label>
          <input id="lid" className="input" inputMode="numeric" placeholder="For example 16120456" value={input} onChange={(e) => setInput(e.target.value)} aria-invalid={!!formError} />
        </div>
        <button className="btn" type="submit">Trace order</button>
        {formError && <span role="alert" style={{ flexBasis: '100%', color: 'var(--high)', fontSize: 14 }}>{formError}</span>}
      </form>

      {orderId && !valid && <div className="notice">“{orderId}” is not a valid order ID.</div>}
      {valid && (
        <section className="card">
          <div className="cardhead">
            <h2>Order {orderId}</h2>
            <Link to={`/trades`} className="rowlink small">Search trades</Link>
          </div>
          <DataState loading={loading} error={error} onRetry={reload}>
            {data && data.length === 0 && <div className="state">No lineage found for this order.</div>}
            {data && data.length > 0 && (
              <ol className="timeline">
                {data.map((step, i) => (
                  <li key={`${step.stage}-${i}`}>
                    <span className={`dot ${step.status === 'OK' ? '' : 'bad'}`} aria-hidden="true">{i + 1}</span>
                    <div className="tl-body">
                      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                        <span className="strong">{step.step}</span>
                        <StatusPill value={step.status} />
                        <span className="pill neutral">{humanize(step.stage)}</span>
                      </div>
                      <span>{step.description}</span>
                      {step.timestamp && <span className="small muted">{formatDateTime(step.timestamp)}</span>}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </DataState>
        </section>
      )}
    </>
  );
}
