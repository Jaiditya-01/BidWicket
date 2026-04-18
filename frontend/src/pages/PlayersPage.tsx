import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Pencil, Trash2, Search, Eye } from 'lucide-react';
import toast from 'react-hot-toast';
import { playersApi, teamsApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Player, Team } from '../types';
import { useNavigate } from 'react-router-dom';

const ROLE_COLORS: Record<string, string> = {
  batsman: 'badge-blue', bowler: 'badge-red', all_rounder: 'badge-purple', wicket_keeper: 'badge-yellow',
};
const fmt = (n: number) => `₹${(n / 100000).toFixed(1)}L`;

function PlayerModal({ onClose, existing }: { onClose: () => void; existing?: Player }) {
  const qc = useQueryClient();
  const [name, setName] = useState(existing?.name ?? '');
  const [country, setCountry] = useState(existing?.country ?? 'India');
  const [age, setAge] = useState(existing?.age ?? '');
  const [role, setRole] = useState(existing?.role ?? 'batsman');
  const [basePrice, setBasePrice] = useState(existing?.base_price ?? 100000);
  const [bio, setBio] = useState(existing?.bio ?? '');

  const mutation = useMutation({
    mutationFn: (body: object) => existing ? playersApi.update(existing.id, body) : playersApi.create(body),
    onSuccess: () => { toast.success(existing ? 'Player updated' : 'Player added!'); qc.invalidateQueries({ queryKey: ['players'] }); onClose(); },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Failed'),
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">{existing ? 'Edit Player' : 'Add Player'}</div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={e => { e.preventDefault(); mutation.mutate({ name, country, age: age ? +age : undefined, role, base_price: basePrice, bio: bio || undefined }); }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 1rem' }}>
            <div className="form-group"><label className="form-label">Name</label><input value={name} onChange={e => setName(e.target.value)} required placeholder="MS Dhoni" /></div>
            <div className="form-group"><label className="form-label">Country</label><input value={country} onChange={e => setCountry(e.target.value)} /></div>
            <div className="form-group"><label className="form-label">Age</label><input type="number" value={age} onChange={e => setAge(e.target.value)} min={10} max={60} /></div>
            <div className="form-group"><label className="form-label">Base Price (₹)</label><input type="number" value={basePrice} onChange={e => setBasePrice(+e.target.value)} min={0} step={50000} /></div>
          </div>
          <div className="form-group"><label className="form-label">Role</label>
            <select value={role} onChange={e => setRole(e.target.value)}>
              {['batsman','bowler','all_rounder','wicket_keeper'].map(r => <option key={r} value={r}>{r.replace('_',' ').replace(/\b\w/g, c => c.toUpperCase())}</option>)}
            </select>
          </div>
          <div className="form-group"><label className="form-label">Bio</label>
            <textarea value={bio} onChange={e => setBio(e.target.value)} rows={2}
              style={{ resize: 'vertical', background: 'var(--bg-elevated)', color: 'var(--text-primary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '0.6rem 0.9rem', width: '100%', fontFamily: 'inherit' }} />
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>{mutation.isPending ? 'Saving…' : 'Save'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function PlayersPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [modal, setModal] = useState<{ open: boolean; player?: Player }>({ open: false });
  const [search, setSearch] = useState('');
  const [filterRole, setFilterRole] = useState('');

  const { data: players = [], isLoading } = useQuery({ queryKey: ['players'], queryFn: () => playersApi.list().then(r => r.data) });
  const { data: teams = [] } = useQuery<Team[]>({ queryKey: ['teams'], queryFn: () => teamsApi.list().then(r => r.data) });
  const teamMap = Object.fromEntries((teams as Team[]).map((t: Team) => [t.id, t.name]));

  const deleteMutation = useMutation({
    mutationFn: (id: string) => playersApi.delete(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries({ queryKey: ['players'] }); },
  });

  const canEdit = hasRole('admin', 'organizer', 'team_owner');

  const filtered = players.filter((p: Player) => {
    const matchSearch = p.name.toLowerCase().includes(search.toLowerCase()) || p.country.toLowerCase().includes(search.toLowerCase());
    const matchRole = filterRole ? p.role === filterRole : true;
    return matchSearch && matchRole;
  });

  return (
    <div className="fade-in">
      <div className="page-header">
        <div><h1 className="page-title">Players</h1><p className="page-subtitle">{players.length} registered players</p></div>
        {canEdit && <button className="btn btn-primary" onClick={() => setModal({ open: true })}><Plus size={16} /> Add Player</button>}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input placeholder="Search by name or country…" value={search} onChange={e => setSearch(e.target.value)} style={{ paddingLeft: '2.2rem' }} />
        </div>
        <select value={filterRole} onChange={e => setFilterRole(e.target.value)} style={{ width: 'auto', minWidth: 160 }}>
          <option value="">All Roles</option>
          {['batsman','bowler','all_rounder','wicket_keeper'].map(r => <option key={r} value={r}>{r.replace('_',' ')}</option>)}
        </select>
      </div>

      {isLoading ? <div className="spinner" /> : (
        <div className="table-wrap">
          <table>
            <thead><tr>
              <th>Player</th><th>Country</th><th>Role</th><th>Base Price</th>
              <th>Matches</th><th>Runs</th><th>Wickets</th><th>Status</th>
              <th>Actions</th>
            </tr></thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={9} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No players found</td></tr>
              ) : filtered.map((p: Player) => (
                <tr key={p.id}>
                  <td><div style={{ fontWeight: 600 }}>{p.name}</div>{p.age && <div className="text-muted text-sm">Age {p.age}</div>}</td>
                  <td>{p.country}</td>
                  <td><span className={`badge ${ROLE_COLORS[p.role]}`}>{p.role.replace('_',' ')}</span></td>
                  <td style={{ fontWeight: 600 }}>{fmt(p.base_price)}</td>
                  <td>{p.stats.matches}</td>
                  <td>{p.stats.runs}</td>
                  <td>{p.stats.wickets}</td>
                  <td>
                    {p.is_available
                      ? <span className="badge badge-green">Available</span>
                      : <>
                          <span className="badge badge-gray">Sold</span>
                          {p.team_id && teamMap[p.team_id] && (
                            <div className="text-muted text-sm" style={{ marginTop: '0.2rem' }}>{teamMap[p.team_id]}</div>
                          )}
                        </>
                    }
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                      {canEdit && (
                        <>
                          <button className="btn btn-secondary btn-sm" onClick={() => setModal({ open: true, player: p })}><Pencil size={12} /></button>
                          <button className="btn btn-danger btn-sm" onClick={() => { if (confirm('Delete?')) deleteMutation.mutate(p.id); }}><Trash2 size={12} /></button>
                        </>
                      )}
                      <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/players/${p.id}`)}><Eye size={12} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {modal.open && <PlayerModal onClose={() => setModal({ open: false })} existing={modal.player} />}
    </div>
  );
}
