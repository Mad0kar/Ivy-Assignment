/**
 * Ivy Homes API client.
 *
 * Everything in here that looks odd is a workaround for something the published
 * API_REFERENCE.md gets wrong. Each one is commented with what the doc claims.
 */
import type { Envelope } from './types';

export const BASE = 'https://solve.ivy.homes';

// DOC: "Append it as a query parameter: GET /v1/listings?api_key=..."
// REAL: query param is rejected with 401; the key must be an X-API-Key header.
export const API_KEY = import.meta.env.VITE_IVY_API_KEY ?? 'IVY26-71CA6294F4C1';

export interface Session {
  access: string;
  refresh: string;
  expiresAt: number; // epoch ms
  email: string;
}

const STORAGE_KEY = 'ivy.session';

export function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}
export function saveSession(s: Session | null) {
  if (s) localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  else localStorage.removeItem(STORAGE_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function parse(res: Response) {
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, body?.detail ?? body);
  return body;
}

export async function login(email: string, password: string): Promise<Session> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
    body: JSON.stringify({ email, password }),
  });
  const body = await parse(res);
  // DOC: response field is "token" and expires_in is 86400 (24h).
  // REAL: the field is "access_token" and expires_in is 900 (15 min).
  return {
    access: body.access_token,
    refresh: body.refresh_token,
    expiresAt: Date.now() + (body.expires_in ?? 900) * 1000,
    email: body.user?.email ?? email,
  };
}

// DOC: "There is no refresh flow."
// REAL: /auth/refresh exists, is advertised in the login response as refresh_url,
// and is the only way to stay logged in past 15 minutes.
export async function refreshSession(s: Session): Promise<Session> {
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
    body: JSON.stringify({ refresh_token: s.refresh }),
  });
  const body = await parse(res);
  return {
    access: body.access_token,
    refresh: body.refresh_token ?? s.refresh,
    expiresAt: Date.now() + (body.expires_in ?? 900) * 1000,
    email: s.email,
  };
}

// DOC: "Invalidates the current token server side."
// REAL: returns {"ok":true,"note":"tokens are stateless; discard them client side"}
// and the token keeps working. So the only real logout is clearing local state.
export async function logout(s: Session) {
  try {
    await fetch(`${BASE}/auth/logout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
        Authorization: `Bearer ${s.access}`,
      },
      body: '{}',
    });
  } catch {
    /* logout is advisory; clearing the client session is what matters */
  }
}

/** Holds the live session and refreshes it before it expires or on a 401. */
export class Api {
  private inflightRefresh: Promise<Session> | null = null;

  private session: Session;
  private onSession: (s: Session) => void;
  private onSignedOut: () => void;

  constructor(session: Session, onSession: (s: Session) => void, onSignedOut: () => void) {
    this.session = session;
    this.onSession = onSession;
    this.onSignedOut = onSignedOut;
  }

  setSession(s: Session) {
    this.session = s;
  }

  private async ensureFresh(): Promise<string> {
    // Refresh a minute early so a request never races the expiry.
    if (Date.now() < this.session.expiresAt - 60_000) return this.session.access;
    if (!this.inflightRefresh) {
      this.inflightRefresh = refreshSession(this.session)
        .then((s) => {
          this.session = s;
          this.onSession(s);
          return s;
        })
        .finally(() => {
          this.inflightRefresh = null;
        });
    }
    const s = await this.inflightRefresh;
    return s.access;
  }

  async get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
    const url = new URL(BASE + path);
    for (const [k, v] of Object.entries(params ?? {})) {
      if (v !== undefined && v !== '') url.searchParams.set(k, String(v));
    }
    return this.request<T>(url.toString(), { method: 'GET' });
  }

  async send<T>(path: string, method: 'POST' | 'DELETE', body?: unknown): Promise<T> {
    return this.request<T>(BASE + path, {
      method,
      body: body === undefined ? undefined : JSON.stringify(body),
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    });
  }

  private async request<T>(url: string, init: RequestInit, retry = true): Promise<T> {
    const access = await this.ensureFresh();
    const headers = new Headers(init.headers);
    headers.set('X-API-Key', API_KEY);
    headers.set('Authorization', `Bearer ${access}`);
    const res = await fetch(url, { ...init, headers });

    if (res.status === 401 && retry) {
      try {
        const s = await refreshSession(this.session);
        this.session = s;
        this.onSession(s);
        return this.request<T>(url, init, false);
      } catch {
        this.onSignedOut();
      }
    }
    // Rate limit is 1200/min; a correct crawl uses ~160. Back off once just in case.
    if (res.status === 429 && retry) {
      await new Promise((r) => setTimeout(r, 2000));
      return this.request<T>(url, init, false);
    }
    return (await parse(res)) as T;
  }

  /**
   * Page a collection to the true end.
   *
   * DOC: "read total, divide by your limit, and request that many pages."
   * REAL: `total` understates the truth by ~5.9% on every endpoint, and `page`
   * is ignored entirely. Only `has_more` tells you when to stop, so that is what
   * this loops on. Following the documented recipe drops 298 listings.
   */
  async drainAll<T>(
    path: string,
    onProgress?: (loaded: number) => void,
    params?: Record<string, string | number | undefined>,
  ): Promise<T[]> {
    const LIMIT = 50; // DOC says max 200; the server silently clamps to 50.
    const out: T[] = [];
    let offset = 0;
    for (;;) {
      const env = await this.get<Envelope<T>>(path, { ...params, limit: LIMIT, offset });
      out.push(...env.results);
      onProgress?.(out.length);
      if (!env.has_more || env.results.length === 0) break;
      offset += LIMIT;
      if (offset > 100_000) break; // paranoia; never reached
    }
    return out;
  }
}
