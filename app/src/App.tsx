import { BrowserRouter, Link, NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './state/AuthContext';
import { DataProvider, useData } from './state/DataContext';
import { SavedProvider, useSaved } from './state/SavedContext';
import Login from './pages/Login';
import Browse from './pages/Browse';
import ListingDetail from './pages/ListingDetail';
import Saved from './pages/Saved';
import Rentals from './pages/Rentals';
import Projects from './pages/Projects';
import Insights from './pages/Insights';

function LoadingBar() {
  const { loading, progress, error, reload } = useData();
  if (error)
    return (
      <div className="loadbar error-bar">
        Could not load the catalogue: {error} <button onClick={reload}>Retry</button>
      </div>
    );
  if (!loading) return null;
  const n = progress.listings + progress.rentals + progress.projects;
  return (
    <div className="loadbar">
      Paging the API to the end — {n.toLocaleString('en-IN')} records so far
      <span className="muted">
        {' '}(the server's <code>total</code> understates it, so we follow <code>has_more</code> instead)
      </span>
    </div>
  );
}

function Shell() {
  const { session, signOut } = useAuth();
  const { me } = useData();
  const { ids } = useSaved();
  return (
    <div className="app">
      <header>
        <Link to="/browse" className="brand">
          ivy<span>·</span>mumbai
        </Link>
        <nav>
          <NavLink to="/browse">Browse</NavLink>
          <NavLink to="/rentals">Rentals</NavLink>
          <NavLink to="/projects">Projects</NavLink>
          <NavLink to="/saved">Saved{ids.size > 0 && <span className="pill">{ids.size}</span>}</NavLink>
          <NavLink to="/insights">Insights</NavLink>
        </nav>
        <div className="who">
          <span className="muted">
            {session?.email}
            {me && <> · {me.city}</>}
          </span>
          <button className="link" onClick={() => void signOut()}>Sign out</button>
        </div>
      </header>
      <LoadingBar />
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/browse" replace />} />
          <Route path="/browse" element={<Browse />} />
          <Route path="/listings/:id" element={<ListingDetail />} />
          <Route path="/rentals" element={<Rentals />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/saved" element={<Saved />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="*" element={<Navigate to="/browse" replace />} />
        </Routes>
      </main>
      <footer className="muted">
        Data from the Ivy Homes property API. Areas, prices and counts on this site are corrected —
        see <Link to="/insights">Insights</Link> for what was wrong and why.
      </footer>
    </div>
  );
}

function Gate() {
  const { session, booting } = useAuth();
  if (booting) return <div className="boot">Restoring your session…</div>;
  if (!session) return <Login />;
  return (
    <DataProvider>
      <SavedProvider>
        <Shell />
      </SavedProvider>
    </DataProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Gate />
      </AuthProvider>
    </BrowserRouter>
  );
}
