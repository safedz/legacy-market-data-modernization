import { useMemo, useState } from 'react';
import { useApi } from '../useApi.js';
import DataState from '../components/DataState.jsx';
import StatusPill from '../components/StatusPill.jsx';
import Pager from '../components/Pager.jsx';
import { Link } from '../router.jsx';
import { countBy, formatDateTime, humanize, paginate } from '../format.js';

const SIZE = 25;
const TYPES = ['ALL', 'SPOOFING', 'RAPID_CANCEL'];

export default function Alerts() {
  const { data, loading, error, reload } = useApi('/api/surveillance/alerts');
  const [type, setType] = useState('ALL');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);

  const all = data ?? [];
  const counts = useMemo(() => countBy(all, (a) => a.type), [all]);
  const filtered = useMemo(() => {
    const q = query.trim();
    return all.filter((a) => (type === 'ALL' || a.type === type) && (!q || String(a.orderId).includes(q)));
  }, [all, type, query]);
  const { slice, pages, current } = paginate(filtered, page, SIZE);

  return (
    <>
      <div className="pagehead">
        <h1>Surveillance alerts</h1>
        <p>Spoofing and rapid-cancel patterns found in the loaded messages, highest severity first.</p>
      </div>
      <section className="card">
        <div className="cardhead">
          <div className="chips" role="group" aria-label="Alert type">
            {TYPES.map((t) => (
              <button key={t} type="button" className={`chip ${type === t ? 'on' : ''}`} aria-pressed={type === t}
                      onClick={() => { setType(t); setPage(1); }}>
                {t === 'ALL' ? `All (${all.length})` : `${humanize(t)} (${counts[t] || 0})`}
              </button>
            ))}
          </div>
          <div className="field" style={{ width: 240 }}>
            <input className="input" style={{ height: 40 }} aria-label="Search by order ID" placeholder="Search order ID"
                   value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} />
          </div>
        </div>
        <DataState loading={loading} error={error} onRetry={reload}>
          {filtered.length === 0 ? (
            <div className="state">{all.length === 0 ? 'No alerts were raised for this data.' : 'No alerts match these filters.'}</div>
          ) : (
            <div className="tablewrap">
              <table>
                <thead><tr><th>Type</th><th>Order ID</th><th>Severity</th><th>Description</th><th>Detected</th><th /></tr></thead>
                <tbody>
                  {slice.map((a) => (
                    <tr key={a.id}>
                      <td className="strong">{humanize(a.type)}</td>
                      <td>{a.orderId}</td>
                      <td><StatusPill value={a.severity} /></td>
                      <td>{a.description}</td>
                      <td>{formatDateTime(a.detectedAt)}</td>
                      <td className="num"><Link to={`/lineage/${a.orderId}`} className="rowlink">View lineage</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Pager current={current} pages={pages} total={filtered.length} size={SIZE} onChange={setPage} />
          {all.length >= 1000 && <span className="small muted">The backend returns at most 1,000 alerts, so counts above cover those only.</span>}
        </DataState>
      </section>
    </>
  );
}
