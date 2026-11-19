import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { apiGet, basicHeader } from './api.js';
import { navigate } from './router.jsx';

const KEY = 'pearl.auth';
const AuthContext = createContext(null);

function readStored() {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function store(value) {
  try {
    if (value) window.sessionStorage.setItem(KEY, JSON.stringify(value));
    else window.sessionStorage.removeItem(KEY);
  } catch {
    /* storage can be blocked; the session then lasts until the tab reloads */
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(readStored);

  // The backend has no login endpoint (HTTP Basic), so signing in means proving the
  // credentials work with a real request.
  const login = useCallback(async (username, password) => {
    const header = basicHeader(username.trim(), password);
    await apiGet('/api/pipeline/summary', header);
    const next = { user: username.trim(), header };
    store(next);
    setAuth(next);
  }, []);

  const logout = useCallback(() => {
    store(null);
    setAuth(null);
    navigate('/login');
  }, []);

  const value = useMemo(() => ({ auth, login, logout }), [auth, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
