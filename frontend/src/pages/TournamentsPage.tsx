import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Pencil, Trash2, Trophy, Eye } from 'lucide-react';
import toast from 'react-hot-toast';
import { tournamentsApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Tournament } from '../types';
import { useNavigate } from 'react-router-dom';

const STATUS_BADGE: Record<string, string> = {
  upcoming: 'badge badge-blue', ongoing: 'badge badge-red badge-live',
  completed: 'badge badge-green', cancelled: 'badge badge-gray',
};

function TournamentModal({ onClose, existing }: { onClose: () => void; existing?: Tournament }) {
  const qc = useQueryClient();
  const [name, setName] = useState(existing?.name ?? '');
  const [desc, setDesc] = useState(existing?.description ?? '');
  const [type, setType] = useState(existing?.tournament_type ?? 'league');
  const [maxTeams, setMaxTeams] = useState(existing?.max_teams ?? 8);

  const mutation = useMutation({
    mutationFn: (body: object) =>
      existing ? tournamentsApi.update(existing.id, body) : tournamentsApi.create(body),
    onSuccess: () => {
      toast.success(existing ? 'Tournament updated' : 'Tournament created!');
      qc.invalidateQueries({ queryKey: ['tournaments'] });
      onClose();
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Failed'),
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">{existing ? 'Edit Tournament' : 'New Tournament'}</div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={e => { e.preventDefault(); mutation.mutate({ name, description: desc, tournament_type: type, max_teams: maxTeams }); }}>
          <div className="form-group"><label className="form-label">Name</label>
            <input value={name} onChange={e => setName(e.target.value)} required placeholder="IPL 2025" /></div>
          <div className="form-group"><label className="form-label">Description</label>
            <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={2}
              style={{ resize: 'vertical', background: 'var(--bg-elevated)', color: 'var(--text-primary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '0.6rem 0.9rem', width: '100%', fontFamily: 'inherit' }} /></div>
          <div className="form-group"><label className="form-label">Type</label>
            <select value={type} onChange={e => setType(e.target.value)}>
              {['league','knockout','t20','odi','test'].map(t => <option key={t} value={t}>{t.toUpperCase()}</option>)}
            </select></div>
          <div className="form-group"><label className="form-label">Max Teams</label>
            <input type="number" value={maxTeams} min={2} max={32} onChange={e => setMaxTeams(+e.target.value)} /></div>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function TournamentsPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [modal, setModal] = useState<{ open: boolean; tournament?: Tournament }>({ open: false });

  const { data: tournaments = [], isLoading } = useQuery({
    queryKey: ['tournaments'],
    queryFn: () => tournamentsApi.list().then(r => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => tournamentsApi.delete(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries({ queryKey: ['tournaments'] }); },
  });

  const canEdit = hasRole('admin', 'organizer');

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Tournaments</h1>
          <p className="page-subtitle">{tournaments.length} tournaments registered</p>
        </div>
        {canEdit && (
          <button className="btn btn-primary" onClick={() => setModal({ open: true })}>
            <Plus size={16} /> New Tournament
          </button>
        )}
      </div>

      {isLoading ? <div className="spinner" /> : tournaments.length === 0 ? (
        <div className="empty-state"><div className="empty-state-icon">🏆</div><p>No tournaments yet.</p>
          {canEdit && <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={() => setModal({ open: true })}><Plus size={16} /> Create one</button>}
        </div>
      ) : (
        <div className="grid-3">
          {tournaments.map((t: Tournament) => (
            <div key={t.id} className="card">
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <div style={{ fontSize: '2rem' }}>🏆</div>
                <span className={STATUS_BADGE[t.status] ?? 'badge badge-gray'}>{t.status}</span>
              </div>
              <div style={{ fontWeight: 700, fontSize: '1.05rem', marginBottom: '0.25rem' }}>{t.name}</div>
              {t.description && <div className="text-muted text-sm" style={{ marginBottom: '0.75rem' }}>{t.description}</div>}
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                <span className="badge badge-purple">{t.tournament_type.toUpperCase()}</span>
                <span className="badge badge-gray">{t.max_teams} teams</span>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {canEdit && (
                  <>
                    <button className="btn btn-secondary btn-sm" onClick={() => setModal({ open: true, tournament: t })}>
                      <Pencil size={13} /> Edit
                    </button>
                    <button className="btn btn-danger btn-sm" onClick={() => { if (confirm('Delete?')) deleteMutation.mutate(t.id); }}>
                      <Trash2 size={13} /> Delete
                    </button>
                  </>
                )}
                <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/tournaments/${t.id}`)}>
                  <Eye size={13} /> View
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {modal.open && <TournamentModal onClose={() => setModal({ open: false })} existing={modal.tournament} />}
    </div>
  );
}
