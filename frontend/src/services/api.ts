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
  updateMe: (body: object) => api.patch('/users/me', body),
  list: (params?: { page?: number; limit?: number; role?: string }) => api.get('/users/', { params }),
  update: (id: string, body: object) => api.patch(`/users/${id}`, body),
  updateRoles: (id: string, roles: string[]) => api.patch(`/admin/${id}/roles`, roles),
  delete: (id: string) => api.delete(`/users/${id}`),
};

// ── Tournaments ───────────────────────────────────────────────────────────────
export const tournamentsApi = {
  create: (body: object) => api.post('/tournaments/', body),
  list: (params?: { page?: number; limit?: number }) => api.get('/tournaments/', { params }),
  get: (id: string) => api.get(`/tournaments/${id}`),
  update: (id: string, body: object) => api.patch(`/tournaments/${id}`, body),
  delete: (id: string) => api.delete(`/tournaments/${id}`),
};

// ── Teams ─────────────────────────────────────────────────────────────────────
export const teamsApi = {
  create: (body: object) => api.post('/teams/', body),
  list: (params?: { tournament_id?: string; page?: number; limit?: number }) =>
    api.get('/teams/', { params }),
  get: (id: string) => api.get(`/teams/${id}`),
  getHistory: (id: string) => api.get(`/teams/${id}/history`),
  addPlayer: (teamId: string, playerId: string) => api.post(`/teams/${teamId}/players/${playerId}`),
  removePlayer: (teamId: string, playerId: string) => api.delete(`/teams/${teamId}/players/${playerId}`),
  update: (id: string, body: object) => api.patch(`/teams/${id}`, body),
  delete: (id: string) => api.delete(`/teams/${id}`),
};

// ── Players ───────────────────────────────────────────────────────────────────
export const playersApi = {
  create: (body: object) => api.post('/players/', body),
  list: (params?: object) => api.get('/players/', { params }),
  getRankings: (params?: { by?: string; limit?: number }) => api.get('/players/rankings', { params }),
  get: (id: string) => api.get(`/players/${id}`),
  getStats: (id: string) => api.get(`/players/${id}/stats`),
  update: (id: string, body: object) => api.patch(`/players/${id}`, body),
  delete: (id: string) => api.delete(`/players/${id}`),
};

// ── Matches ───────────────────────────────────────────────────────────────────
export const matchesApi = {
  create: (body: object) => api.post('/matches/', body),
  list: (params?: { tournament_id?: string; page?: number; limit?: number }) =>
    api.get('/matches/', { params }),
  get: (id: string) => api.get(`/matches/${id}`),
  update: (id: string, body: object) => api.patch(`/matches/${id}`, body),
  addCommentary: (id: string, body: object) => api.post(`/matches/${id}/commentary`, body),
  generateAiCommentary: (id: string, body: object) => api.post(`/matches/${id}/generate-ai-commentary`, body),
  delete: (id: string) => api.delete(`/matches/${id}`),
};

// ── Auctions ──────────────────────────────────────────────────────────────────
export const auctionsApi = {
  create: (body: object) => api.post('/auctions/', body),
  list: (params?: { page?: number; limit?: number }) => api.get('/auctions/', { params }),
  get: (id: string) => api.get(`/auctions/${id}`),
  update: (id: string, body: object) => api.patch(`/auctions/${id}`, body),
  startAuction: (id: string) => api.post(`/auctions/${id}/start`),
  finalizeAuction: (id: string) => api.post(`/auctions/${id}/finalize`),
  resetAuction: (id: string) => api.post(`/auctions/${id}/reset`),
  listItems: (auctionId: string) => api.get(`/auctions/${auctionId}/items`),
  addItem: (auctionId: string, body: object) => api.post(`/auctions/${auctionId}/items`, body),
  activateItem: (auctionId: string, itemId: string) =>
    api.post(`/auctions/${auctionId}/items/${itemId}/activate`),
  sellItem: (auctionId: string, itemId: string) =>
    api.post(`/auctions/${auctionId}/items/${itemId}/sell`),
  forceSell: (auctionId: string, itemId: string, body: { team_id: string; amount?: number | null }) =>
    api.post(`/auctions/${auctionId}/items/${itemId}/force-sell`, body),
  markUnsold: (auctionId: string, itemId: string) =>
    api.post(`/auctions/${auctionId}/items/${itemId}/unsold`),
  resetTimer: (auctionId: string, itemId: string, body: { seconds: number }) =>
    api.post(`/auctions/${auctionId}/items/${itemId}/reset-timer`, body),
  placeBid: (auctionId: string, itemId: string, body: object) =>
    api.post(`/auctions/${auctionId}/items/${itemId}/bid`, body),
  listBids: (auctionId: string, itemId: string) =>
    api.get(`/auctions/${auctionId}/items/${itemId}/bids`),
};

// ── Notifications ─────────────────────────────────────────────────────────────
export const notificationsApi = {
  list: (params?: { limit?: number; skip?: number }) => api.get('/notifications/', { params }),
  unreadCount: () => api.get('/notifications/unread-count'),
  markRead: (id: string) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/read-all'),
};

// ── Search ────────────────────────────────────────────────────────────────────
export const searchApi = {
  search: (q: string, limit?: number) => api.get('/search/', { params: { q, limit } }),
};

// ── Admin ─────────────────────────────────────────────────────────────────────
export const adminApi = {
  overview: () => api.get('/admin/overview'),
  exportUsersCsvUrl: () => `${BASE_URL}/admin/export/users.csv`,
  exportBidsCsvUrl: (auctionId?: string) =>
    auctionId ? `${BASE_URL}/admin/export/bids.csv?auction_id=${encodeURIComponent(auctionId)}` : `${BASE_URL}/admin/export/bids.csv`,
  exportTournamentsCsvUrl: () => `${BASE_URL}/admin/export/tournaments.csv`,
  exportPlayersCsvUrl: () => `${BASE_URL}/admin/export/players.csv`,
  exportMatchesCsvUrl: (tournamentId?: string) =>
    tournamentId ? `${BASE_URL}/admin/export/matches.csv?tournament_id=${encodeURIComponent(tournamentId)}` : `${BASE_URL}/admin/export/matches.csv`,
};
