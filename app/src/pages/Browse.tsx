import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useData } from '../state/DataContext';
import { ListingCard, Empty } from '../components/Bits';
import { carpetSqft, propertyKey } from '../api/corrections';

type SortKey = 'posted_at' | 'price' | 'carpet_area' | 'bedroom';

const PAGE = 24;

export default function Browse() {
  const { listings, localities, loading, fakeIds, corruptIds } = useData();
  const [params, setParams] = useSearchParams();
  const [shown, setShown] = useState(PAGE);

  const get = (k: string) => params.get(k) ?? '';
  const set = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    setParams(next, { replace: true });
    setShown(PAGE);
  };

  // Records that repeat a property already present under another listing_id.
  const duplicateIds = useMemo(() => {
    const seen = new Set<string>();
    const dupes = new Set<string>();
    for (const l of listings) {
      const k = propertyKey(l);
      if (seen.has(k)) dupes.add(l.listing_id);
      else seen.add(k);
    }
    return dupes;
  }, [listings]);

  const filtered = useMemo(() => {
    const locality = get('locality');
    const bhk = get('bhk');
    const furnishing = get('furnishing');
    const type = get('type');
    // Only bound the price when the user actually sets a bound. Defaulting min
    // to 0 would quietly hide the eleven negative-price records, and hiding a
    // broken record is how you end up not noticing it exists.
    const min = get('min') ? Number(get('min')) : -Infinity;
    const max = get('max') ? Number(get('max')) : Infinity;
    const sort = (get('sort') || 'posted_at') as SortKey;
    const dir = get('dir') === 'asc' ? 1 : -1;
    const hideProblem = get('clean') === '1';

    let rows = listings.filter((l) => {
      if (locality && l.locality !== locality) return false;
      if (bhk && String(l.bedroom) !== bhk) return false;
      if (furnishing && l.furnishing !== furnishing) return false;
      if (type && l.property_type !== type) return false;
      if (l.price < min || l.price > max) return false;
      if (hideProblem && (fakeIds.has(l.listing_id) || corruptIds.has(l.listing_id) || !l.is_live))
        return false;
      return true;
    });

    // Sorting is done here, not by the server: `order` is accepted and ignored
    // on every collection endpoint, and sort_by=carpet_area orders on a value
    // the payload does not contain.
    rows = [...rows].sort((a, b) => {
      if (sort === 'carpet_area') return (carpetSqft(a) - carpetSqft(b)) * dir;
      if (sort === 'posted_at') return a.posted_at.localeCompare(b.posted_at) * dir;
      return ((a[sort] as number) - (b[sort] as number)) * dir;
    });
    return rows;
  }, [listings, params, fakeIds, corruptIds]);

  if (loading) return <Empty>Loading the full catalogue…</Empty>;

  return (
    <div>
      <div className="card filters">
        <div className="filter-grid">
          <label>
            Locality
            <select value={get('locality')} onChange={(e) => set('locality', e.target.value)}>
              <option value="">All localities</option>
              {localities.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </label>
          <label>
            Bedrooms
            <select value={get('bhk')} onChange={(e) => set('bhk', e.target.value)}>
              <option value="">Any</option>
              {[0, 1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>{n === 0 ? 'Studio / plot' : `${n} BHK`}</option>
              ))}
            </select>
          </label>
          <label>
            Furnishing
            <select value={get('furnishing')} onChange={(e) => set('furnishing', e.target.value)}>
              <option value="">Any</option>
              <option value="unfurnished">unfurnished</option>
              <option value="semi-furnished">semi-furnished</option>
              <option value="fully-furnished">fully-furnished</option>
            </select>
          </label>
          <label>
            Type
            <select value={get('type')} onChange={(e) => set('type', e.target.value)}>
              <option value="">Any</option>
              {['apartment', 'villa', 'independent house', 'plot', 'builder floor'].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
          <label>
            Min price (₹)
            <input type="number" step={100000} value={get('min')} onChange={(e) => set('min', e.target.value)} placeholder="0" />
          </label>
          <label>
            Max price (₹)
            <input type="number" step={100000} value={get('max')} onChange={(e) => set('max', e.target.value)} placeholder="no max" />
          </label>
          <label>
            Sort by
            <select value={get('sort') || 'posted_at'} onChange={(e) => set('sort', e.target.value)}>
              <option value="posted_at">Date posted</option>
              <option value="price">Price</option>
              <option value="carpet_area">Carpet area</option>
              <option value="bedroom">Bedrooms</option>
            </select>
          </label>
          <label>
            Order
            <select value={get('dir') || 'desc'} onChange={(e) => set('dir', e.target.value)}>
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </label>
        </div>
        <label className="checkline">
          <input
            type="checkbox"
            checked={get('clean') === '1'}
            onChange={(e) => set('clean', e.target.checked ? '1' : '')}
          />
          Hide listings that are not live, impossible, or likely fake
        </label>
        <div className="muted result-count">
          {filtered.length.toLocaleString('en-IN')} matching records
          {filtered.length !== listings.length && ` of ${listings.length.toLocaleString('en-IN')}`}
        </div>
      </div>

      {filtered.length === 0 && <Empty>Nothing matches those filters.</Empty>}
      <div className="grid">
        {filtered.slice(0, shown).map((l) => (
          <ListingCard
            key={l.listing_id}
            listing={l}
            fake={fakeIds.has(l.listing_id)}
            corrupt={corruptIds.has(l.listing_id)}
            duplicate={duplicateIds.has(l.listing_id)}
          />
        ))}
      </div>
      {shown < filtered.length && (
        <button className="more" onClick={() => setShown((s) => s + PAGE)}>
          Show more ({filtered.length - shown} left)
        </button>
      )}
    </div>
  );
}
