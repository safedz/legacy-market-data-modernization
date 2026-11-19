import { useApi } from '../useApi.js';
import DataState from '../components/DataState.jsx';
import StatusPill from '../components/StatusPill.jsx';
import { formatDateTime, formatNumber, formatPercent, humanize } from '../format.js';

function Gate({ title, pass, children }) {
  return (
    <div className="gate">
      <div className="cardhead"><span className="strong">{title}</span><StatusPill value={pass ? 'PASS' : 'FAIL'} /></div>
      {children}
    </div>
  );
}

export default function Quality() {
  const { data: q, loading, error, reload } = useApi('/api/quality');
  const notRun = q && q.orderBookStatus === 'NOT_RUN';
  const violations = q ? Object.entries(q.lifecycleViolations ?? {}) : [];

  return (
    <>
      <div className="pagehead">
        <h1>Data quality</h1>
        <p>Independent checks on the loaded data: order-book reconciliation and order lifecycle rules.</p>
      </div>
      <DataState loading={loading} error={error} onRetry={reload}>
        {notRun && <div className="notice">The quality stage has not run yet. Run <code>python run_pipeline.py</code> to produce a report.</div>}
        {q && !notRun && (
          <>
            <section className="card">
              <div className="cardhead">
                <h2>Overall</h2>
                <span className="small muted">Batch {q.batchId} · {formatDateTime(q.generatedAt)}</span>
              </div>
              <div><StatusPill value={q.overallPass ? 'PASS' : 'FAIL'}>{q.overallPass ? 'ALL CHECKS PASS' : 'CHECKS FAILING'}</StatusPill></div>
            </section>

            <div className="gates">
              <Gate title="Order-book reconciliation" pass={q.orderBookStatus === 'PASS'}>
                <div className="stats">
                  <div className="stat"><b>{formatNumber(q.checked)}</b><span className="small muted">Checked</span></div>
                  <div className="stat"><b>{formatNumber(q.matched)}</b><span className="small muted">Matched</span></div>
                  <div className="stat"><b>{formatNumber(q.mismatched)}</b><span className="small muted">Mismatched</span></div>
                </div>
                <div>
                  <div className="small muted" style={{ marginBottom: 6 }}>Match rate {formatPercent(q.matchRate)}</div>
                  <div className="bar" role="img" aria-label={`Match rate ${formatPercent(q.matchRate)}`}><span style={{ width: formatPercent(q.matchRate, 2) }} /></div>
                </div>
                <div>
                  <div className="small muted" style={{ marginBottom: 6 }}>Coverage {formatPercent(q.coverage)}</div>
                  <div className="bar" role="img" aria-label={`Coverage ${formatPercent(q.coverage)}`}><span style={{ width: formatPercent(q.coverage, 2) }} /></div>
                </div>
              </Gate>
              <Gate title="Order lifecycle" pass={q.lifecyclePass}>
                <div className="stats">
                  <div className="stat"><b>{formatNumber(q.orphanEvents)}</b><span className="small muted">Orphan events</span></div>
                </div>
                {violations.length === 0 ? <span className="small muted">No lifecycle violations.</span> : (
                  <ul style={{ margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {violations.map(([name, n]) => <li key={name}>{humanize(name)}: <span className="strong">{formatNumber(n)}</span></li>)}
                  </ul>
                )}
              </Gate>
            </div>
            {q.orderBookStatus === 'SKIPPED' && <div className="notice">Order-book reconciliation was skipped because no order-book file was provided.</div>}
          </>
        )}
      </DataState>
    </>
  );
}
