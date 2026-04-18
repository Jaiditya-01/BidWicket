import { useParams, NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { tournamentsApi, teamsApi, matchesApi } from '../services/api';
import type { Tournament, Team, Match } from '../types';
import { Trophy, Calendar, Users, Activity, Shield } from 'lucide-react';
import { PageSkeleton } from '../components/Skeleton';

export default function TournamentDetailPage() {
  const { id: tournamentId } = useParams<{ id: string }>();
  const actualId = tournamentId || window.location.pathname.split('/').pop()!;

  const { data: tournament, isLoading: loading1 } = useQuery<Tournament>({
    queryKey: ['tournament', actualId],
    queryFn: () => tournamentsApi.get(actualId).then(r => r.data),
  });

  const { data: teams = [], isLoading: loading2 } = useQuery<Team[]>({
    queryKey: ['tournament-teams', actualId],
    queryFn: () => teamsApi.list({ tournament_id: actualId }).then(r => r.data),
  });

  const { data: matches = [], isLoading: loading3 } = useQuery<Match[]>({
    queryKey: ['tournament-matches', actualId],
    queryFn: () => matchesApi.list({ tournament_id: actualId }).then(r => r.data),
  });

  if (loading1 || loading2 || loading3) return <PageSkeleton />;
  if (!tournament) return <div className="empty-state"><div className="empty-state-icon">🏆</div><p>Tournament not found</p></div>;

  return (
    <div className="fade-in">
      <div className="page-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {tournament.logo_url ? (
              <img src={tournament.logo_url} alt={tournament.name} style={{ width: 64, height: 64, borderRadius: 'var(--radius)', objectFit: 'cover' }} />
            ) : (
              <div style={{ width: 64, height: 64, borderRadius: 'var(--radius)', background: 'linear-gradient(135deg, var(--accent), var(--purple))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem' }}>
                <Trophy size={32} color="white" />
              </div>
            )}
            {tournament.name}
          </h1>
          <div className="page-subtitle" style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
            <span className="badge badge-accent">{tournament.tournament_type.toUpperCase()}</span>
            <span className={
              tournament.status === 'upcoming' ? 'badge badge-yellow' :
              tournament.status === 'ongoing' ? 'badge badge-green badge-live' :
              tournament.status === 'completed' ? 'badge badge-blue' : 'badge badge-red'
            }>{tournament.status}</span>
          </div>
          {tournament.description && (
            <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>{tournament.description}</p>
          )}
        </div>
      </div>

      <div className="grid-3" style={{ marginBottom: '2rem' }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--accent-light)' }}><Users size={24} /></div>
          <div><div className="stat-value">{teams.length} / {tournament.max_teams}</div><div className="stat-label">Teams Enrolled</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399' }}><Activity size={24} /></div>
          <div><div className="stat-value">{matches.length}</div><div className="stat-label">Matches Scheduled</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(139,92,246,0.15)', color: '#a78bfa' }}><Calendar size={24} /></div>
          <div>
            <div className="stat-value" style={{ fontSize: '1.2rem' }}>
              {tournament.start_date ? new Date(tournament.start_date).toLocaleDateString() : 'TBD'}
            </div>
            <div className="stat-label">Start Date</div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><div className="card-title">Teams</div></div>
          {teams.length === 0 ? (
            <div className="empty-state">No teams enrolled</div>
          ) : (
            <div className="grid-2">
              {teams.map(team => (
                <NavLink to={`/teams/${team.id}`} key={team.id} style={{
                  display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem', 
                  borderRadius: 'var(--radius-sm)', background: 'var(--bg-elevated)', textDecoration: 'none'
                }}>
                  <div style={{ width: 40, height: 40, borderRadius: 'var(--radius)', background: 'var(--bg-card)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Shield size={20} color="var(--accent-light)" />
                  </div>
                  <div>
                    <div className="fw-700 text-primary">{team.name}</div>
                    <div className="text-muted text-sm">{team.players.length} players</div>
                  </div>
                </NavLink>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header"><div className="card-title">Recent Matches</div></div>
          {matches.length === 0 ? (
            <div className="empty-state">No matches scheduled</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {matches.slice(0, 5).map(match => {
                const t1 = teams.find(t => t.id === match.team1_id);
                const t2 = teams.find(t => t.id === match.team2_id);
                return (
                  <NavLink to={`/matches/${match.id}`} key={match.id} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '0.75rem', borderRadius: 'var(--radius-sm)', background: 'var(--bg-elevated)',
                    textDecoration: 'none', color: 'inherit'
                  }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                      <div className="fw-700">{t1?.name ?? 'Team 1'} <span className="text-muted">vs</span> {t2?.name ?? 'Team 2'}</div>
                      <div className="text-muted text-sm">{match.venue || 'TBA'} • {new Date(match.match_date!).toLocaleDateString()}</div>
                    </div>
                    <div>
                      <span className={
                        match.status === 'live' ? 'badge badge-red badge-live' :
                        match.status === 'completed' ? 'badge badge-green' : 'badge badge-gray'
                      }>{match.status}</span>
                    </div>
                  </NavLink>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
