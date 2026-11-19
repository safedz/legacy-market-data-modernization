import { useMemo } from 'react';
import { useApi } from '../useApi.js';
import DataState from '../components/DataState.jsx';
import { Link } from '../router.jsx';
import { countBy, formatNumber } from '../format.js';

export default function Rejected() {
  const { data, loading, error, reload } = useApi('/api/rejected-records');
  const rows = data ?? [];
  const byReason = useMemo(
    () => Object.entries(countBy(rows, (r) => r.reason)).sort((a, b) => b[1] - a[1]),
    [rows],
  );

  return (
    <>
      <div className="pagehead">
        <h1>Rejected records</h1>
        <p>Messages that failed a validation rule, with the reason and the exact place in the source file.</p>
      </div>
      <DataState loading={loading} error={error} onRetry={reload}>
        {rows.length === 0 ? (
          <section className="card"><div className="state">No records were rejected. Every source message passed validation.</div></section>
        ) : (
          <>
            <section className="card">
              <h2>Reasons</h2>
              <div className="chips">
                {byReason.map(([reason, n]) => <span key={reason} className="pill high">{reason} · {formatNumber(n)}</span>)}
              </div>
            </section>
            <section className="card">
              <div className="cardhead"><h2>All rejected records</h2><span className="small muted">{formatNumber(rows.length)} records</span></div>
              <div className="tablewrap">
                <table>
                  <thead><tr><th>Order ID</th><th>Reason</th><th>Source file</th><th className="num">Line</th><th /></tr></thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id}>
                        <td className="strong">{r.orderId}</td>
                        <td>{r.reason}</td>
                        <td>{r.sourceFile}</td>
                        <td className="num">{formatNumber(r.lineNumber)}</td>
                        <td className="num"><Link to={`/lineage/${r.orderId}`} className="rowlink">View lineage</Link></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </DataState>
    </>
  );
}
