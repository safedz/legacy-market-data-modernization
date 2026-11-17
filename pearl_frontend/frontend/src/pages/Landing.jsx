import { Link } from '../router.jsx';
import Logo from '../components/Logo.jsx';
import { useAuth } from '../auth.jsx';

const FEATURES = [
  ['Legacy data, made usable', 'LOBSTER order-book messages are ingested, checksummed and converted into clean, typed records.'],
  ['Every record accounted for', 'Valid and rejected messages are reconciled against the source file, with the reason for each rejection.'],
  ['Surveillance built in', 'Spoofing and rapid-cancel patterns are flagged with severity so analysts can start from the riskiest.'],
  ['Traceable lineage', 'Follow any order from ingestion through transformation and validation to the database.'],
];

export default function Landing() {
  const { auth } = useAuth();
  return (
    <div className="site">
      <header>
        <span className="brand"><Logo size={34} /> Pearl Protocol</span>
        <Link to={auth ? '/dashboard' : '/login'} className="btn small">{auth ? 'Open dashboard' : 'Sign in'}</Link>
      </header>
      <section className="hero">
        <h1>Unlocking legacy market data and surveillance data.</h1>
        <p>A data pipeline, a surveillance data lake and an analyst dashboard for historical order-book data, built so that every number can be traced back to its source.</p>
        <div><Link to={auth ? '/dashboard' : '/login'} className="btn">{auth ? 'Open dashboard' : 'Sign in to the dashboard'}</Link></div>
      </section>
      <section className="features" aria-label="Features">
        {FEATURES.map(([title, text]) => (
          <div className="feature" key={title}><h2>{title}</h2><p>{text}</p></div>
        ))}
      </section>
      <footer>TransitionX 2026 · Team Pearl Protocol</footer>
    </div>
  );
}
