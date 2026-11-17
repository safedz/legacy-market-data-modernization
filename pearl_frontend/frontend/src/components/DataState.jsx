/** Shows a spinner, an error with Retry, or its children once data has loaded. */
export default function DataState({ loading, error, onRetry, children }) {
  if (loading) {
    return (
      <div className="state" role="status" aria-live="polite">
        <div className="spinner" />
        <span>Loading…</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="state error" role="alert">
        <span>{error.message}</span>
        {onRetry && <button type="button" className="btn secondary small" onClick={onRetry}>Try again</button>}
      </div>
    );
  }
  return children;
}
