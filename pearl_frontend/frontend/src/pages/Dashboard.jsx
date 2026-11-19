import { useApi } from '../useApi.js';
import DataState from '../components/DataState.jsx';
import StatusPill from '../components/StatusPill.jsx';
import { Link } from '../router.jsx';
import {
  formatDateTime,
  formatNumber,
  formatPercent,
  humanize,
  isPipelineReady
} from '../format.js';

function Kpi({ label, value, note }) {
  return (
    <div className="kpi">
      <span className="small muted">{label}</span>
      <span className="value">{value}</span>
      {note && <span className="small muted">{note}</span>}
    </div>
  );
}

export default function Dashboard() {
  const summary = useApi('/api/pipeline/summary');
  const quality = useApi('/api/quality');
  const alerts = useApi('/api/surveillance/alerts');
  const analytics = useApi('/api/analytics/summary');

  const s = summary.data;
  const q = quality.data;
  const a = analytics.data;
  const events = a?.eventDistribution || [];
  const maxEventCount = Math.max(1, ...events.map((event) => event.count));

  return (
    <>
      <div className="pagehead">
        <h1>Dashboard</h1>
        <p>Where the latest pipeline run stands.</p>
      </div>

      <DataState loading={summary.loading} error={summary.error} onRetry={summary.reload}>
        {s && !isPipelineReady(s.lastRun) && (
          <div className="notice">
            The data is not available yet ({s.lastRun}). Run the pipeline, then load the database if the backend reads from it.
          </div>
        )}
        {s && (
          <div className="kpis">
            <Kpi label="Source records" value={formatNumber(s.sourceRecords)} />
            <Kpi label="Loaded records" value={formatNumber(s.loadedRecords)} />
            <Kpi label="Rejected records" value={formatNumber(s.rejectedRecords)} />
            <div className="kpi">
              <span className="small muted">Reconciliation</span>
              <span>
                <StatusPill value={s.reconciled ? 'PASS' : 'FAIL'}>
                  {s.reconciled ? 'RECONCILED' : 'NOT RECONCILED'}
                </StatusPill>
              </span>
              <span className="small muted">
                Last run: {isPipelineReady(s.lastRun) ? formatDateTime(s.lastRun) : '-'}
              </span>
            </div>
          </div>
        )}
      </DataState>

      <div className="two">
        <section className="card" aria-labelledby="dq">
          <div className="cardhead">
            <h2 id="dq">Data quality</h2>
            <Link to="/quality" className="rowlink">Details</Link>
          </div>
          <DataState loading={quality.loading} error={quality.error} onRetry={quality.reload}>
            {q && (
              <>
                <div>
                  <StatusPill value={q.overallPass ? 'PASS' : q.orderBookStatus === 'NOT_RUN' ? 'NOT_RUN' : 'FAIL'}>
                    {q.orderBookStatus === 'NOT_RUN' ? 'NOT RUN' : q.overallPass ? 'ALL CHECKS PASS' : 'CHECKS FAILING'}
                  </StatusPill>
                </div>
                <div className="stats">
                  <div className="stat">
                    <b>{formatPercent(q.matchRate)}</b>
                    <span className="small muted">Order-book match</span>
                  </div>
                  <div className="stat">
                    <b>{formatPercent(q.coverage)}</b>
                    <span className="small muted">Coverage</span>
                  </div>
                  <div className="stat">
                    <b>{formatNumber(q.orphanEvents)}</b>
                    <span className="small muted">Orphan events</span>
                  </div>
                </div>
              </>
            )}
          </DataState>
        </section>

        <section className="card" aria-labelledby="al">
          <div className="cardhead">
            <h2 id="al">Latest alerts</h2>
            <Link to="/alerts" className="rowlink">View all</Link>
          </div>
          <DataState loading={alerts.loading} error={alerts.error} onRetry={alerts.reload}>
            {alerts.data && alerts.data.length === 0 && <div className="state">No alerts.</div>}
            {alerts.data && alerts.data.length > 0 && (
              <ul style={{
                listStyle: 'none',
                margin: 0,
                padding: 0,
                display: 'flex',
                flexDirection: 'column',
                gap: 12
              }}>
                {alerts.data.slice(0, 5).map((alert) => (
                  <li key={alert.id} style={{
                    display: 'flex',
                    gap: 12,
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <span>
                      <span className="strong">{humanize(alert.type)}</span>{' '}
                      <span className="muted small">order {alert.orderId}</span>
                    </span>
                    <StatusPill value={alert.severity} />
                  </li>
                ))}
              </ul>
            )}
          </DataState>
        </section>
      </div>

      <section className="card" aria-labelledby="duckdb-analytics" style={{ marginTop: 20 }}>
        <div className="cardhead">
          <div>
            <h2 id="duckdb-analytics">Parquet analytics</h2>
            <p className="small muted">Analytical queries powered by DuckDB on the curated data lake.</p>
          </div>
          <button className="btn" type="button" onClick={analytics.reload}>
            Refresh
          </button>
        </div>

        <DataState
          loading={analytics.loading}
          error={analytics.error}
          onRetry={analytics.reload}
        >
          {a && (
            <>
              <div className="kpis">
                <Kpi label="Analysed records" value={formatNumber(a.totalRecords)} />
                <Kpi label="Average price" value={Number(a.averagePrice).toFixed(4)} />
                <Kpi label="Highest price" value={Number(a.highestPrice).toFixed(2)} />
                <Kpi label="Average order size" value={formatNumber(a.averageOrderSize)} />
                <Kpi label="Largest order" value={formatNumber(a.largestOrder)} />
              </div>

              <div style={{ marginTop: 28 }}>
                <h3 style={{ marginBottom: 16 }}>Event distribution</h3>
                {events.map((event) => (
                  <div key={event.eventLabel} style={{ marginBottom: 16 }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: 12,
                      marginBottom: 6
                    }}>
                      <span className="small strong">{humanize(event.eventLabel)}</span>
                      <span className="small muted">{formatNumber(event.count)}</span>
                    </div>
                    <div style={{
                      height: 10,
                      background: 'var(--border, #e5e7eb)',
                      borderRadius: 10,
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${(event.count / maxEventCount) * 100}%`,
                        height: '100%',
                        background: 'var(--accent, #64748b)',
                        borderRadius: 10
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </DataState>
      </section>
    </>
  );
}
