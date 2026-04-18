import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Gavel, ChevronUp, Users, Plus } from 'lucide-react';
import { auctionsApi, playersApi, teamsApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../hooks/useWebSocket';
import type { Auction, AuctionItem, Player, WsEvent, Team } from '../types';

const fmt = (n: number) => n >= 10000000
  ? `₹${(n / 10000000).toFixed(2)}Cr`
  : `₹${(n / 100000).toFixed(2)}L`;

// ── Timer ─────────────────────────────────────────────────────────────────────
function useTimer(endsAt: string | null | undefined, defaultSeconds: number) {
  const [remaining, setRemaining] = useState(defaultSeconds);
  useEffect(() => {
    if (!endsAt) { setRemaining(defaultSeconds); return; }
    
    const update = () => {
      // Ensure the string parses as UTC if the backend returned a naive ISO string
      const tzString = endsAt.includes('Z') || endsAt.includes('+') ? endsAt : `${endsAt}Z`;
      const ms = new Date(tzString).getTime() - Date.now();
      setRemaining(Math.max(0, Math.ceil(ms / 1000)));
    };
    
    update();
    const iv = setInterval(update, 1000);
    return () => clearInterval(iv);
  }, [endsAt, defaultSeconds]);
  return remaining;
}

export default function AuctionRoomPage() {
  const { auctionId } = useParams<{ auctionId: string }>();
  const { user, hasRole } = useAuth();
  const qc = useQueryClient();
  const [bidAmount, setBidAmount] = useState('');
  const [teamId, setTeamId] = useState('');
  const [liveBids, setLiveBids] = useState<Array<{ amount: number; team_id: string; bidder_id: string }>>([]);
  const [activeItemId, setActiveItemId] = useState<string | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState('');

  const { data: auction } = useQuery<Auction>({
    queryKey: ['auction', auctionId],
    queryFn: () => auctionsApi.get(auctionId!).then(r => r.data),
    refetchInterval: 5000,
  });

  const { data: items = [] } = useQuery<AuctionItem[]>({
    queryKey: ['auction-items', auctionId],
    queryFn: () => auctionsApi.listItems(auctionId!).then(r => r.data),
    refetchInterval: 3000,
  });

  const { data: myTeams = [] } = useQuery<Team[]>({
    queryKey: ['teams', 'my'],
    queryFn: () => teamsApi.list().then(r => r.data),
  });

  const { data: players = [] } = useQuery<Player[]>({
    queryKey: ['players'],
    queryFn: () => playersApi.list().then(r => r.data),
  });

  // Set active item from auction state
  useEffect(() => {
    if (auction?.current_item_id) setActiveItemId(auction.current_item_id);
  }, [auction?.current_item_id]);

  const activeItem = items.find(i => i.id === activeItemId);
  const activePlayer = players.find(p => p.id === activeItem?.player_id);
  const timer = useTimer(activeItem?.status === 'active' ? activeItem.ends_at : null, auction?.bid_timer_seconds ?? 30);

  // WebSocket handler
  const handleWsEvent = useCallback((event: WsEvent) => {
    if (event.type === 'new_bid') {
      setLiveBids(prev => [event.data, ...prev].slice(0, 20));
      qc.invalidateQueries({ queryKey: ['auction-items', auctionId] });
      toast(`💰 New bid: ${fmt(event.data.amount)}`, { duration: 2000 });
    } else if (event.type === 'item_activated') {
      setActiveItemId(event.item_id);
      setLiveBids([]);
      qc.invalidateQueries({ queryKey: ['auction-items', auctionId] });
      toast('🎯 New player up for auction!');
    } else if (event.type === 'item_sold') {
      toast.success(`🏏 Sold for ${fmt(event.data.sold_price)}!`);
      qc.invalidateQueries({ queryKey: ['auction-items', auctionId] });
    } else if (event.type === 'item_unsold') {
      toast('😔 Player went unsold');
      qc.invalidateQueries({ queryKey: ['auction-items', auctionId] });
    } else if (event.type === 'auction_status') {
      qc.invalidateQueries({ queryKey: ['auction', auctionId] });
    } else if (event.type === 'auction_finalized') {
      toast.success('🏆 Auction complete! All players have been finalized.', { duration: 5000 });
      qc.invalidateQueries({ queryKey: ['auction', auctionId] });
      qc.invalidateQueries({ queryKey: ['auction-items', auctionId] });
    }
  }, [auctionId, qc]);

  useWebSocket(`/auctions/${auctionId}/ws`, handleWsEvent, !!auctionId);

  const bidMutation = useMutation({
    mutationFn: () => auctionsApi.placeBid(auctionId!, activeItemId!, { amount: +bidAmount, team_id: teamId }),
    onSuccess: () => { toast.success('Bid placed!'); setBidAmount(''); },
    onError: (e: any) => {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Bid failed');
    },
  });

  const activateMutation = useMutation({
    mutationFn: (itemId: string) => auctionsApi.activateItem(auctionId!, itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['auction-items', auctionId] }),
    onError: (e: any) => toast.error(typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : 'Failed to activate player'),
  });

  const sellMutation = useMutation({
    mutationFn: () => auctionsApi.sellItem(auctionId!, activeItemId!),
    onSuccess: () => { toast.success('Item finalised'); qc.invalidateQueries({ queryKey: ['auction-items', auctionId] }); },
    onError: (e: any) => {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Failed to sell player');
    },
  });

  const addMutation = useMutation({
    mutationFn: () => {
      const p = players.find(pl => pl.id === selectedPlayerId);
      if (!p) throw new Error('Select a player');
      return auctionsApi.addItem(auctionId!, { auction_id: auctionId!, player_id: selectedPlayerId, base_price: p.base_price });
    },
    onSuccess: () => { toast.success('Player added to queue!'); setSelectedPlayerId(''); qc.invalidateQueries({ queryKey: ['auction-items', auctionId] }); },
    onError: (e: any) => {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Failed to add player to queue');
    },
  });

  const startMutation = useMutation({
    mutationFn: () => auctionsApi.startAuction(auctionId!),
    onSuccess: () => { toast.success('Auction is now LIVE!'); qc.invalidateQueries({ queryKey: ['auction', auctionId] }); },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Failed to start auction'),
  });

  const resetMutation = useMutation({
    mutationFn: () => auctionsApi.resetAuction(auctionId!),
    onSuccess: () => {
      toast.success('All players reset to pending!');
      setActiveItemId(null);
      setLiveBids([]);
      qc.invalidateQueries({ queryKey: ['auction-items', auctionId] });
      qc.invalidateQueries({ queryKey: ['auction', auctionId] });
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Reset failed'),
  });

  const isOrganizer = hasRole('admin', 'organizer');
  const isTeamOwner = hasRole('admin', 'team_owner');
  const isLive = auction?.status === 'live';

  const finalizeMutation = useMutation({
    mutationFn: () => auctionsApi.finalizeAuction(auctionId!),
    onSuccess: () => {
      toast.success('🏆 Auction finalized!');
      qc.invalidateQueries({ queryKey: ['auction', auctionId] });
      qc.invalidateQueries({ queryKey: ['auction-items', auctionId] });
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Finalize failed'),
  });

  // Auto-finalize: if the organizer is watching and all items are done, call finalize
  useEffect(() => {
    if (!isOrganizer || !isLive || items.length === 0 || finalizeMutation.isPending) return;
    const allDone = items.every((i: AuctionItem) => i.status === 'sold' || i.status === 'unsold');
    if (allDone) {
      finalizeMutation.mutate();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, isLive]);

  const suggestedBid = activeItem
    ? Math.ceil(Math.max(activeItem.base_price, activeItem.current_bid) * 1.1 / 100000) * 100000
    : 0;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">{auction?.name ?? 'Auction Room'}</h1>
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.4rem' }}>
            <span className={isLive ? 'badge badge-red badge-live' : 'badge badge-blue'}>
              {auction?.status ?? 'loading'}
            </span>
            <span className="badge badge-gray"><Users size={11} /> {items.length} players</span>
          </div>
        </div>
        {isOrganizer && auction?.status === 'upcoming' && (
          <button className="btn btn-primary" onClick={() => startMutation.mutate()} disabled={startMutation.isPending}>
            🚀 Start Auction
          </button>
        )}
        {isOrganizer && isLive && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              className="btn btn-secondary"
              onClick={() => { if (confirm('Reset ALL players back to pending? Sold players will be reversed.')) resetMutation.mutate(); }}
              disabled={resetMutation.isPending}
            >
              🔄 {resetMutation.isPending ? 'Resetting…' : 'Reset All Players'}
            </button>
            <button
              className="btn btn-danger"
              onClick={() => { if (confirm('Finalize and close this auction? This cannot be undone.')) finalizeMutation.mutate(); }}
              disabled={finalizeMutation.isPending}
            >
              🏆 {finalizeMutation.isPending ? 'Finalizing…' : 'Finalize Auction'}
            </button>
          </div>
        )}
      </div>

      <div className="auction-room">
        {/* ── Main panel ──────────────────────────────────────────────────── */}
        <div className="auction-main">
          {/* Player spotlight */}
          <div className="player-spotlight">
            {activePlayer ? (
              <>
                <div style={{ fontSize: '4rem' }}>🏏</div>
                <div className="player-spotlight-name">{activePlayer.name}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.75rem' }}>
                  {activePlayer.country} · {activePlayer.role.replace('_', ' ')} · Base {fmt(activePlayer.base_price)}
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Current Bid</div>
                  <div className="current-bid-display">
                    {activeItem!.current_bid > 0 ? fmt(activeItem!.current_bid) : fmt(activeItem!.base_price)}
                  </div>
                  <div className="text-muted text-sm">{activeItem!.bid_count} bids</div>
                </div>

                <div className={`bid-timer ${timer <= 10 ? 'urgent' : ''}`}>{timer}s</div>

                {/* Bid input */}
                {isTeamOwner && isLive && activeItem?.status === 'active' && (
                  <div style={{ marginTop: '1.5rem' }}>
                    <div className="bid-input-area">
                      <input
                        type="number"
                        placeholder={`Min: ${fmt(suggestedBid)}`}
                        value={bidAmount}
                        onChange={e => setBidAmount(e.target.value)}
                        style={{ maxWidth: 200 }}
                        min={suggestedBid}
                        step={100000}
                      />
                      <select
                        value={teamId}
                        onChange={e => setTeamId(e.target.value)}
                        style={{ maxWidth: 200, appearance: 'auto' }}
                      >
                        <option value="">Select your team</option>
                        {myTeams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                      </select>
                      <button
                        className="btn btn-primary"
                        onClick={() => bidMutation.mutate()}
                        disabled={bidMutation.isPending || !bidAmount || !teamId}
                      >
                        <Gavel size={16} />
                        {bidMutation.isPending ? 'Placing…' : `Bid ${bidAmount ? fmt(+bidAmount) : ''}`}
                      </button>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                      {[1, 1.5, 2, 3].map(m => (
                        <button key={m} className="btn btn-secondary btn-sm"
                          onClick={() => setBidAmount(String(Math.ceil(suggestedBid * m / 100000) * 100000))}>
                          +{fmt(Math.ceil(suggestedBid * m / 100000) * 100000)}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Organizer controls */}
                {isOrganizer && isLive && (
                  <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem', justifyContent: 'center' }}>
                    <button className="btn btn-success" onClick={() => sellMutation.mutate()} disabled={sellMutation.isPending}>
                      ✅ Sell Player
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">🔨</div>
                <p>{isLive ? 'Waiting for next player…' : 'Auction not started yet'}</p>
              </div>
            )}
          </div>

          {/* Live bid log */}
          {liveBids.length > 0 && (
            <div className="card">
              <div className="card-header"><div className="card-title">Live Bid Feed</div></div>
              <div className="bid-log">
                {liveBids.map((b, i) => (
                  <div key={i} className={`bid-log-item${i === 0 ? ' winning' : ''}`}>
                    <span className="text-muted text-sm">Team {b.team_id.slice(-6)}</span>
                    <span style={{ fontWeight: 700, color: 'var(--green)' }}>{fmt(b.amount)}</span>
                    {i === 0 && <span className="badge badge-green">Leading</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Right sidebar ───────────────────────────────────────────────── */}
        <div className="auction-sidebar-panel">
          {/* Add Players (Organizer only) */}
          {isOrganizer && auction?.status !== 'completed' && (
            <div className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
              <div style={{ fontWeight: 600, marginBottom: '0.75rem' }}>Add to Auction</div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <select value={selectedPlayerId} onChange={e => setSelectedPlayerId(e.target.value)} style={{ flex: 1 }}>
                  <option value="">Select player…</option>
                  {players
                    .filter(p => p.is_available && !items.find(i => i.player_id === p.id))
                    .map(p => <option key={p.id} value={p.id}>{p.name} ({fmt(p.base_price)})</option>)
                  }
                </select>
                <button
                  className="btn btn-primary"
                  onClick={() => addMutation.mutate()}
                  disabled={!selectedPlayerId || addMutation.isPending}
                >
                  <Plus size={16} /> Add
                </button>
              </div>
            </div>
          )}

          {/* Queue */}
          <div className="card">
            <div className="card-header"><div className="card-title">Player Queue</div></div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: 400, overflowY: 'auto' }}>
              {items.length === 0 ? (
                <div className="empty-state">No players added</div>
              ) : items.map(item => {
                const p = players.find(pl => pl.id === item.player_id);
                const isActive = item.id === activeItemId;
                return (
                  <div key={item.id} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '0.6rem 0.75rem', borderRadius: 'var(--radius-sm)',
                    background: isActive ? 'rgba(59,130,246,0.1)' : 'var(--bg-elevated)',
                    border: `1px solid ${isActive ? 'rgba(59,130,246,0.4)' : 'var(--border)'}`,
                  }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{p?.name ?? 'Unknown'}</div>
                      <div className="text-muted text-sm">{fmt(item.base_price)}</div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                      <span className={
                        item.status === 'sold' ? 'badge badge-green' :
                        item.status === 'unsold' ? 'badge badge-gray' :
                        item.status === 'active' ? 'badge badge-red' : 'badge badge-blue'
                      }>{item.status}</span>
                      {isOrganizer && item.status !== 'active' && (
                        <button className="btn btn-secondary btn-sm" onClick={() => activateMutation.mutate(item.id)} disabled={activateMutation.isPending}>
                          <Gavel size={13} style={{ marginRight: 4 }} /> {item.status === 'pending' ? 'Start Bidding' : 'Restart Bidding'}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
