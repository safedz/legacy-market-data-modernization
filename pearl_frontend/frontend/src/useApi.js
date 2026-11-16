import { useCallback, useEffect, useState } from 'react';
import { apiGet } from './api.js';
import { useAuth } from './auth.jsx';

/** Loads `path` with the signed-in user's credentials. Pass enabled=false to wait. */
export function useApi(path, enabled = true) {
  const { auth, logout } = useAuth();
  const [state, setState] = useState({ data: null, error: null, loading: enabled });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!enabled || !auth) {
      setState({ data: null, error: null, loading: false });
      return undefined;
    }
    const controller = new AbortController();
    setState({ data: null, error: null, loading: true });
    apiGet(path, auth.header, controller.signal)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => {
        if (error.name === 'AbortError') return;
        if (error.status === 401) {
          logout(); // credentials were revoked or changed
          return;
        }
        setState({ data: null, error, loading: false });
      });
    return () => controller.abort();
  }, [path, enabled, auth, logout, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}
