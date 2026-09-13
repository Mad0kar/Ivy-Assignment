import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { useAuth } from './AuthContext';
import type { Listing } from '../api/types';

/**
 * DOC: GET/POST /v1/favourites with body {"id": ...}, DELETE /v1/favourites/{id}
 * REAL: all three 404. The endpoint is /v1/saved and the POST body key is
 * listing_id. Saved lists are per user and survive logout and re-login.
 */
interface SavedValue {
  ids: Set<string>;
  items: Listing[];
  loading: boolean;
  toggle: (id: string) => Promise<void>;
  error: string | null;
}

const Ctx = createContext<SavedValue | null>(null);

export function SavedProvider({ children }: { children: ReactNode }) {
  const { api, session } = useAuth();
  const [items, setItems] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!api) return;
    setLoading(true);
    try {
      const body = await api.get<{ count: number; results: Listing[] }>('/v1/saved');
      setItems(body.results ?? []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void refresh();
  }, [refresh, session?.email]);

  const toggle = async (id: string) => {
    if (!api) return;
    const saved = items.some((i) => i.listing_id === id);
    try {
      if (saved) await api.send('/v1/saved/' + encodeURIComponent(id), 'DELETE');
      else await api.send('/v1/saved', 'POST', { listing_id: id });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <Ctx.Provider
      value={{ ids: new Set(items.map((i) => i.listing_id)), items, loading, toggle, error }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useSaved() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useSaved outside SavedProvider');
  return v;
}
