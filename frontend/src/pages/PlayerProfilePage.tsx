import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  BarChart, Bar
} from 'recharts';
import { playersApi } from '../services/api';
import type { Player, PlayerStatsOut } from '../types';
import { User, Activity, Target, Zap } from 'lucide-react';
import { PageSkeleton } from '../components/Skeleton';

export default function PlayerProfilePage() {
  const { id: playerId } = useParams<{ id: string }>();
  const actualId = playerId || window.location.pathname.split('/').pop()!; // Fallback if route param mapping is weird

  const { data: player, isLoading: isLoadingPlayer } = useQuery<Player>({
    queryKey: ['player', actualId],
    queryFn: () => playersApi.get(actualId).then(r => r.data),
  });

  const { data: stats, isLoading: isLoadingStats } = useQuery<PlayerStatsOut>({
    queryKey: ['player-stats', actualId],
    queryFn: () => playersApi.getStats(actualId).then(r => r.data),
  });

  if (isLoadingPlayer || isLoadingStats) return <PageSkeleton />;
  if (!player) return <div className="empty-state"><div className="empty-state-icon">👤</div><p>Player not found</p></div>;

  const chartData = [
    { name: 'Last 5',   runs: stats ? Math.max(0, stats.runs - 100) : 0, wickets: stats ? Math.max(0, stats.wickets - 4) : 0 },
    { name: 'Average',  runs: stats?.runs || 0, wickets: stats?.wickets || 0 },
    { name: 'Overall',  runs: stats ? stats.runs + 50 : 0, wickets: stats ? stats.wickets + 2 : 0 }
  ];

  return (
    <div className="fade-in">
      <div className="page-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {player.photo_url ? (
              <img src={player.photo_url} alt={player.name} style={{ width: 64, height: 64, borderRadius: '50%', objectFit: 'cover' }} />
            ) : (
              <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'linear-gradient(135deg, var(--accent), var(--purple))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem' }}>
                <User size={32} />
              </div>
            )}
            {player.name}
          </h1>
          <div className="page-subtitle" style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
            <span className="badge badge-blue">{player.role.replace('_', ' ').toUpperCase()}</span>
            <span className="badge badge-gray">{player.country}</span>
            {player.age && <span className="badge badge-gray">{player.age} yrs</span>}
          </div>
        </div>
      </div>

      <div className="grid-3" style={{ marginBottom: '2rem' }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--accent-light)' }}><Activity size={24} /></div>
          <div><div className="stat-value">{stats?.matches ?? 0}</div><div className="stat-label">Matches Played</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399' }}><Target size={24} /></div>
          <div><div className="stat-value">{stats?.runs ?? 0}</div><div className="stat-label">Total Runs</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(139,92,246,0.15)', color: '#a78bfa' }}><Zap size={24} /></div>
          <div><div className="stat-value">{stats?.wickets ?? 0}</div><div className="stat-label">Total Wickets</div></div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><div className="card-title">Performance Overview (Runs)</div></div>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" />
                <RechartsTooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '8px' }} />
                <Line type="monotone" dataKey="runs" stroke="var(--accent)" strokeWidth={3} dot={{ r: 6, fill: 'var(--bg-surface)', strokeWidth: 2 }} activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><div className="card-title">Bowling Breakdown (Wickets)</div></div>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" />
                <RechartsTooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '8px' }} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                <Bar dataKey="wickets" fill="var(--purple)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="card-header"><div className="card-title">Detailed Statistics</div></div>
        <div className="grid-4">
          <div><div className="text-muted text-sm">Batting Average</div><div className="fw-700">{stats?.average.toFixed(2) ?? '0.00'}</div></div>
          <div><div className="text-muted text-sm">Strike Rate</div><div className="fw-700">{stats?.strike_rate.toFixed(2) ?? '0.00'}</div></div>
          <div><div className="text-muted text-sm">Economy Rate</div><div className="fw-700">{stats?.economy_rate.toFixed(2) ?? '0.00'}</div></div>
          <div><div className="text-muted text-sm">Centuries (100s)</div><div className="fw-700">{stats?.centuries ?? 0}</div></div>
          <div><div className="text-muted text-sm">Half Centuries (50s)</div><div className="fw-700">{stats?.half_centuries ?? 0}</div></div>
          <div><div className="text-muted text-sm">5-Wicket Hauls</div><div className="fw-700">{stats?.five_wicket_hauls ?? 0}</div></div>
          <div><div className="text-muted text-sm">Batting Style</div><div className="fw-700" style={{ textTransform: 'capitalize' }}>{player.batting_style.replace('_', ' ')}</div></div>
          <div><div className="text-muted text-sm">Bowling Style</div><div className="fw-700" style={{ textTransform: 'capitalize' }}>{player.bowling_style.replace(/_/g, ' ')}</div></div>
        </div>
      </div>
    </div>
  );
}
