// A tiny hash router (#/dashboard). It needs no library and works on any static host.
import { useEffect, useState } from 'react';

export function currentPath() {
  const hash = window.location.hash.replace(/^#/, '');
  return hash.split('?')[0] || '/';
}

export function useHashPath() {
  const [path, setPath] = useState(currentPath);
  useEffect(() => {
    const onChange = () => setPath(currentPath());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return path;
}

export function navigate(to) {
  window.location.hash = to;
}

export function Link({ to, children, ...rest }) {
  return <a href={`#${to}`} {...rest}>{children}</a>;
}

export function NavLink({ to, className = '', activeClassName = 'active', children, ...rest }) {
  const path = useHashPath();
  const active = path === to || path.startsWith(`${to}/`);
  return (
    <a href={`#${to}`} className={`${className} ${active ? activeClassName : ''}`.trim()}
       aria-current={active ? 'page' : undefined} {...rest}>
      {children}
    </a>
  );
}

/** matchRoute('/lineage/:orderId', '/lineage/123') -> { orderId: '123' }, or null when it does not match. */
export function matchRoute(pattern, path) {
  const a = pattern.split('/').filter(Boolean);
  const b = path.split('/').filter(Boolean);
  if (a.length !== b.length) return null;
  const params = {};
  for (let i = 0; i < a.length; i++) {
    if (a[i].startsWith(':')) params[a[i].slice(1)] = decodeURIComponent(b[i]);
    else if (a[i] !== b[i]) return null;
  }
  return params;
}
