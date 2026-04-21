import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Trophy, Users, UserCircle, Gavel, Swords, TrendingUp } from 'lucide-react';
import { tournamentsApi, teamsApi, playersApi, auctionsApi, matchesApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Tournament, Auction, Match } from '../types';

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number | string; color: string }) {
  return (
    <div className="stat-card">
      <div className="stat-icon" style={{ background: `${color}22`, color }}>{icon}</div>
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    live: 'badge badge-red badge-live', ongoing: 'badge badge-red badge-live',
    upcoming: 'badge badge-blue', scheduled: 'badge badge-blue',
    completed: 'badge badge-green', paused: 'badge badge-yellow',
    cancelled: 'badge badge-gray', abandoned: 'badge badge-gray',
  };
  return map[status] ?? 'badge badge-gray';
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: tournaments } = useQuery({ queryKey: ['tournaments'], queryFn: () => tournamentsApi.list().then(r => r.data) });
  const { data: teams } = useQuery({ queryKey: ['teams'], queryFn: () => teamsApi.list().then(r => r.data) });
  const { data: players } = useQuery({ queryKey: ['players'], queryFn: () => playersApi.list({ limit: 100 }).then(r => r.data) });
  const { data: auctions } = useQuery({ queryKey: ['auctions'], queryFn: () => auctionsApi.list().then(r => r.data) });
  const { data: matches } = useQuery({ queryKey: ['matches'], queryFn: () => matchesApi.list().then(r => r.data) });

  const liveAuctions = (auctions ?? []).filter((a: Auction) => a.status === 'live');
  const liveMatches = (matches ?? []).filter((m: Match) => m.status === 'live');
  const recentTournaments = (tournaments ?? []).slice(0, 5);

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Welcome back, {user?.full_name?.split(' ')[0]} 👋</p>
        </div>
        <Link to="/tournaments" className="btn btn-primary">
          <Trophy size={16} /> New Tournament
        </Link>
      </div>

      {/* Stats */}
      <div className="grid-4" style={{ marginBottom: '2rem' }}>
        <StatCard icon={<Trophy size={22} />} label="Tournaments" value={tournaments?.length ?? 0} color="var(--accent)" />
        <StatCard icon={<Users size={22} />} label="Teams" value={teams?.length ?? 0} color="var(--purple)" />
        <StatCard icon={<UserCircle size={22} />} label="Players" value={players?.length ?? 0} color="var(--green)" />
        <StatCard icon={<Gavel size={22} />} label="Auctions" value={auctions?.length ?? 0} color="var(--yellow)" />
      </div>

      {/* Live now banner */}
      {(liveAuctions.length > 0 || liveMatches.length > 0) && (
        <div className="card" style={{ borderColor: 'var(--red)', marginBottom: '1.5rem', background: 'rgba(239,68,68,0.05)' }}>
          <div className="card-header">
            <div className="card-title" style={{ color: 'var(--red)' }}>🔴 Live Now</div>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
            {liveAuctions.map((a: Auction) => (
              <Link key={a.id} to={`/auctions/${a.id}`} className="btn btn-danger btn-sm">
                <Gavel size={14} /> {a.name}
              </Link>
            ))}
            {liveMatches.map((m: Match) => (
              <Link key={m.id} to={`/matches/${m.id}`} className="btn btn-danger btn-sm">
                <Swords size={14} /> Match #{m.id.slice(-4)}
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="grid-2">
        {/* Recent Tournaments */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Recent Tournaments</div>
              <div className="card-subtitle">{tournaments?.length ?? 0} total</div>
            </div>
            <Link to="/tournaments" className="btn btn-secondary btn-sm">View all</Link>
          </div>
          {recentTournaments.length === 0 ? (
            <div className="empty-state"><div className="empty-state-icon">🏆</div>No tournaments yet</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {recentTournaments.map((t: Tournament) => (
                <Link key={t.id} to={`/tournaments/${t.id}`}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.6rem 0', borderBottom: '1px solid var(--border)' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{t.name}</div>
                    <div className="text-muted text-sm">{t.tournament_type.toUpperCase()} · {t.max_teams} teams</div>
                  </div>
                  <span className={statusBadge(t.status)}>{t.status}</span>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent Auctions */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Auctions</div>
              <div className="card-subtitle">{liveAuctions.length} live</div>
            </div>
            <Link to="/auctions" className="btn btn-secondary btn-sm">View all</Link>
          </div>
          {(auctions ?? []).length === 0 ? (
            <div className="empty-state"><div className="empty-state-icon">🔨</div>No auctions yet</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {(auctions ?? []).slice(0, 5).map((a: Auction) => (
                <Link key={a.id} to={`/auctions/${a.id}`}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.6rem 0', borderBottom: '1px solid var(--border)' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{a.name}</div>
                    <div className="text-muted text-sm">Timer: {a.bid_timer_seconds}s per item</div>
                  </div>
                  <span className={statusBadge(a.status)}>{a.status}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
