import { useAuth } from '../auth.jsx';
import { Link, NavLink } from '../router.jsx';
import Logo from './Logo.jsx';

const I = { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true };
const ICONS = {
  dashboard: <svg {...I}><rect x="3" y="3" width="7" height="9" rx="1" /><rect x="14" y="3" width="7" height="5" rx="1" /><rect x="14" y="12" width="7" height="9" rx="1" /><rect x="3" y="16" width="7" height="5" rx="1" /></svg>,
  alerts: <svg {...I}><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></svg>,
  trades: <svg {...I}><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>,
  rejected: <svg {...I}><circle cx="12" cy="12" r="9" /><path d="m5.6 5.6 12.8 12.8" /></svg>,
  lineage: <svg {...I}><circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="18" r="2.5" /><path d="M8.5 6H15a3 3 0 0 1 0 6H9a3 3 0 0 0 0 6h6.5" /></svg>,
  quality: <svg {...I}><path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z" /><path d="m9 12 2 2 4-4" /></svg>,
  lake: <svg {...I}><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" /><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" /></svg>,
  
};
const NAV = [
  ['/dashboard', 'Dashboard', 'dashboard'],
  ['/alerts', 'Surveillance alerts', 'alerts'],
  ['/trades', 'Trade search', 'trades'],
  ['/rejected', 'Rejected records', 'rejected'],
  ['/lineage', 'Order lineage', 'lineage'],
  ['/quality', 'Data quality', 'quality'],
  ['/lake', 'Data lake', 'lake'],
];

export default function Layout({ children }) {
  const { auth, logout } = useAuth();
  const name = auth?.user ?? '';
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link to="/" className="brand"><Logo /> Pearl Protocol</Link>
        <nav aria-label="Main">
          {NAV.map(([to, label, icon]) => (
            <NavLink key={to} to={to} className="navlink">{ICONS[icon]}{label}</NavLink>
          ))}
        </nav>
        <div className="userchip">
          <div className="avatar">{name.charAt(0).toUpperCase()}</div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>{name}</span>
            <button type="button" className="linkbtn" onClick={logout}>Sign out</button>
          </div>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
