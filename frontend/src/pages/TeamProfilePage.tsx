import { useParams, NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import { teamsApi, playersApi } from '../services/api';
import type { Team, TeamHistoryOut, Player } from '../types';
import { Shield, Users, Wallet, Trophy } from 'lucide-react';
import { PageSkeleton } from '../components/Skeleton';

export default function TeamProfilePage() {
  const { id: teamId } = useParams<{ id: string }>();
  const actualId = teamId || window.location.pathname.split('/').pop()!;

  const { data: team, isLoading: isLoadingTeam } = useQuery<Team>({
    queryKey: ['team', actualId],
    queryFn: () => teamsApi.get(actualId).then(r => r.data),
  });

  const { data: history, isLoading: isLoadingHistory } = useQuery<TeamHistoryOut>({
    queryKey: ['team-history', actualId],
    queryFn: () => teamsApi.getHistory(actualId).then(r => r.data),
  });

  const { data: playersList } = useQuery<Player[]>({
    queryKey: ['players', { team_id: actualId }],
    queryFn: () => playersApi.list({ team_id: actualId }).then(r => r.data),
    enabled: !!team,
  });

  if (isLoadingTeam || isLoadingHistory) return <PageSkeleton />;
  if (!team) return <div className="empty-state"><div className="empty-state-icon">🛡️</div><p>Team not found</p></div>;

  const roster = playersList || [];
  
  const historyData = [
    { name: 'Won', value: history?.won ?? 0, color: '#10b981' },
    { name: 'Lost', value: history?.lost ?? 0, color: '#ef4444' },
    { name: 'Tied', value: history?.tied ?? 0, color: '#f59e0b' }
  ].filter(d => d.value > 0);

  const fmtBudget = (n: number) => n >= 10000000 ? `₹${(n / 10000000).toFixed(2)}Cr` : `₹${(n / 100000).toFixed(2)}L`;

  return (
    <div className="fade-in">
      <div className="page-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {team.logo_url ? (
              <img src={team.logo_url} alt={team.name} style={{ width: 64, height: 64, borderRadius: 'var(--radius)', objectFit: 'cover' }} />
            ) : (
              <div style={{ width: 64, height: 64, borderRadius: 'var(--radius)', background: 'linear-gradient(135deg, var(--blue), var(--purple))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem' }}>
                <Shield size={32} color="white" />
              </div>
            )}
            {team.name}
            {team.short_name && <span style={{ color: 'var(--text-muted)', fontSize: '1.2rem' }}>({team.short_name})</span>}
          </h1>
          <div className="page-subtitle" style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem', alignItems: 'center' }}>
            <span className="badge badge-purple">{team.home_ground || 'No Home Ground'}</span>
            <span className="badge badge-gray" style={{ fontFamily: 'monospace', userSelect: 'all' }}>ID: {team.id}</span>
          </div>
        </div>
      </div>

      <div className="grid-3" style={{ marginBottom: '2rem' }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--accent-light)' }}><Wallet size={24} /></div>
          <div>
            <div className="stat-value" style={{ color: team.remaining_budget < team.budget * 0.2 ? 'var(--red)' : '' }}>
              {fmtBudget(team.remaining_budget)}
            </div>
            <div className="stat-label">Remaining of {fmtBudget(team.budget)}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399' }}><Users size={24} /></div>
          <div><div className="stat-value">{roster.length}</div><div className="stat-label">Players in Roster</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}><Trophy size={24} /></div>
          <div><div className="stat-value">{history?.played ?? 0}</div><div className="stat-label">Matches Played</div></div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><div className="card-title">Win/Loss Record</div></div>
          <div style={{ height: 250, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {historyData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={historyData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                    {historyData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state">No match history available</div>
            )}
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '1rem' }}>
            <div className="badge badge-green">Won: {history?.won ?? 0}</div>
            <div className="badge badge-red">Lost: {history?.lost ?? 0}</div>
            <div className="badge badge-yellow">Tied: {history?.tied ?? 0}</div>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><div className="card-title">Team Roster</div></div>
          <div style={{ maxHeight: 300, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {roster.length === 0 ? (
              <div className="empty-state" style={{ padding: '2rem' }}>No players assigned</div>
            ) : roster.map(p => (
              <NavLink to={`/players/${p.id}`} key={p.id} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '0.75rem', borderRadius: 'var(--radius-sm)', background: 'var(--bg-elevated)',
                textDecoration: 'none', color: 'inherit'
              }}>
                <div>
                  <div className="fw-700">{p.name}</div>
                  <div className="text-muted text-sm">{p.role.replace('_', ' ')} • {p.country}</div>
                </div>
                <div className="badge badge-blue">₹{(p.base_price / 100000).toFixed(1)}L</div>
              </NavLink>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
