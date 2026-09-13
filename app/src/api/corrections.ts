/**
 * The correction layer.
 *
 * The API is honest; the documentation is not, and some of the records were
 * written by sellers. Everything the app displays goes through here first, so
 * that no screen ever shows a number in the wrong unit or counts a record that
 * cannot exist. Each rule below was derived from the full dataset, not from a
 * single response - see README.md for how.
 */
import type { Listing, Project, Rental } from './types';

export const SQFT_PER_SQM = 10.7639;

/** The reference moment the assignment anchors to, as an IST wall-clock string. */
export const REFERENCE_IST = '2026-09-10T00:00:00';

/**
 * magichomes switched its area unit from square feet to square metres on
 * 2026-06-01. The cutover is exact: no magichomes listing dated before that has
 * an area under 300, and none dated on or after it has an area over 300.
 * DOC: "Area: Square feet, integer, everywhere in the API."
 */
export function areaIsSquareMetres(l: Pick<Listing, 'website' | 'posted_at'>): boolean {
  return l.website === 'magichomes' && l.posted_at >= '2026-06-01';
}

export function carpetSqft(l: Listing): number {
  return areaIsSquareMetres(l) ? l.carpet_area * SQFT_PER_SQM : l.carpet_area;
}
export function builtUpSqft(l: Listing): number {
  return areaIsSquareMetres(l) ? l.super_built_up_area * SQFT_PER_SQM : l.super_built_up_area;
}

/**
 * DOC: "price_min and price_max are in rupees."
 * REAL: they are floats in crores. Six projects additionally report price_min in
 * lakhs, which is the only reason their price_min exceeds their price_max.
 */
export function projectPriceRangeInr(p: Project): { min: number; max: number; minWasLakhs: boolean } {
  const max = Math.round(p.price_max * 1e7);
  const minWasLakhs = p.price_min > p.price_max;
  const min = minWasLakhs ? Math.round(p.price_min * 1e5) : Math.round(p.price_min * 1e7);
  return { min, max, minWasLakhs };
}

/** posted_at is naive Asia/Kolkata local time, despite the doc claiming UTC + "Z". */
export function postedAtIst(iso: string): Date {
  return new Date(iso.length === 19 ? iso + '+05:30' : iso);
}

// ---------------------------------------------------------------------------
// Records that cannot exist. Seven disjoint classes, exactly 11 records each.
// ---------------------------------------------------------------------------
export type CorruptReason =
  | 'negative price'
  | 'price far below any real sale'
  | 'carpet area exceeds super built-up area'
  | 'floor above the top floor'
  | 'posted after the reference date'
  | 'latitude and longitude transposed'
  | 'no bedrooms and no bathrooms';

export function corruptReasons(l: Listing): CorruptReason[] {
  const out: CorruptReason[] = [];
  if (l.price <= 0) out.push('negative price');
  else if (l.price < 100_000) out.push('price far below any real sale');
  if (l.carpet_area > l.super_built_up_area) out.push('carpet area exceeds super built-up area');
  if (l.floor > l.total_floors) out.push('floor above the top floor');
  if (l.posted_at >= REFERENCE_IST) out.push('posted after the reference date');
  if (l.latitude < 18.8 || l.latitude > 19.5) out.push('latitude and longitude transposed');
  // Plots legitimately have 0 bedrooms, 0 bathrooms and 0 floors.
  if (l.bedroom === 0 && l.bathroom === 0 && l.property_type !== 'plot')
    out.push('no bedrooms and no bathrooms');
  return out;
}
export const isCorrupt = (l: Listing) => corruptReasons(l).length > 0;

/**
 * Listings that exist to harvest enquiries.
 *
 * Bait pricing alone does not separate them - 1,549 honest listings undercut the
 * most expensive fake. The discriminator is the conjunction: a phone number with
 * ten or more listings on which EVERY listing is is_verified. Exactly five
 * numbers in the city qualify, with 38 listings each; the next busiest agent has
 * 33 listings and is verified on 20 of them. Each of the five posts under
 * several different seller names and covers all ten localities at roughly half
 * the market rate.
 */
export function fakePhoneNumbers(listings: Listing[]): Set<string> {
  const byPhone = new Map<string, Listing[]>();
  for (const l of listings) {
    const arr = byPhone.get(l.posted_by_contact);
    if (arr) arr.push(l);
    else byPhone.set(l.posted_by_contact, [l]);
  }
  const fake = new Set<string>();
  for (const [phone, rows] of byPhone) {
    if (rows.length >= 10 && rows.every((r) => r.is_verified)) fake.add(phone);
  }
  return fake;
}

/**
 * The same physical property, re-posted under a second listing_id.
 *
 * DOC: "each listing corresponds to exactly one physical property."
 * Duplicate pairs agree on all eleven structural attributes below and sit within
 * ~0.0005 degrees of each other. Exact coordinate matches are NOT duplicates -
 * those are different flats in one building, and their floors always differ.
 */
export function propertyKey(l: Listing): string {
  const name = l.apartment_name.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  return [
    name, l.locality, l.bedroom, l.floor, l.bathroom, l.balcony,
    l.total_floors, l.facing_direction, l.furnishing, l.property_type, l.covered_parking,
  ].join('|');
}

export function countDistinctProperties(listings: Listing[]): number {
  return new Set(listings.map(propertyKey)).size;
}

/** Rental titles name the wrong locality in 91% of records; the field is right. */
export function rentalTitleLocalityDisagrees(r: Rental): boolean {
  const m = /^\d+ BHK for rent in (.+)$/.exec(r.title ?? '');
  return m ? m[1].trim().toLowerCase() !== r.locality : false;
}

export const inr = (n: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

export function inrShort(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`;
  if (abs >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`;
  return inr(n);
}

export const sqft = (n: number) => `${Math.round(n).toLocaleString('en-IN')} sq ft`;
