import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Pencil, Trash2, Eye } from 'lucide-react';
import toast from 'react-hot-toast';
import { teamsApi, tournamentsApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Team, Tournament } from '../types';
import { useNavigate } from 'react-router-dom';

function TeamModal({ onClose, existing }: { onClose: () => void; existing?: Team }) {
  const qc = useQueryClient();
  const { data: tournaments = [] } = useQuery({ queryKey: ['tournaments'], queryFn: () => tournamentsApi.list().then(r => r.data) });
  const [name, setName] = useState(existing?.name ?? '');
  const [shortName, setShortName] = useState(existing?.short_name ?? '');
  const [tournamentId, setTournamentId] = useState(existing?.tournament_id ?? '');
  const [budget, setBudget] = useState(existing?.budget ?? 10000000);
  const [homeGround, setHomeGround] = useState(existing?.home_ground ?? '');

  const mutation = useMutation({
    mutationFn: (body: object) => existing ? teamsApi.update(existing.id, body) : teamsApi.create(body),
    onSuccess: () => { toast.success(existing ? 'Team updated' : 'Team created!'); qc.invalidateQueries({ queryKey: ['teams'] }); onClose(); },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Failed'),
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">{existing ? 'Edit Team' : 'New Team'}</div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={e => { e.preventDefault(); mutation.mutate({ name, short_name: shortName, tournament_id: tournamentId || undefined, budget, home_ground: homeGround || undefined }); }}>
          <div className="form-group"><label className="form-label">Team Name</label><input value={name} onChange={e => setName(e.target.value)} required placeholder="Mumbai Indians" /></div>
          <div className="form-group"><label className="form-label">Short Name</label><input value={shortName} onChange={e => setShortName(e.target.value)} placeholder="MI" maxLength={5} /></div>
          <div className="form-group"><label className="form-label">Tournament</label>
            <select value={tournamentId} onChange={e => setTournamentId(e.target.value)}>
              <option value="">— None —</option>
              {tournaments.map((t: Tournament) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          <div className="form-group"><label className="form-label">Budget (₹)</label><input type="number" value={budget} onChange={e => setBudget(+e.target.value)} min={0} step={100000} /></div>
          <div className="form-group"><label className="form-label">Home Ground</label><input value={homeGround} onChange={e => setHomeGround(e.target.value)} placeholder="Wankhede Stadium" /></div>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>{mutation.isPending ? 'Saving…' : 'Save'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

const fmt = (n: number) => n >= 10000000 ? `₹${(n / 10000000).toFixed(2)}Cr` : `₹${(n / 100000).toFixed(2)}L`;

export default function TeamsPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [modal, setModal] = useState<{ open: boolean; team?: Team }>({ open: false });

  const { data: teams = [], isLoading } = useQuery({ queryKey: ['teams'], queryFn: () => teamsApi.list().then(r => r.data) });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => teamsApi.delete(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries({ queryKey: ['teams'] }); },
  });

  const canEdit = hasRole('admin', 'organizer', 'team_owner');

  return (
    <div className="fade-in">
      <div className="page-header">
        <div><h1 className="page-title">Teams</h1><p className="page-subtitle">{teams.length} registered teams</p></div>
        {canEdit && <button className="btn btn-primary" onClick={() => setModal({ open: true })}><Plus size={16} /> New Team</button>}
      </div>

      {isLoading ? <div className="spinner" /> : teams.length === 0 ? (
        <div className="empty-state"><div className="empty-state-icon">🛡️</div><p>No teams yet.</p></div>
      ) : (
        <div className="grid-3">
          {teams.map((t: Team) => (
            <div key={t.id} className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                <div style={{ width: 48, height: 48, borderRadius: 'var(--radius-sm)', background: 'linear-gradient(135deg,var(--accent),var(--purple))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '1.1rem' }}>
                  {t.short_name ?? t.name.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{t.name}</div>
                  {t.home_ground && <div className="text-muted text-sm">{t.home_ground}</div>}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                <span className="badge badge-green">Budget {fmt(t.budget)}</span>
                <span className="badge badge-blue">Remaining {fmt(t.remaining_budget)}</span>
                <span className="badge badge-gray">{t.players.length} players</span>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {canEdit && (
                  <button className="btn btn-secondary btn-sm" onClick={() => setModal({ open: true, team: t })}>
                    <Pencil size={13} /> Edit
                  </button>
                )}
                {canEdit && (
                  <button className="btn btn-danger btn-sm" onClick={() => { if (confirm('Delete?')) deleteMutation.mutate(t.id); }}>
                    <Trash2 size={13} /> Delete
                  </button>
                )}
                <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/teams/${t.id}`)}>
                  <Eye size={13} /> View
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      {modal.open && <TeamModal onClose={() => setModal({ open: false })} existing={modal.team} />}
    </div>
  );
}
