// API 客户端：所有 fetch 都从这里走，自动带上 token、统一错误处理
const TOKEN_KEY = 'app.token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = String(data.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get('Content-Type') || '';
  if (ct.includes('application/json')) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

// ----- 类型 -----
export interface User {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

export interface AuthResp {
  token: string;
  user: User;
}

export interface PlanResp {
  intent: 'chat' | 'research' | 'email';
  subqueries: string[];
}

export interface HistoryItem {
  id: number;
  topic: string;
  intent: string;
  subqueries: string[];
  file_path?: string;
  email_to?: string | null;
  created_at: string;
}

export interface HistoryDetail extends HistoryItem {
  document: string;
}

// ----- 接口 -----
export const api = {
  register: (username: string, password: string, email?: string) =>
    request<AuthResp>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, email: email || null }),
    }),
  login: (username: string, password: string) =>
    request<AuthResp>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<{ user: User }>('/api/auth/me'),
  updateProfile: (email: string) =>
    request<{ user: User }>('/api/auth/profile', {
      method: 'PATCH',
      body: JSON.stringify({ email }),
    }),
  plan: (topic: string, email?: string) => {
    const params = new URLSearchParams({ topic });
    if (email) params.set('email', email);
    return request<PlanResp>(`/api/research/plan?${params.toString()}`);
  },
  listHistory: () => request<{ items: HistoryItem[] }>('/api/history'),
  getHistory: (id: number) => request<HistoryDetail>(`/api/history/${id}`),
  deleteHistory: (id: number) =>
    request<{ ok: boolean }>(`/api/history/${id}`, { method: 'DELETE' }),
};
