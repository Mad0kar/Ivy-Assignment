import { useSaved } from '../state/SavedContext';
import { useData } from '../state/DataContext';
import { useAuth } from '../state/AuthContext';
import { Empty, ListingCard } from '../components/Bits';

export default function Saved() {
  const { items, loading, error } = useSaved();
  const { fakeIds, corruptIds } = useData();
  const { session } = useAuth();

  return (
    <div>
      <h1>Saved listings</h1>
      <p className="muted">
        Stored server side against {session?.email} via <code>/v1/saved</code> — the documented
        <code> /v1/favourites</code> returns 404. They survive a reload and a re-login, and
        another demo account sees its own list, not this one.
      </p>
      {error && <p className="error">{error}</p>}
      {loading ? (
        <Empty>Loading…</Empty>
      ) : items.length === 0 ? (
        <Empty>Nothing saved yet. Tap the star on any listing.</Empty>
      ) : (
        <div className="grid">
          {items.map((l) => (
            <ListingCard
              key={l.listing_id}
              listing={l}
              fake={fakeIds.has(l.listing_id)}
              corrupt={corruptIds.has(l.listing_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
