import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Gavel, Play, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { auctionsApi, tournamentsApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Auction, Tournament } from '../types';

const STATUS_BADGE: Record<string, string> = {
  upcoming: 'badge badge-blue', live: 'badge badge-red badge-live',
  paused: 'badge badge-yellow', completed: 'badge badge-green',
};

function AuctionModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const { data: tournaments = [] } = useQuery({ queryKey: ['tournaments'], queryFn: () => tournamentsApi.list().then(r => r.data) });
  const [name, setName] = useState('');
  const [tournamentId, setTournamentId] = useState('');
  const [timer, setTimer] = useState(30);

  const mutation = useMutation({
    mutationFn: (body: object) => auctionsApi.create(body),
    onSuccess: () => { toast.success('Auction created!'); qc.invalidateQueries({ queryKey: ['auctions'] }); onClose(); },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Failed'),
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">New Auction</div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={e => { e.preventDefault(); mutation.mutate({ name, tournament_id: tournamentId, bid_timer_seconds: timer }); }}>
          <div className="form-group"><label className="form-label">Auction Name</label>
            <input value={name} onChange={e => setName(e.target.value)} required placeholder="IPL 2025 Mega Auction" /></div>
          <div className="form-group"><label className="form-label">Tournament</label>
            <select value={tournamentId} onChange={e => setTournamentId(e.target.value)} required>
              <option value="">Select tournament</option>
              {tournaments.map((t: Tournament) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select></div>
          <div className="form-group"><label className="form-label">Bid Timer (seconds)</label>
            <input type="number" value={timer} min={5} max={120} onChange={e => setTimer(+e.target.value)} /></div>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>{mutation.isPending ? 'Creating…' : 'Create'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AuctionsPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const { data: auctions = [], isLoading } = useQuery({
    queryKey: ['auctions'],
    queryFn: () => auctionsApi.list().then(r => r.data),
    refetchInterval: 5000,
  });

  const startMutation = useMutation({
    mutationFn: (id: string) => auctionsApi.update(id, { status: 'live' }),
    onSuccess: () => { toast.success('Auction is now LIVE 🔴'); qc.invalidateQueries({ queryKey: ['auctions'] }); },
  });

  const canEdit = hasRole('admin', 'organizer');

  return (
    <div className="fade-in">
      <div className="page-header">
        <div><h1 className="page-title">Auctions</h1><p className="page-subtitle">{auctions.length} auctions total</p></div>
        {canEdit && <button className="btn btn-primary" onClick={() => setShowModal(true)}><Plus size={16} /> New Auction</button>}
      </div>

      {isLoading ? <div className="spinner" /> : auctions.length === 0 ? (
        <div className="empty-state"><div className="empty-state-icon">🔨</div><p>No auctions yet.</p></div>
      ) : (
        <div className="grid-3">
          {auctions.map((a: Auction) => (
            <div key={a.id} className="card" style={{ borderColor: a.status === 'live' ? 'rgba(239,68,68,0.4)' : undefined }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                <div style={{ fontSize: '2rem' }}>🔨</div>
                <span className={STATUS_BADGE[a.status] ?? 'badge badge-gray'}>{a.status}</span>
              </div>
              <div style={{ fontWeight: 700, fontSize: '1.05rem', marginBottom: '0.25rem' }}>{a.name}</div>
              <div className="text-muted text-sm" style={{ marginBottom: '1rem' }}>
                ⏱ {a.bid_timer_seconds}s per player
                {a.started_at && ` · Started ${new Date(a.started_at).toLocaleDateString()}`}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <Link to={`/auctions/${a.id}`} className="btn btn-secondary btn-sm"><ExternalLink size={13} /> Open Room</Link>
                {canEdit && a.status === 'upcoming' && (
                  <button className="btn btn-success btn-sm" onClick={() => startMutation.mutate(a.id)}>
                    <Play size={13} /> Go Live
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {showModal && <AuctionModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
