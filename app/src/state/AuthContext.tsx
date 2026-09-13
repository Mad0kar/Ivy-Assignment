import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Api, login as apiLogin, loadSession, logout as apiLogout, refreshSession, saveSession, type Session } from '../api/client';

interface AuthValue {
  session: Session | null;
  api: Api | null;
  booting: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const Ctx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [booting, setBooting] = useState(true);
  const sessionRef = useRef<Session | null>(null);

  const commit = (s: Session | null) => {
    sessionRef.current = s;
    setSession(s);
    saveSession(s);
  };

  // Restore the session across a page refresh. The access token only lives 900s,
  // so a restored session is usually already stale - refresh it before use.
  // The ref guard stops StrictMode's double-invoke from firing two refreshes;
  // this server tolerates that, but a server that made refresh tokens single-use
  // would sign the user out on the second call.
  const booted = useRef(false);
  useEffect(() => {
    if (booted.current) return;
    booted.current = true;
    (async () => {
      const stored = loadSession();
      if (!stored) return setBooting(false);
      if (Date.now() < stored.expiresAt - 60_000) commit(stored);
      else {
        try {
          commit(await refreshSession(stored));
        } catch {
          commit(null);
        }
      }
      setBooting(false);
    })();
  }, []);

  const api = useMemo(() => {
    if (!session) return null;
    return new Api(session, commit, () => commit(null));
  }, [session?.email]);

  useEffect(() => {
    if (api && session) api.setSession(session);
  }, [api, session]);

  // Keep the session alive while the tab is open, so the app still works
  // thirty minutes after login without the user touching anything.
  useEffect(() => {
    if (!session) return;
    const id = setInterval(async () => {
      const cur = sessionRef.current;
      if (!cur) return;
      if (Date.now() > cur.expiresAt - 120_000) {
        try {
          commit(await refreshSession(cur));
        } catch {
          commit(null);
        }
      }
    }, 60_000);
    return () => clearInterval(id);
  }, [session?.email]);

  const value: AuthValue = {
    session,
    api,
    booting,
    signIn: async (email, password) => commit(await apiLogin(email, password)),
    signOut: async () => {
      const cur = sessionRef.current;
      if (cur) await apiLogout(cur);
      commit(null);
    },
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth outside AuthProvider');
  return v;
}
