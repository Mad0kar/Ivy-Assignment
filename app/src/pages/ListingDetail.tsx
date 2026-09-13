import { Link, useParams } from 'react-router-dom';
import { useMemo } from 'react';
import { useData } from '../state/DataContext';
import { Badge, Empty, ListingCard, SaveButton } from '../components/Bits';
import {
  areaIsSquareMetres, builtUpSqft, carpetSqft, corruptReasons, inr, inrShort,
  postedAtIst, projectPriceRangeInr, propertyKey, sqft,
} from '../api/corrections';

export default function ListingDetail() {
  const { id = '' } = useParams();
  const { listings, projects, loading, fakeIds, corruptIds } = useData();

  const listing = listings.find((l) => l.listing_id === id);

  const twins = useMemo(
    () => (listing ? listings.filter((l) => l.listing_id !== id && propertyKey(l) === propertyKey(listing)) : []),
    [listings, listing, id],
  );

  // DOC: GET /v1/listings/{id}/similar returns up to ten comparables.
  // REAL: 404. Computed here on the documented rule instead.
  const similar = useMemo(() => {
    if (!listing) return [];
    return listings
      .filter(
        (l) =>
          l.listing_id !== listing.listing_id &&
          l.locality === listing.locality &&
          l.bedroom === listing.bedroom &&
          listing.price > 0 &&
          Math.abs(l.price - listing.price) / listing.price <= 0.15,
      )
      .slice(0, 10);
  }, [listings, listing]);

  if (loading) return <Empty>Loading…</Empty>;
  if (!listing) return <Empty>No listing with id {id} in this city.</Empty>;

  const project = projects.find((p) => p.project_id === listing.project_id);
  const problems = corruptReasons(listing);
  const fake = fakeIds.has(listing.listing_id);
  const area = carpetSqft(listing);

  const facts: [string, string][] = [
    ['Price', listing.price > 0 ? inr(listing.price) : `${inr(listing.price)} — impossible`],
    ['Carpet area', sqft(area)],
    ['Super built-up', sqft(builtUpSqft(listing))],
    ['Price per sq ft', listing.price > 0 && area > 0 ? `₹${Math.round(listing.price / area).toLocaleString('en-IN')}` : '—'],
    ['Bedrooms', String(listing.bedroom)],
    ['Bathrooms', String(listing.bathroom)],
    ['Balconies', String(listing.balcony)],
    ['Floor', `${listing.floor} of ${listing.total_floors}`],
    ['Furnishing', listing.furnishing],
    ['Facing', listing.facing_direction],
    ['Covered parking', String(listing.covered_parking)],
    ['Property type', listing.property_type],
    ['Locality', listing.locality],
    ['Source', listing.website],
    ['Posted', postedAtIst(listing.posted_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) + ' IST'],
    ['Posted by', `${listing.posted_by_name} (${listing.posted_by})`],
    ['Contact', listing.posted_by_contact],
  ];

  return (
    <article className="detail">
      <div className="row between wrap">
        <div>
          <h1>
            {listing.bedroom === 0 ? listing.property_type : `${listing.bedroom} BHK`} in {listing.apartment_name}
          </h1>
          <p className="muted cap">{listing.locality} · {listing.listing_id}</p>
        </div>
        <SaveButton id={listing.listing_id} />
      </div>

      <div className="row gap wrap badges">
        {!listing.is_live && <Badge kind="warn">not live</Badge>}
        {fake && <Badge kind="danger">likely fake</Badge>}
        {problems.length > 0 && <Badge kind="danger">impossible data</Badge>}
        {twins.length > 0 && <Badge kind="info">{twins.length} duplicate record{twins.length > 1 ? 's' : ''}</Badge>}
        {areaIsSquareMetres(listing) && <Badge kind="info">area converted from m²</Badge>}
        {listing.is_verified && <Badge kind={fake ? 'warn' : 'ok'}>verified</Badge>}
      </div>

      {(problems.length > 0 || fake || !listing.is_live) && (
        <div className="card notice">
          <strong>Why this listing is flagged</strong>
          <ul>
            {problems.map((p) => (
              <li key={p}>{p}</li>
            ))}
            {fake && (
              <li>
                Posted from {listing.posted_by_contact}, one of five numbers carrying 38 listings each,
                every one marked verified, priced around half the market rate, under several different
                seller names. Treated as an enquiry farm.
              </li>
            )}
            {!listing.is_live && <li>is_live is false — the documentation claims such records are filtered out server side.</li>}
          </ul>
        </div>
      )}

      <div className="card">
        <p className="desc">{listing.description}</p>
        <dl className="facts">
          {facts.map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
        <a className="ext" href={listing.listing_url} target="_blank" rel="noreferrer">
          View on {listing.website} ↗
        </a>
      </div>

      {project && (
        <div className="card">
          <h2>Part of {project.apartment_name}</h2>
          <p className="muted">
            {project.developer_name} · {project.project_status} · possession {project.possession_date}
          </p>
          <p>
            Price band {inrShort(projectPriceRangeInr(project).min)} – {inrShort(projectPriceRangeInr(project).max)}
          </p>
          <Link to={`/projects#${project.project_id}`}>See project →</Link>
        </div>
      )}

      {twins.length > 0 && (
        <section>
          <h2>The same property, listed again</h2>
          <p className="muted">
            These records match on every structural attribute and sit within about 50 metres.
            The API says every listing is one distinct property; these are not.
          </p>
          <div className="grid">
            {twins.map((t) => (
              <ListingCard key={t.listing_id} listing={t} fake={fakeIds.has(t.listing_id)} corrupt={corruptIds.has(t.listing_id)} />
            ))}
          </div>
        </section>
      )}

      {similar.length > 0 && (
        <section>
          <h2>You may also like</h2>
          <p className="muted">
            Same locality, same bedroom count, price within 15% — the rule the documented
            /v1/listings/{'{id}'}/similar endpoint promised before it turned out to 404.
          </p>
          <div className="grid">
            {similar.map((s) => (
              <ListingCard key={s.listing_id} listing={s} fake={fakeIds.has(s.listing_id)} corrupt={corruptIds.has(s.listing_id)} />
            ))}
          </div>
        </section>
      )}
    </article>
  );
}
