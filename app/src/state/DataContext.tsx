import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useAuth } from './AuthContext';
import type { Listing, Me, Project, Rental } from '../api/types';
import { countDistinctProperties, fakePhoneNumbers, isCorrupt } from '../api/corrections';

interface Loaded {
  listings: Listing[];
  rentals: Rental[];
  projects: Project[];
  me: Me | null;
  localities: string[];
}

interface DataValue extends Loaded {
  loading: boolean;
  error: string | null;
  progress: { listings: number; rentals: number; projects: number };
  fakePhones: Set<string>;
  fakeIds: Set<string>;
  corruptIds: Set<string>;
  uniqueProperties: number;
  reload: () => void;
}

const Ctx = createContext<DataValue | null>(null);

const EMPTY: Loaded = { listings: [], rentals: [], projects: [], me: null, localities: [] };

export function DataProvider({ children }: { children: ReactNode }) {
  const { api } = useAuth();
  const [data, setData] = useState<Loaded>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState({ listings: 0, rentals: 0, projects: 0 });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!api) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        // /v1/me and /v1/localities are undocumented but real. They give us the
        // city, the assigned locality and the true per-locality counts, so
        // nothing here has to be hard-coded.
        const [me, locs] = await Promise.all([
          api.get<Me>('/v1/me').catch(() => null),
          api
            .get<{ results: { locality: string; listing_count: number }[] }>('/v1/localities')
            .catch(() => ({ results: [] })),
        ]);

        // Page every collection to has_more === false. `total` is understated,
        // so it is used for nothing.
        const [listings, rentals, projects] = await Promise.all([
          api.drainAll<Listing>('/v1/listings', (n) => !cancelled && setProgress((p) => ({ ...p, listings: n }))),
          api.drainAll<Rental>('/v1/rentals', (n) => !cancelled && setProgress((p) => ({ ...p, rentals: n }))),
          api.drainAll<Project>('/v1/projects', (n) => !cancelled && setProgress((p) => ({ ...p, projects: n }))),
        ]);
        if (cancelled) return;
        setData({
          listings,
          rentals,
          projects,
          me,
          localities: locs.results.map((r) => r.locality).sort(),
        });
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [api, nonce]);

  const derived = useMemo(() => {
    const fakePhones = fakePhoneNumbers(data.listings);
    const fakeIds = new Set(
      data.listings.filter((l) => fakePhones.has(l.posted_by_contact)).map((l) => l.listing_id),
    );
    const corruptIds = new Set(data.listings.filter(isCorrupt).map((l) => l.listing_id));
    return {
      fakePhones,
      fakeIds,
      corruptIds,
      uniqueProperties: countDistinctProperties(data.listings),
    };
  }, [data.listings]);

  return (
    <Ctx.Provider value={{ ...data, ...derived, loading, error, progress, reload: () => setNonce((n) => n + 1) }}>
      {children}
    </Ctx.Provider>
  );
}

export function useData() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useData outside DataProvider');
  return v;
}
