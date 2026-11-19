import { useEffect } from 'react';
import { useAuth } from './auth.jsx';
import { matchRoute, navigate, useHashPath } from './router.jsx';
import Layout from './components/Layout.jsx';
import Landing from './pages/Landing.jsx';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Alerts from './pages/Alerts.jsx';
import Trades from './pages/Trades.jsx';
import Rejected from './pages/Rejected.jsx';
import Lineage from './pages/Lineage.jsx';
import Quality from './pages/Quality.jsx';
import DataLake from './pages/DataLake.jsx';

const PROTECTED = [
  ['/dashboard', () => <Dashboard />],
  ['/alerts', () => <Alerts />],
  ['/trades', () => <Trades />],
  ['/rejected', () => <Rejected />],
  ['/lineage', () => <Lineage />],
  ['/lineage/:orderId', (p) => <Lineage key={p.orderId} orderId={p.orderId} />],
  ['/quality', () => <Quality />],
    ['/lake', () => <DataLake />],
];

export default function App() {
  const path = useHashPath();
  const { auth } = useAuth();

  const hit = PROTECTED.map(([pattern, render]) => [matchRoute(pattern, path), render]).find(([m]) => m);
  const needsLogin = !!hit && !auth;

  useEffect(() => {
    if (needsLogin) navigate('/login');
    else if (path === '/login' && auth) navigate('/dashboard');
  }, [needsLogin, path, auth]);

  if (path === '/') return <Landing />;
  if (path === '/login') return auth ? null : <Login />;
  if (hit && auth) return <Layout>{hit[1](hit[0])}</Layout>;
  if (needsLogin) return null;
  return (
    <div className="login"><div className="formside" style={{ flexDirection: 'column', gap: 16 }}>
      <h1>Page not found</h1><a className="btn" href="#/">Go home</a>
    </div></div>
  );
}
