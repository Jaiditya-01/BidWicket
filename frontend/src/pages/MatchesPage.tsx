import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Pencil, Trash2, Radio } from 'lucide-react';
import toast from 'react-hot-toast';
import { matchesApi, teamsApi, tournamentsApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Match, Team, Tournament } from '../types';
import { useNavigate } from 'react-router-dom';

const STATUS_BADGE: Record<string, string> = {
  scheduled: 'badge badge-blue', live: 'badge badge-red badge-live',
  completed: 'badge badge-green', abandoned: 'badge badge-gray',
};

function MatchModal({ onClose, existing }: { onClose: () => void; existing?: Match }) {
  const qc = useQueryClient();
  const { data: tournaments = [] } = useQuery({ queryKey: ['tournaments'], queryFn: () => tournamentsApi.list().then(r => r.data) });
  const { data: teams = [] } = useQuery({ queryKey: ['teams'], queryFn: () => teamsApi.list().then(r => r.data) });
  const [tournamentId, setTournamentId] = useState(existing?.tournament_id ?? '');
  const [team1, setTeam1] = useState(existing?.team1_id ?? '');
  const [team2, setTeam2] = useState(existing?.team2_id ?? '');
  const [venue, setVenue] = useState(existing?.venue ?? '');
  const [matchDate, setMatchDate] = useState(existing?.match_date?.slice(0, 16) ?? '');

  const mutation = useMutation({
    mutationFn: (body: object) => existing ? matchesApi.update(existing.id, body) : matchesApi.create(body),
    onSuccess: () => { toast.success(existing ? 'Match updated' : 'Match created!'); qc.invalidateQueries({ queryKey: ['matches'] }); onClose(); },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Failed'),
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">{existing ? 'Edit Match' : 'New Match'}</div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={e => { e.preventDefault(); mutation.mutate({ tournament_id: tournamentId, team1_id: team1, team2_id: team2, venue: venue || undefined, match_date: matchDate || undefined }); }}>
          <div className="form-group"><label className="form-label">Tournament</label>
            <select value={tournamentId} onChange={e => setTournamentId(e.target.value)} required>
              <option value="">Select tournament</option>
              {tournaments.map((t: Tournament) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select></div>
          <div className="form-group"><label className="form-label">Team 1</label>
            <select value={team1} onChange={e => setTeam1(e.target.value)} required>
              <option value="">Select team</option>
              {teams.map((t: Team) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select></div>
          <div className="form-group"><label className="form-label">Team 2</label>
            <select value={team2} onChange={e => setTeam2(e.target.value)} required>
              <option value="">Select team</option>
              {teams.filter((t: Team) => t.id !== team1).map((t: Team) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select></div>
          <div className="form-group"><label className="form-label">Venue</label><input value={venue} onChange={e => setVenue(e.target.value)} placeholder="Eden Gardens" /></div>
          <div className="form-group"><label className="form-label">Date & Time</label><input type="datetime-local" value={matchDate} onChange={e => setMatchDate(e.target.value)} /></div>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>{mutation.isPending ? 'Saving…' : 'Save'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function MatchesPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [modal, setModal] = useState<{ open: boolean; match?: Match }>({ open: false });
  const { data: matches = [], isLoading } = useQuery({ queryKey: ['matches'], queryFn: () => matchesApi.list().then(r => r.data) });
  const { data: teams = [] } = useQuery({ queryKey: ['teams'], queryFn: () => teamsApi.list().then(r => r.data) });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => matchesApi.delete(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries({ queryKey: ['matches'] }); },
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => matchesApi.update(id, { status }),
    onSuccess: (_d, vars) => {
      toast.success(vars.status === 'live' ? '🔴 Match is now LIVE!' : vars.status === 'completed' ? '✅ Match completed!' : 'Status updated');
      qc.invalidateQueries({ queryKey: ['matches'] });
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Failed to update status'),
  });

  const teamName = (id: string) => teams.find((t: Team) => t.id === id)?.name ?? id.slice(-6);
  const canEdit = hasRole('admin', 'organizer');

  return (
    <div className="fade-in">
      <div className="page-header">
        <div><h1 className="page-title">Matches</h1><p className="page-subtitle">{matches.length} matches scheduled</p></div>
        {canEdit && <button className="btn btn-primary" onClick={() => setModal({ open: true })}><Plus size={16} /> New Match</button>}
      </div>

      {isLoading ? <div className="spinner" /> : matches.length === 0 ? (
        <div className="empty-state"><div className="empty-state-icon">🏏</div><p>No matches yet.</p></div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Match</th><th>Venue</th><th>Date</th><th>Status</th><th>Score</th><th>Actions</th></tr></thead>
            <tbody>
              {matches.map((m: Match) => (
                <tr key={m.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{teamName(m.team1_id)} vs {teamName(m.team2_id)}</div>
                  </td>
                  <td className="text-muted">{m.venue ?? '—'}</td>
                  <td className="text-muted text-sm">{m.match_date ? new Date(m.match_date).toLocaleString() : '—'}</td>
                  <td><span className={STATUS_BADGE[m.status] ?? 'badge badge-gray'}>{m.status}</span></td>
                  <td className="text-sm">
                    {m.innings1 ? `${m.innings1.runs}/${m.innings1.wickets}` : '—'}
                    {m.innings2 ? ` | ${m.innings2.runs}/${m.innings2.wickets}` : ''}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                      {canEdit && (
                        <>
                          <button className="btn btn-secondary btn-sm" onClick={() => setModal({ open: true, match: m })}><Pencil size={12} /></button>
                          <button className="btn btn-danger btn-sm" onClick={() => { if (confirm('Delete?')) deleteMutation.mutate(m.id); }}><Trash2 size={12} /></button>
                        </>
                      )}
                      {canEdit && m.status === 'scheduled' && (
                        <button
                          className="btn btn-success btn-sm"
                          onClick={() => statusMutation.mutate({ id: m.id, status: 'live' })}
                          disabled={statusMutation.isPending}
                        >▶ Go Live</button>
                      )}
                      {canEdit && m.status === 'live' && (
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => { if (confirm('Mark this match as completed?')) statusMutation.mutate({ id: m.id, status: 'completed' }); }}
                          disabled={statusMutation.isPending}
                        >✓ End Match</button>
                      )}
                      <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/matches/${m.id}`)}><Radio size={12} /> Live / View</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {modal.open && <MatchModal onClose={() => setModal({ open: false })} existing={modal.match} />}
    </div>
  );
}
