import { useApi } from '../useApi.js';
import DataState from './DataState.jsx';
import { formatNumber, humanize } from '../format.js';
import './analytics.css';

const money = (n, digits = 2) => `$${Number(n).toFixed(digits)}`;
const decimals = (n, digits = 2) => Number(n).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });

function Metric({ label, value, note }) {
  return (
    <div className="metric">
      <span className="small muted">{label}</span>
      <span className="metric-value">{value}</span>
      {note && <span className="small muted">{note}</span>}
    </div>
  );
}


function EventChart({ rows, total }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <ul className="hbars" aria-label="Messages per event type">
      {rows.map((r) => (
        <li key={r.event}>
          <span className="hbar-label">{humanize(r.event)}</span>
          <span className="hbar-track" aria-hidden="true">
            <span className="hbar-fill" style={{ width: `${(r.count / max) * 100}%` }} />
          </span>
          <span className="hbar-value">
            {formatNumber(r.count)}
            <span className="small muted"> · {total ? ((r.count / total) * 100).toFixed(1) : '0.0'}%</span>
          </span>
        </li>
      ))}
    </ul>
  );
}


function Histogram({ buckets, caption }) {
  const max = Math.max(1, ...buckets.map((b) => b.count));
  return (
    <figure className="hist-figure">
      <div className="hist" role="list" aria-label={caption}>
        {buckets.map((b) => (
          <div className="hist-col" role="listitem" key={b.label} title={`${b.range}: ${formatNumber(b.count)} messages`}>
            <span className="hist-count">{formatNumber(b.count)}</span>
            <span className="hist-bar" style={{ height: `${b.count > 0 ? Math.max(2, (b.count / max) * 100) : 0}%` }} />
            <span className="hist-label">{b.label}</span>
          </div>
        ))}
      </div>
      <figcaption className="small muted">{caption}</figcaption>
    </figure>
  );
}

export default function AnalyticsPanel() {
  const { data: a, loading, error, reload } = useApi('/api/analytics/summary');
  return (
    <section className="card" aria-labelledby="analytics-title">
      <div className="cardhead">
        <h2 id="analytics-title">Market analytics</h2>
        <span className="small muted">Calculated with DuckDB from the curated Parquet file</span>
      </div>
      <DataState loading={loading} error={error} onRetry={reload}>
        {a && (
          <>
            <div className="metrics">
              <Metric label="Total records" value={formatNumber(a.totalRecords)} note={`${formatNumber(a.duplicateRows)} flagged duplicates`} />
              <Metric label="Average price" value={money(a.avgPrice, 4)} />
              <Metric label="Highest price" value={money(a.maxPrice)} note={`Lowest ${money(a.minPrice)}`} />
              <Metric label="Average order size" value={decimals(a.avgOrderSize)} note="shares" />
              <Metric label="Largest order" value={formatNumber(a.largestOrder)} note="shares" />
            </div>
            <div className="chart-grid">
              <div className="chart">
                <h3>Event distribution</h3>
                <EventChart rows={a.eventCounts} total={a.totalRecords} />
              </div>
              <div className="chart">
                <h3>Price distribution</h3>
                <Histogram buckets={a.priceBuckets} caption="Messages by price (dollars, start of each range)" />
              </div>
              <div className="chart">
                <h3>Order-size distribution</h3>
                <Histogram buckets={a.sizeBuckets} caption="Messages by order size (shares)" />
              </div>
            </div>
          </>
        )}
      </DataState>
    </section>
  );
}
