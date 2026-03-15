/**
 * API client — typed fetch wrapper for all backend endpoints.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || 'Request failed');
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// ── Config ────────────────────────────────────────────────────────────────────

export const config = {
  get: () => request<{ google_oauth: boolean; stripe_enabled: boolean }>('/api/config'),
};

// ── Auth ─────────────────────────────────────────────────────────────────────

export const auth = {
  register: (email: string, password: string, name?: string) =>
    request('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password, name }) }),
  login: (email: string, password: string) =>
    request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  me: () => request<any>('/api/auth/me'),
  refresh: () => request('/api/auth/refresh', { method: 'POST' }),
  googleUrl: () => request<{ url: string }>('/api/auth/google'),
  forgotPassword: (email: string) =>
    request('/api/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (token: string, new_password: string) =>
    request('/api/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, new_password }) }),
  verifyResetToken: (token: string) =>
    request<{ valid: boolean }>('/api/auth/verify-reset-token', { method: 'POST', body: JSON.stringify({ token }) }),
};

// ── Projects ────────────────────────────────────────────────────────────────

export const projects = {
  list: () => request<any[]>('/api/projects'),
  create: (name: string) => request<any>('/api/projects', { method: 'POST', body: JSON.stringify({ name }) }),
  get: (id: string) => request<any>(`/api/projects/${id}`),
  delete: (id: string) => request(`/api/projects/${id}`, { method: 'DELETE' }),
  keys: (id: string) => request<any[]>(`/api/projects/${id}/keys`),
  createKey: (id: string) => request<any>(`/api/projects/${id}/keys`, { method: 'POST' }),
  usage: (id: string) => request<any>(`/api/projects/${id}/usage`),
  updateSettings: (id: string, data: any) =>
    request(`/api/projects/${id}/settings`, { method: 'PATCH', body: JSON.stringify(data) }),
};

// ── Features ────────────────────────────────────────────────────────────────

export const features = {
  list: (projectId: string) => request<any[]>(`/api/projects/${projectId}/features`),
  create: (projectId: string, name: string) =>
    request<any>(`/api/projects/${projectId}/features`, { method: 'POST', body: JSON.stringify({ name }) }),
  updateSettings: (projectId: string, featureId: string, data: any) =>
    request(`/api/projects/${projectId}/features/${featureId}/settings`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (projectId: string, featureId: string) =>
    request(`/api/projects/${projectId}/features/${featureId}`, { method: 'DELETE' }),
};

// ── Stats ───────────────────────────────────────────────────────────────────

export const stats = {
  overview: (projectId: string, days = 30) => request<any>(`/api/projects/${projectId}/stats/overview?days=${days}`),
  features: (projectId: string, days = 30) => request<any>(`/api/projects/${projectId}/stats/features?days=${days}`),
};

// ── Suggestions ─────────────────────────────────────────────────────────────

export const suggestions = {
  list: (projectId: string) => request<any[]>(`/api/projects/${projectId}/suggestions`),
  update: (projectId: string, suggestionId: string, action: string) =>
    request(`/api/projects/${projectId}/suggestions/${suggestionId}?action=${action}`, { method: 'PATCH' }),
};

// ── Billing ─────────────────────────────────────────────────────────────────

export const billing = {
  plans: () => request<any[]>('/api/billing/plans'),
  subscription: () => request<any>('/api/billing/subscription'),
  changePlan: (planCode: string) =>
    request('/api/billing/change-plan', { method: 'POST', body: JSON.stringify({ plan_code: planCode }) }),
  portal: () => request<{ url: string }>('/api/billing/portal', { method: 'POST' }),
};

// ── Admin ──────────────────────────────────────────────────────────────────

export const admin = {
  stats: () => request<any>('/api/admin/stats'),
  users: (page = 1, perPage = 20) => request<any>(`/api/admin/users?page=${page}&per_page=${perPage}`),
  changeUserPlan: (userId: string, planCode: string) =>
    request('/api/admin/users/' + userId + '/plan?plan_code=' + planCode, { method: 'PATCH' }),
  toggleAdmin: (userId: string) =>
    request('/api/admin/users/' + userId + '/admin', { method: 'PATCH' }),
};
