import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export const api = axios.create({ baseURL: BASE_URL });

// Attach access token automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    if (err.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE_URL}/auth/refresh`, null, {
            params: { refresh_token: refresh },
          });
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          err.config.headers.Authorization = `Bearer ${data.access_token}`;
          return api.request(err.config);
        } catch {
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (body: { email: string; password: string; full_name: string; roles: string[] }) =>
    api.post('/auth/register', body),
  login: (body: { email: string; password: string }) =>
    api.post('/auth/login', body),
};

// ── Users ─────────────────────────────────────────────────────────────────────
export const usersApi = {
  me: () => api.get('/users/me'),
  list: () => api.get('/users/'),
  update: (id: string, body: object) => api.patch(`/users/${id}`, body),
  delete: (id: string) => api.delete(`/users/${id}`),
};

// ── Tournaments ───────────────────────────────────────────────────────────────
export const tournamentsApi = {
  create: (body: object) => api.post('/tournaments/', body),
  list: () => api.get('/tournaments/'),
  get: (id: string) => api.get(`/tournaments/${id}`),
  update: (id: string, body: object) => api.patch(`/tournaments/${id}`, body),
  delete: (id: string) => api.delete(`/tournaments/${id}`),
};

// ── Teams ─────────────────────────────────────────────────────────────────────
export const teamsApi = {
  create: (body: object) => api.post('/teams/', body),
  list: (tournament_id?: string) =>
    api.get('/teams/', { params: tournament_id ? { tournament_id } : {} }),
  get: (id: string) => api.get(`/teams/${id}`),
  update: (id: string, body: object) => api.patch(`/teams/${id}`, body),
  delete: (id: string) => api.delete(`/teams/${id}`),
};

// ── Players ───────────────────────────────────────────────────────────────────
export const playersApi = {
  create: (body: object) => api.post('/players/', body),
  list: (params?: object) => api.get('/players/', { params }),
  get: (id: string) => api.get(`/players/${id}`),
  update: (id: string, body: object) => api.patch(`/players/${id}`, body),
  delete: (id: string) => api.delete(`/players/${id}`),
};

// ── Matches ───────────────────────────────────────────────────────────────────
export const matchesApi = {
  create: (body: object) => api.post('/matches/', body),
  list: (tournament_id?: string) =>
    api.get('/matches/', { params: tournament_id ? { tournament_id } : {} }),
  get: (id: string) => api.get(`/matches/${id}`),
  update: (id: string, body: object) => api.patch(`/matches/${id}`, body),
  addCommentary: (id: string, body: object) => api.post(`/matches/${id}/commentary`, body),
  delete: (id: string) => api.delete(`/matches/${id}`),
};

// ── Auctions ──────────────────────────────────────────────────────────────────
export const auctionsApi = {
  create: (body: object) => api.post('/auctions/', body),
  list: () => api.get('/auctions/'),
  get: (id: string) => api.get(`/auctions/${id}`),
  update: (id: string, body: object) => api.patch(`/auctions/${id}`, body),
  listItems: (auctionId: string) => api.get(`/auctions/${auctionId}/items`),
  addItem: (auctionId: string, body: object) => api.post(`/auctions/${auctionId}/items`, body),
  activateItem: (auctionId: string, itemId: string) =>
    api.post(`/auctions/${auctionId}/items/${itemId}/activate`),
  sellItem: (auctionId: string, itemId: string) =>
    api.post(`/auctions/${auctionId}/items/${itemId}/sell`),
  placeBid: (auctionId: string, itemId: string, body: object) =>
    api.post(`/auctions/${auctionId}/items/${itemId}/bid`, body),
  listBids: (auctionId: string, itemId: string) =>
    api.get(`/auctions/${auctionId}/items/${itemId}/bids`),
};
