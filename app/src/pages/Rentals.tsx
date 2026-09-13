import { useMemo, useState } from 'react';
import { useData } from '../state/DataContext';
import { Empty } from '../components/Bits';
import { inr, inrShort, rentalTitleLocalityDisagrees, sqft } from '../api/corrections';

export default function Rentals() {
  const { rentals, localities, loading, me } = useData();
  const [locality, setLocality] = useState('');
  const [bhk, setBhk] = useState('');
  const [shown, setShown] = useState(24);

  const rows = useMemo(
    () =>
      rentals
        .filter((r) => (!locality || r.locality === locality) && (!bhk || String(r.bedroom) === bhk))
        .sort((a, b) => b.price - a.price),
    [rentals, locality, bhk],
  );

  const total = rows.reduce((s, r) => s + r.price, 0);
  if (loading) return <Empty>Loading…</Empty>;

  return (
    <div>
      <h1>Rentals</h1>
      <p className="muted">
        {rentals.length.toLocaleString('en-IN')} rental records. Rent and deposit really are in
        rupees per month — unlike listing areas and project prices, these needed no correction.
        The <code>title</code> does not: it names the wrong locality in 91% of records, so the
        heading below is built from the structured fields instead.
      </p>

      <div className="card filters">
        <div className="filter-grid">
          <label>
            Locality
            <select value={locality} onChange={(e) => { setLocality(e.target.value); setShown(24); }}>
              <option value="">All localities</option>
              {localities.map((l) => <option key={l}>{l}</option>)}
            </select>
          </label>
          <label>
            Bedrooms
            <select value={bhk} onChange={(e) => { setBhk(e.target.value); setShown(24); }}>
              <option value="">Any</option>
              {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n} BHK</option>)}
            </select>
          </label>
        </div>
        <div className="muted result-count">
          {rows.length.toLocaleString('en-IN')} records · total monthly rent {inr(total)}
          {locality === me?.assigned_locality && ' · this is the answer to question 5'}
        </div>
      </div>

      <div className="grid">
        {rows.slice(0, shown).map((r) => (
          <div key={r.listing_id} className="card listing-card">
            <strong>{r.bedroom} BHK {r.property_type} in {r.apartment_name}</strong>
            <div className="muted cap">{r.locality}</div>
            <div className="row gap price-row">
              <span className="price">{inrShort(r.price)}<span className="muted">/mo</span></span>
              <span className="muted">{sqft(r.carpet_area)} carpet</span>
            </div>
            <div className="muted small">
              Deposit {inrShort(r.deposit)} · maintenance {inr(r.maintenance)} · {r.furnishing}
            </div>
            {rentalTitleLocalityDisagrees(r) && (
              <div className="muted small strike">
                API title says “{r.title}” — wrong locality
              </div>
            )}
          </div>
        ))}
      </div>
      {shown < rows.length && (
        <button className="more" onClick={() => setShown((s) => s + 24)}>
          Show more ({rows.length - shown} left)
        </button>
      )}
    </div>
  );
}
