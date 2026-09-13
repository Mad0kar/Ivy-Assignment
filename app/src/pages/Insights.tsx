import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useData } from '../state/DataContext';
import { Empty } from '../components/Bits';
import {
  REFERENCE_IST, areaIsSquareMetres, carpetSqft, corruptReasons, inr, inrShort,
  postedAtIst, projectPriceRangeInr, rentalTitleLocalityDisagrees,
} from '../api/corrections';
import type { Listing } from '../api/types';

const median = (xs: number[]) => {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {note && <span className="stat-note">{note}</span>}
    </div>
  );
}

export default function Insights() {
  const { listings, rentals, projects, me, loading, fakeIds, corruptIds, uniqueProperties } = useData();

  const a = useMemo(() => {
    if (!listings.length) return null;
    const live = listings.filter((l) => l.is_live);
    const pps = (l: Listing) => l.price / carpetSqft(l);

    // Q6: live 2 BHKs, excluding the impossible and the fraudulent.
    const twoBhk = live.filter(
      (l) => l.bedroom === 2 && !corruptIds.has(l.listing_id) && !fakeIds.has(l.listing_id),
    );
    const avg2bhk = twoBhk.reduce((s, l) => s + pps(l), 0) / (twoBhk.length || 1);

    // Q8: the seven days before the reference moment, in IST.
    const refMs = postedAtIst(REFERENCE_IST).getTime();
    const weekMs = 7 * 864e5;
    const last7 = listings.filter((l) => {
      const t = postedAtIst(l.posted_at).getTime();
      return t >= refMs - weekMs && t < refMs;
    }).length;

    const assigned = me?.assigned_locality ?? 'powai';
    const rentTotal = rentals.filter((r) => r.locality === assigned).reduce((s, r) => s + r.price, 0);
    const rentCount = rentals.filter((r) => r.locality === assigned).length;

    const costliest = projects.reduce((best, p) => (p.price_max > best.price_max ? p : best), projects[0]);

    const liveByProject = new Map<string, number>();
    for (const l of listings) {
      if (l.project_id && l.is_live) liveByProject.set(l.project_id, (liveByProject.get(l.project_id) ?? 0) + 1);
    }
    const wrongCounts = projects.filter(
      (p) => p.total_listings !== (liveByProject.get(p.project_id) ?? 0),
    ).length;

    const healthy = live.filter((l) => !corruptIds.has(l.listing_id) && !fakeIds.has(l.listing_id));
    const byLocality = [...new Set(listings.map((l) => l.locality))]
      .map((loc) => {
        const rows = healthy.filter((l) => l.locality === loc);
        return {
          locality: loc,
          count: listings.filter((l) => l.locality === loc).length,
          medianPrice: median(rows.map((l) => l.price)),
          medianPps: median(rows.map(pps)),
        };
      })
      .sort((x, y) => y.medianPps - x.medianPps);

    const byBhk = [0, 1, 2, 3, 4, 5].map((b) => ({
      bedroom: b,
      count: listings.filter((l) => l.bedroom === b).length,
      medianPrice: median(healthy.filter((l) => l.bedroom === b).map((l) => l.price)),
    }));

    const corruptByReason = new Map<string, number>();
    for (const l of listings) for (const r of corruptReasons(l)) corruptByReason.set(r, (corruptByReason.get(r) ?? 0) + 1);

    const metricIds = listings.filter(areaIsSquareMetres);
    const naive2bhk = live.filter((l) => l.bedroom === 2).reduce((s, l) => s + l.price / l.carpet_area, 0)
      / (live.filter((l) => l.bedroom === 2).length || 1);

    return {
      live, healthy, twoBhk, avg2bhk, last7, assigned, rentTotal, rentCount,
      costliest, wrongCounts, byLocality, byBhk, corruptByReason, metricIds, naive2bhk,
      medianPrice: median(healthy.map((l) => l.price)),
      medianPps: median(healthy.map(pps)),
      dupRecords: listings.length - uniqueProperties,
      titleWrong: rentals.filter(rentalTitleLocalityDisagrees).length,
      fakePhones: new Set(listings.filter((l) => fakeIds.has(l.listing_id)).map((l) => l.posted_by_contact)),
    };
  }, [listings, rentals, projects, me, fakeIds, corruptIds, uniqueProperties]);

  if (loading || !a) return <Empty>Computing over the full dataset…</Empty>;

  const cp = projectPriceRangeInr(a.costliest);

  return (
    <div className="insights">
      <h1>Insights</h1>
      <p className="muted lede">
        The documentation promises these aggregates from <code>/v1/analytics/summary</code>. That
        endpoint returns 404, so everything below is computed in your browser from all{' '}
        {listings.length.toLocaleString('en-IN')} listings, {rentals.length.toLocaleString('en-IN')} rentals
        and {projects.length} projects — after the corrections this dataset needs. Nothing here is
        hard-coded; refresh and it recomputes.
      </p>

      <h2>The city at a glance</h2>
      <div className="stats">
        <Stat label="Listing records" value={listings.length.toLocaleString('en-IN')} note={`server reports 4,802 — it is wrong`} />
        <Stat label="Distinct properties" value={uniqueProperties.toLocaleString('en-IN')} note={`${a.dupRecords} records are re-posts`} />
        <Stat label="Live listings" value={a.live.length.toLocaleString('en-IN')} note={`${listings.length - a.live.length} are not live`} />
        <Stat label="Median price" value={inrShort(a.medianPrice)} note="live, excluding fake and impossible" />
        <Stat label="Median ₹/sq ft" value={`₹${Math.round(a.medianPps).toLocaleString('en-IN')}`} note="on unit-corrected areas" />
        <Stat label="Posted in the last 7 days" value={String(a.last7)} note={`before ${REFERENCE_IST.slice(0, 10)} IST`} />
      </div>

      <h2>What the data is hiding</h2>
      <div className="stats">
        <Stat label="Enquiry-farm listings" value={String(fakeIds.size)} note={`${a.fakePhones.size} phone numbers, all “verified”`} />
        <Stat label="Impossible records" value={String(corruptIds.size)} note="7 classes, 11 records each" />
        <Stat label="Areas in m², not sq ft" value={String(a.metricIds.length)} note="magichomes, from 2026-06-01" />
        <Stat label="Duplicate records" value={String(a.dupRecords)} note="same property, second listing_id" />
        <Stat label="Projects with a wrong count" value={String(a.wrongCounts)} note={`of ${projects.length}`} />
        <Stat label="Rentals with a wrong title" value={String(a.titleWrong)} note={`of ${rentals.length}`} />
      </div>

      <div className="card highlight">
        <h3>The unit bug is worth a factor of two</h3>
        <p>
          Average price per square foot for live 2 BHKs, excluding the impossible and the
          fraudulent, taking <code>carpet_area</code> at face value:{' '}
          <strong className="wrong">₹{a.naive2bhk.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</strong>.
          After converting the {a.metricIds.length} magichomes records posted on or after 2026-06-01 from
          square metres:{' '}
          <strong className="right">₹{a.avg2bhk.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</strong>{' '}
          across {a.twoBhk.length.toLocaleString('en-IN')} records.
        </p>
      </div>

      <h2>By locality</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Locality</th><th>Records</th><th>Median price</th><th>Median ₹/sq ft</th></tr>
          </thead>
          <tbody>
            {a.byLocality.map((r) => (
              <tr key={r.locality}>
                <td className="cap">
                  <Link to={`/browse?locality=${encodeURIComponent(r.locality)}`}>{r.locality}</Link>
                  {r.locality === a.assigned && <span className="tag">assigned</span>}
                </td>
                <td>{r.count}</td>
                <td>{inrShort(r.medianPrice)}</td>
                <td>₹{Math.round(r.medianPps).toLocaleString('en-IN')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>By bedroom count</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Bedrooms</th><th>Records</th><th>Median price</th></tr></thead>
          <tbody>
            {a.byBhk.map((r) => (
              <tr key={r.bedroom}>
                <td>{r.bedroom === 0 ? 'Studio / plot' : `${r.bedroom} BHK`}</td>
                <td>{r.count}</td>
                <td>{r.medianPrice ? inrShort(r.medianPrice) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Records that cannot exist</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Why it is impossible</th><th>Records</th></tr></thead>
          <tbody>
            {[...a.corruptByReason.entries()].map(([reason, n]) => (
              <tr key={reason}><td>{reason}</td><td>{n}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Answers to the ten questions</h2>
      <p className="muted">Computed live, in this browser, from the numbers above.</p>
      <div className="table-wrap">
        <table>
          <thead><tr><th>#</th><th>Question</th><th>Answer</th></tr></thead>
          <tbody>
            <tr><td>1</td><td>Retrievable listing records</td><td>{listings.length.toLocaleString('en-IN')}</td></tr>
            <tr><td>2</td><td>Distinct properties</td><td>{uniqueProperties.toLocaleString('en-IN')}</td></tr>
            <tr><td>3</td><td>Records with is_live true</td><td>{a.live.length.toLocaleString('en-IN')}</td></tr>
            <tr><td>4</td><td>Impossible listing records</td><td>{corruptIds.size}</td></tr>
            <tr><td>5</td><td>Monthly rent across {a.assigned}</td><td>{inr(a.rentTotal)} <span className="muted">({a.rentCount} records)</span></td></tr>
            <tr><td>6</td><td>Mean ₹/sq ft, live 2 BHK</td><td>₹{a.avg2bhk.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td></tr>
            <tr><td>7</td><td>Costliest project</td><td>{a.costliest.project_id} — {inr(cp.max)}</td></tr>
            <tr><td>8</td><td>Posted in the 7 days before the reference</td><td>{a.last7}</td></tr>
            <tr><td>9</td><td>Enquiry-farm listings</td><td>{fakeIds.size}</td></tr>
            <tr><td>10</td><td>Projects with a wrong listing count</td><td>{a.wrongCounts}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
