import { useState } from 'react';
import { useApi } from '../useApi.js';
import DataState from '../components/DataState.jsx';
import { formatDateTime, formatNumber, humanize } from '../format.js';

function formatBytes(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) return '-';
  if (n < 1024) return `${n} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let size = n / 1024;
  let i = 0;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i += 1;
  }
  return `${size.toFixed(1)} ${units[i]}`;
}

function cellText(value) {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'number') return formatNumber(value);
  return String(value);
}

function StorageCards() {
  const { data: s, loading, error, reload } = useApi('/api/lake/summary');
  return (
    <section className="card">
      <div className="cardhead"><h2>Storage</h2></div>
      <DataState loading={loading} error={error} onRetry={reload}>
        {s && !s.available && (
          <div className="notice">
            The data lake is empty. Run <code>python run_pipeline.py</code> in the project folder to create it.
          </div>
        )}
        {s && s.available && (
          <>
            <div className="lake-cards">
              <div className="lake-stat"><b>{formatNumber(s.rawFiles)}</b><span className="small muted">Raw files</span></div>
              <div className="lake-stat"><b>{formatNumber(s.curatedFiles)}</b><span className="small muted">Curated files</span></div>
              <div className="lake-stat"><b>{formatBytes(s.totalBytes)}</b><span className="small muted">Total size</span></div>
              <div className="lake-stat"><b>{formatNumber(s.curatedRecords)}</b><span className="small muted">Curated records</span></div>
            </div>
            <div className="small muted" style={{ marginTop: 12 }}>Read with DuckDB from {s.curatedFile}</div>
          </>
        )}
      </DataState>
    </section>
  );
}

function FilesTable() {
  const { data: files, loading, error, reload } = useApi('/api/lake/files');
  return (
    <section className="card">
      <div className="cardhead"><h2>Files</h2></div>
      <DataState loading={loading} error={error} onRetry={reload}>
        {files && files.length === 0 && <span className="small muted">No files in the lake yet.</span>}
        {files && files.length > 0 && (
          <div className="lake-table-wrap">
            <table className="lake-table">
              <thead>
                <tr><th>Zone</th><th>File</th><th>Batch</th><th>Size</th><th>Modified</th></tr>
              </thead>
              <tbody>
                {files.map((f) => (
                  <tr key={`${f.zone}/${f.batchId}/${f.name}`}>
                    <td>{humanize(f.zone)}</td>
                    <td>{f.name}</td>
                    <td>{f.batchId || '-'}</td>
                    <td className="num">{formatBytes(f.sizeBytes)}</td>
                    <td>{formatDateTime(f.modifiedAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </DataState>
    </section>
  );
}

function QueryExplorer() {
  const queries = useApi('/api/lake/queries');
  const [name, setName] = useState('');
  const result = useApi(`/api/lake/query/${name}`, name !== '');
  const r = result.data;
  const picked = queries.data ? queries.data.find((q) => q.name === name) : null;

  return (
    <section className="card">
      <div className="cardhead"><h2>Query explorer</h2></div>
      <DataState loading={queries.loading} error={queries.error} onRetry={queries.reload}>
        {queries.data && (
          <>
            <label className="small muted" htmlFor="lake-query">Choose a query to run on the Parquet file</label>
            <div style={{ margin: '6px 0 14px' }}>
              <select id="lake-query" className="lake-select" value={name} onChange={(e) => setName(e.target.value)}>
                <option value="">Select a query...</option>
                {queries.data.map((q) => (
                  <option key={q.name} value={q.name}>{q.description}</option>
                ))}
              </select>
            </div>
          </>
        )}
      </DataState>

      {name !== '' && (
        <DataState loading={result.loading} error={result.error} onRetry={result.reload}>
          {r && (
            <>
              <div className="small muted" style={{ marginBottom: 8 }}>
                {picked ? picked.description : r.description} · {formatNumber(r.rows.length)} rows
              </div>
              <div className="lake-table-wrap">
                <table className="lake-table">
                  <thead>
                    <tr>{r.columns.map((c) => <th key={c}>{humanize(c)}</th>)}</tr>
                  </thead>
                  <tbody>
                    {r.rows.map((row, i) => (
                      <tr key={i}>
                        {row.map((v, j) => (
                          <td key={j} className={typeof v === 'number' ? 'num' : undefined}>{cellText(v)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </DataState>
      )}
    </section>
  );
}

export default function DataLake() {
  return (
    <>
      <div className="pagehead">
        <h1>Data lake</h1>
        <p>Raw and curated files in the lake, queried live with DuckDB.</p>
      </div>
      <StorageCards />
      <FilesTable />
      <QueryExplorer />
    </>
  );
}