import { useMemo, useState } from 'react';
import { useData } from '../state/DataContext';
import { Badge, Empty } from '../components/Bits';
import { inrShort, projectPriceRangeInr } from '../api/corrections';

export default function Projects() {
  const { projects, listings, localities, loading } = useData();
  const [locality, setLocality] = useState('');
  const [status, setStatus] = useState('');
  const [shown, setShown] = useState(24);

  const liveByProject = useMemo(() => {
    const m = new Map<string, number>();
    for (const l of listings) {
      if (l.project_id && l.is_live) m.set(l.project_id, (m.get(l.project_id) ?? 0) + 1);
    }
    return m;
  }, [listings]);

  const rows = useMemo(
    () =>
      projects
        .filter((p) => (!locality || p.locality === locality) && (!status || p.project_status === status))
        .sort((a, b) => b.price_max - a.price_max),
    [projects, locality, status],
  );

  if (loading) return <Empty>Loading…</Empty>;
  const wrongCount = projects.filter(
    (p) => p.total_listings !== (liveByProject.get(p.project_id) ?? 0),
  ).length;

  return (
    <div>
      <h1>Projects</h1>
      <p className="muted">
        {projects.length.toLocaleString('en-IN')} builder projects. <code>price_min</code> and{' '}
        <code>price_max</code> arrive in crores, not rupees as documented, and are converted here.{' '}
        <strong>{wrongCount}</strong> projects report a <code>total_listings</code> that disagrees with
        the number of live listings actually carrying their <code>project_id</code>, which the
        documentation says can never happen.
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
            Status
            <select value={status} onChange={(e) => { setStatus(e.target.value); setShown(24); }}>
              <option value="">Any status</option>
              {['new launch', 'under construction', 'ready to move'].map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
        </div>
        <div className="muted result-count">{rows.length} projects, priciest first</div>
      </div>

      <div className="grid">
        {rows.slice(0, shown).map((p) => {
          const { min, max, minWasLakhs } = projectPriceRangeInr(p);
          const actual = liveByProject.get(p.project_id) ?? 0;
          return (
            <div key={p.project_id} id={p.project_id} className="card listing-card">
              <strong>{p.apartment_name}</strong>
              <div className="muted cap">{p.developer_name} · {p.locality}</div>
              <div className="row gap price-row">
                <span className="price">{inrShort(min)} – {inrShort(max)}</span>
              </div>
              <div className="muted small">
                {p.project_status} · {p.total_units} units · {p.total_towers} towers ·
                {' '}{p.min_area_sqft}–{p.max_area_sqft} sq ft
              </div>
              <div className="muted small">
                Launched {p.launch_date} · possession {p.possession_date} · RERA {p.rera_number}
              </div>
              <div className="row gap wrap badges">
                {p.total_listings !== actual ? (
                  <Badge kind="warn" title="Documented to always agree with the listings feed">
                    claims {p.total_listings} listings, {actual} live
                  </Badge>
                ) : (
                  <Badge kind="ok">{actual} live listings</Badge>
                )}
                {minWasLakhs && <Badge kind="info" title="price_min arrived in lakhs while price_max was in crores">price_min unit fixed</Badge>}
              </div>
              <div className="muted small">{p.amenities.join(' · ')}</div>
            </div>
          );
        })}
      </div>
      {shown < rows.length && (
        <button className="more" onClick={() => setShown((s) => s + 24)}>
          Show more ({rows.length - shown} left)
        </button>
      )}
    </div>
  );
}
