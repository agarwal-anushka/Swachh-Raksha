const API = '/api';

function getToken() {
  return localStorage.getItem('ptv_token');
}

export function getUser() {
  const raw = localStorage.getItem('ptv_user');
  return raw ? JSON.parse(raw) : null;
}

export function setAuth(token, user) {
  localStorage.setItem('ptv_token', token);
  localStorage.setItem('ptv_user', JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem('ptv_token');
  localStorage.removeItem('ptv_user');
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearAuth();
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: async (email, password) => {
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    if (!res.ok) throw new Error('Invalid credentials');
    return res.json();
  },

  me: () => request('/auth/me'),

  // Admin
  listGenerators: () => request('/admin/generators'),
  listBins: () => request('/admin/bins'),
  createGenerator: (data) => request('/admin/generators', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  createBin: (data) => request('/admin/bins', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),

  // Collector
  getBin: (qr) => request(`/collector/bin/${encodeURIComponent(qr)}`),
  submitPickup: async (formData) => {
    const token = getToken();
    const res = await fetch(`${API}/collector/pickup`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  // Reviewer
  reviewQueue: () => request('/reviews/queue'),
  submitReview: (evidence_id, verdict) =>
    request('/reviews/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ evidence_id, verdict }),
    }),

  // Authenticated photos: <img> cannot send a token, so fetch -> blob URL
  photoBlob: async (url) => {
    const res = await fetch(`${API}${url}`, { headers: { Authorization: `Bearer ${getToken()}` } });
    if (!res.ok) throw new Error('Photo unavailable');
    return URL.createObjectURL(await res.blob());
  },

  // Generator
  generatorMe: () => request('/generator/me'),
  contest: (id, text) =>
    request(`/generator/notices/${id}/contest`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }),
    }),

  // Officer
  verifyChain: () => request('/officer/chain/verify'),
  missed: () => request('/officer/missed'),
  demoTamper: (id) => request(`/officer/demo/tamper/${id}`, { method: 'POST' }),
  demoRestore: () => request('/officer/demo/restore', { method: 'POST' }),
  dashboard: () => request('/officer/dashboard'),
  listNotices: (status) => request(`/officer/notices${status ? `?status=${status}` : ''}`),
  noticeAction: (id, action, remark) =>
    request(`/officer/notices/${id}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, remark }),
    }),
};
