import { Link } from 'react-router-dom';
import type { Listing } from '../api/types';
import { carpetSqft, inrShort, areaIsSquareMetres, sqft } from '../api/corrections';
import { useSaved } from '../state/SavedContext';

export function Badge({ kind, children, title }: { kind: string; children: React.ReactNode; title?: string }) {
  return (
    <span className={`badge badge-${kind}`} title={title}>
      {children}
    </span>
  );
}

export function SaveButton({ id }: { id: string }) {
  const { ids, toggle } = useSaved();
  const on = ids.has(id);
  return (
    <button
      className={`save ${on ? 'on' : ''}`}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void toggle(id);
      }}
      aria-label={on ? 'Remove from saved' : 'Save listing'}
      title={on ? 'Remove from saved' : 'Save listing'}
    >
      {on ? '★' : '☆'}
    </button>
  );
}

export function ListingCard({
  listing: l,
  fake,
  corrupt,
  duplicate,
}: {
  listing: Listing;
  fake?: boolean;
  corrupt?: boolean;
  duplicate?: boolean;
}) {
  const area = carpetSqft(l);
  return (
    <Link to={`/listings/${encodeURIComponent(l.listing_id)}`} className="card listing-card">
      <div className="row between">
        <strong>
          {l.bedroom === 0 ? l.property_type : `${l.bedroom} BHK`} in {l.apartment_name}
        </strong>
        <SaveButton id={l.listing_id} />
      </div>
      <div className="muted cap">{l.locality}</div>
      <div className="row gap price-row">
        <span className="price">{inrShort(l.price)}</span>
        <span className="muted">{sqft(area)} carpet</span>
        {l.price > 0 && area > 0 && (
          <span className="muted">₹{Math.round(l.price / area).toLocaleString('en-IN')}/sqft</span>
        )}
      </div>
      <div className="row gap wrap badges">
        {!l.is_live && <Badge kind="warn" title="is_live is false - the docs claim these are filtered out server side">not live</Badge>}
        {fake && <Badge kind="danger" title="Part of a 190-listing enquiry-farming cluster">likely fake</Badge>}
        {corrupt && <Badge kind="danger" title="This record describes something that cannot exist">impossible data</Badge>}
        {duplicate && <Badge kind="info" title="The same property is listed again under another listing_id">duplicate</Badge>}
        {areaIsSquareMetres(l) && <Badge kind="info" title="Source reports m²; converted to sq ft">area corrected</Badge>}
        {l.is_verified && !fake && <Badge kind="ok">verified</Badge>}
      </div>
    </Link>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="empty">{children}</p>;
}
