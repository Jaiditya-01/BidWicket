import { useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import { matchesApi, teamsApi, playersApi } from '../services/api';
import type { Match, Team, Player, WsEvent, Commentary } from '../types';
import { Radio, Repeat, User, Sparkles, Volume2, VolumeX, ArrowLeftRight } from 'lucide-react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAuth } from '../context/AuthContext';
import { PageSkeleton } from '../components/Skeleton';
import toast from 'react-hot-toast';

function formatOvers(overs: number) {
  const o = Math.floor(overs);
  const b = Math.round((overs - o) * 10);
  return `${o}.${b}`;
}

// Roles eligible to bat / bowl (Bug 1)
const BATTER_ROLES = new Set(['batsman', 'all_rounder', 'wicket_keeper']);
const BOWLER_ROLES = new Set(['bowler', 'all_rounder']);

export default function LiveMatchPage() {
  const { id: matchId } = useParams<{ id: string }>();
  const actualId = matchId || window.location.pathname.split('/').pop()!;
  const qc = useQueryClient();
  const { hasRole } = useAuth();

  // ── UI state ────────────────────────────────────────────────────────────────
  const [liveWicket, setLiveWicket] = useState<string | null>(null);
  const [isAudioEnabled, setIsAudioEnabled] = useState(false);

  // Commentary form state
  const [ballDesc, setBallDesc] = useState('');
  const [runs, setRuns] = useState(0);
  const [isWicket, setIsWicket] = useState(false);

  // Bug 3: ball/over tracking
  const [currentOver, setCurrentOver] = useState(0);   // integer over index
  const [ballsInOver, setBallsInOver] = useState(0);   // 0–5 within over

  // Players on field
  const [batterId, setBatterId] = useState('');         // on-strike batter
  const [nonStrikerId, setNonStrikerId] = useState('');
  const [bowlerId, setBowlerId] = useState('');
  const [quickRuns, setQuickRuns] = useState(1);        // custom run input

  // Derived: bowler locked once an over has started (at least 1 ball bowled)
  const bowlerLocked = !!bowlerId && ballsInOver > 0;
  // Float representation sent to backend: e.g. over 2, ball 3 → 2.3
  const floatOver = currentOver + (ballsInOver > 0 ? ballsInOver / 10 : 0);

  // ── Queries (Bug 2: refetchInterval for auto-refresh) ──────────────────────
  const { data: match, isLoading } = useQuery<Match>({
    queryKey: ['match', actualId],
    queryFn: () => matchesApi.get(actualId).then(r => r.data),
    refetchInterval: 5000,   // Bug 2: poll every 5 s
  });

  const { data: team1 } = useQuery<Team>({
    queryKey: ['team', match?.team1_id],
    queryFn: () => teamsApi.get(match!.team1_id).then(r => r.data),
    enabled: !!match?.team1_id,
    refetchInterval: 10000,
  });

  const { data: team2 } = useQuery<Team>({
    queryKey: ['team', match?.team2_id],
    queryFn: () => teamsApi.get(match!.team2_id).then(r => r.data),
    enabled: !!match?.team2_id,
    refetchInterval: 10000,
  });

  const { data: team1Roster = [] } = useQuery<Player[]>({
    queryKey: ['players', { team_id: match?.team1_id }],
    queryFn: () => playersApi.list({ limit: 100, team_id: match!.team1_id }).then(r => r.data),
    enabled: !!match?.team1_id,
  });

  const { data: team2Roster = [] } = useQuery<Player[]>({
    queryKey: ['players', { team_id: match?.team2_id }],
    queryFn: () => playersApi.list({ limit: 100, team_id: match!.team2_id }).then(r => r.data),
    enabled: !!match?.team2_id,
  });

  const { data: allPlayers = [] } = useQuery<Player[]>({
    queryKey: ['players', 'all'],
    queryFn: () => playersApi.list({ limit: 100 }).then(r => r.data),
  });

  // ── Helpers ─────────────────────────────────────────────────────────────────
  const speakText = useCallback((text: string) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    let voice = voices.find(v => v.lang.includes('hi') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Premium')));
    if (!voice) voice = voices.find(v => v.lang.includes('hi'));
    if (!voice && voices.length > 0) voice = voices[0];
    if (voice) utterance.voice = voice;
    utterance.lang = 'hi-IN';
    utterance.rate = 1.05;
    utterance.pitch = 1.1;
    window.speechSynthesis.speak(utterance);
  }, []);

  const handleWs = useCallback((ev: WsEvent) => {
    if (ev.type === 'score_update') {
      qc.setQueryData(['match', actualId], ev.data);
    } else if (ev.type === 'commentary_update') {
      qc.setQueryData<Match>(['match', actualId], (old) => {
        if (!old) return old;
        return { ...old, commentary: [...old.commentary, ev.data as Commentary] };
      });
      if (isAudioEnabled) speakText((ev.data as Commentary).ball_description);
    } else if (ev.type === 'wicket_update') {
      toast.error(`WICKET! Over ${ev.data.over}: ${ev.data.description}`);
      setLiveWicket(`OUT! ${ev.data.description}`);
      setTimeout(() => setLiveWicket(null), 5000);
    }
  }, [actualId, qc, isAudioEnabled, speakText]);

  useWebSocket(`/matches/${actualId}/ws`, handleWs, !!match);

  // ── Mutations (ALL hooks must come before ANY early return) ──────────────────

  type BallOverride = { runs?: number; wicket?: boolean; desc?: string };

  const commentaryMutation = useMutation({
    mutationFn: (override?: BallOverride) => matchesApi.addCommentary(actualId, {
      ball_description: override?.desc ?? ballDesc,
      runs_scored:      override?.runs   ?? runs,
      wicket:           override?.wicket ?? isWicket,
      over: floatOver,
      batter_id: batterId || undefined,
      bowler_id: bowlerId || undefined,
    }),
    onSuccess: () => {
      toast.success('Commentary added!');
      const wasWicket = isWicket;

      // Reset per-ball fields
      setBallDesc('');
      setRuns(0);
      setIsWicket(false);
      qc.invalidateQueries({ queryKey: ['match', actualId] });

      // Bug 3: advance ball counter; lock/unlock bowler; swap strike at over end
      const newBalls = ballsInOver + 1;
      if (newBalls >= 6) {
        // Over complete
        setBallsInOver(0);
        setCurrentOver(o => o + 1);
        setBowlerId('');          // must pick new bowler
        // Traditional cricket: strike swaps at end of over
        const prevStriker = batterId;
        setBatterId(nonStrikerId);
        setNonStrikerId(prevStriker);
        toast('⚾ Over complete — select new bowler', { icon: '🏏' });
      } else {
        setBallsInOver(newBalls);
      }

      // Bug 3 / Bug 4: clear out-batsman from strike
      if (wasWicket) {
        setBatterId('');
        toast.error('🏏 Wicket! Select new batsman');
      }
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Failed to add commentary'),
  });

  const switchInningsMutation = useMutation({
    mutationFn: () => matchesApi.update(actualId, { current_innings: match!.current_innings === 1 ? 2 : 1 }),
    onSuccess: () => {
      // Reset all per-over tracking on innings switch
      setBallsInOver(0);
      setCurrentOver(0);
      setBatterId('');
      setNonStrikerId('');
      setBowlerId('');
      qc.invalidateQueries({ queryKey: ['match', actualId] });
    },
  });

  // AI commentary mutation — defined here so hooks order is deterministic
  const aiMutation = useMutation({
    mutationFn: () => {
      const getPlayerName = (id: string) =>
        [...team1Roster, ...team2Roster, ...allPlayers].find(p => p.id === id)?.name || id;
      // Determine batting/bowling side from current match state
      const t1Batting = match
        ? (match.current_innings === 1
          ? ((match.toss_decision === 'bat' && match.toss_winner_id === match.team1_id) ||
             (match.toss_decision === 'bowl' && match.toss_winner_id === match.team2_id) ||
             !match.toss_decision)
          : ((match.innings1?.batting_team_id || match.innings1?.team_id) === match.team2_id))
        : false;
      return matchesApi.generateAiCommentary(actualId, {
        batting_team: t1Batting ? team1?.name : team2?.name,
        bowling_team: t1Batting ? team2?.name : team1?.name,
        batter_name: getPlayerName(batterId),
        bowler_name: getPlayerName(bowlerId),
        runs,
        is_wicket: isWicket,
        over: floatOver,
      });
    },
    onSuccess: (res) => {
      setBallDesc(res.data.commentary);
      toast.success('AI Commentary Generated!');
      speakText(res.data.hindi_commentary || res.data.commentary);
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Failed to generate AI commentary'),
  });

  const isOrganizer = hasRole('admin', 'organizer');

  // ── Early returns (after ALL hooks) ─────────────────────────────────────────
  if (isLoading) return <PageSkeleton />;
  if (!match) return <div className="empty-state"><div className="empty-state-icon">🏏</div><p>Match not found</p></div>;

  // ── Derived data (safe to compute after guards) ──────────────────────────────
  const isLive = match.status === 'live';

  const chartData = match.commentary.map((c, i) => {
    const totalRunsBefore = match.commentary.slice(0, i + 1).reduce((sum, item) => sum + item.runs_scored, 0);
    return { over: c.over, runs: totalRunsBefore, isWicket: c.wicket ? totalRunsBefore : null };
  });

  const i1 = match.innings1;
  const i2 = match.innings2;
  const currentInning = match.current_innings === 1 ? i1 : i2;

  const getPlayerName = (id: string) => {
    const p = [...team1Roster, ...team2Roster, ...allPlayers].find(player => player.id === id);
    return p ? p.name : id;
  };

  const isTeam1Batting = (match.current_innings === 1)
    ? (match.toss_decision === 'bat' && match.toss_winner_id === match.team1_id) ||
      (match.toss_decision === 'bowl' && match.toss_winner_id === match.team2_id) ||
      !match.toss_decision
    : ((match.innings1?.batting_team_id || match.innings1?.team_id) === match.team2_id);

  const battingRoster = isTeam1Batting ? team1Roster : team2Roster;
  const bowlingRoster = isTeam1Batting ? team2Roster : team1Roster;
  const battingTeamName = isTeam1Batting ? team1?.name : team2?.name;

  const rawBattingRoster = battingRoster;
  const rawBowlingRoster = bowlingRoster;

  // Bug 4: collect already-out player IDs from this innings
  const outPlayerIds = new Set(
    (currentInning?.batters ?? []).filter(b => b.is_out).map(b => b.player_id)
  );

  // Bug 1 + Bug 4: role-filter AND exclude out batsmen
  const filteredBatters = rawBattingRoster.filter(
    p => BATTER_ROLES.has(p.role) && !outPlayerIds.has(p.id)
  );
  // Fallback: if role filter empties the list (e.g. no roles assigned), just exclude out players
  const safeBatters = filteredBatters.length > 0
    ? filteredBatters
    : rawBattingRoster.filter(p => !outPlayerIds.has(p.id));

  // Bug 1: role-filter bowlers
  const filteredBowlers = rawBowlingRoster.filter(p => BOWLER_ROLES.has(p.role));
  const safeBowlers = filteredBowlers.length > 0 ? filteredBowlers : rawBowlingRoster;

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="fade-in">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="page-header" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 className="page-title" style={{ textAlign: 'left', margin: 0 }}>
          {match.venue}
          <span style={{ fontSize: '1rem', color: 'var(--text-secondary)', marginLeft: '1rem', fontWeight: 400 }}>
            {match.stage} • {new Date(match.match_date).toLocaleDateString()}
          </span>
        </h1>
        <button
          onClick={() => {
            if (!isAudioEnabled) speakText('लाइव ऑडियो कमेंट्री शुरू');
            setIsAudioEnabled(!isAudioEnabled);
          }}
          className={`btn ${isAudioEnabled ? 'btn-primary' : 'btn-outline'}`}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          {isAudioEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          {isAudioEnabled ? 'Voice Commentary: ON' : 'Voice Commentary: OFF'}
        </button>
      </div>

      {/* ── Scoreboard ─────────────────────────────────────────────────────── */}
      <div style={{ marginBottom: '1.5rem', textAlign: 'center' }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <span className={isLive ? 'badge badge-red badge-live' : 'badge badge-blue'}>
              {isLive && <Radio size={12} />} {match.status.toUpperCase()}
            </span>
            <span className="badge badge-accent">{match.stage.toUpperCase()}</span>
            {isLive && (currentInning?.batting_team_id || currentInning?.team_id) && (
              <span className="badge badge-gray">{battingTeamName} Batting (Innings {match.current_innings})</span>
            )}
            {isOrganizer && isLive && (
              <button className="btn btn-secondary btn-sm" onClick={() => { if (confirm('Switch Innings?')) switchInningsMutation.mutate(); }}>
                <Repeat size={12} /> Switch Innings
              </button>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '2rem' }}>
            <div style={{ textAlign: 'right', flex: 1 }}>
              <div className="fw-700" style={{ fontSize: '1.5rem' }}>{team1?.name || match.team1_id}</div>
              <div className="text-muted">{team1?.home_ground}</div>
            </div>
            <div style={{ padding: '1rem 2rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', minWidth: 200 }}>
              <div className="text-accent fw-700" style={{ fontSize: '2rem', lineHeight: 1.2 }}>
                {i2 ? `${i2.runs}/${i2.wickets}` : i1 ? `${i1.runs}/${i1.wickets}` : '0/0'}
              </div>
              <div className="text-muted text-sm">
                Over {i2 ? formatOvers(i2.overs) : i1 ? formatOvers(i1.overs) : '0.0'}
              </div>
              {match.current_innings === 2 && i1 && (
                <div className="text-muted text-sm" style={{ marginTop: '0.4rem', fontWeight: 700, color: 'var(--text)' }}>
                  Target: {i1.runs + 1}
                </div>
              )}
            </div>
            <div style={{ textAlign: 'left', flex: 1 }}>
              <div className="fw-700" style={{ fontSize: '1.5rem' }}>{team2?.name || match.team2_id}</div>
              <div className="text-muted">{team2?.home_ground}</div>
            </div>
          </div>

          {(match.result_description || match.toss_decision) && (
            <p style={{ marginTop: '1.5rem', color: match.result_description ? 'var(--green)' : 'var(--text-secondary)', fontWeight: 600 }}>
              {match.result_description || `${match.toss_winner_id === match.team1_id ? team1?.name : team2?.name} won the toss and elected to ${match.toss_decision}`}
            </p>
          )}
          {liveWicket && (
            <div className="slide-in" style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--red)', borderRadius: 'var(--radius-sm)', color: 'var(--red)', fontWeight: 'bold' }}>
              {liveWicket}
            </div>
          )}
        </div>
      </div>

      <div className="grid-2">
        {/* ── Run Rate Chart ────────────────────────────────────────────────── */}
        <div className="card">
          <div className="card-header"><div className="card-title">Run Rate Progression</div></div>
          <div style={{ height: 300 }}>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorRuns" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="over" stroke="var(--text-secondary)" tickFormatter={v => `Ov ${v}`} />
                  <YAxis stroke="var(--text-secondary)" />
                  <RechartsTooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '8px' }} />
                  <Area type="monotone" dataKey="runs" stroke="var(--accent)" fillOpacity={1} fill="url(#colorRuns)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state">Not enough data to plot</div>
            )}
          </div>
        </div>

        {/* ── Scorecard ─────────────────────────────────────────────────────── */}
        {currentInning && (
          <div className="card" style={{ gridColumn: '1 / -1' }}>
            <div className="card-header"><div className="card-title">Scorecard - Innings {match.current_innings}</div></div>
            <div className="grid-2" style={{ gap: '2rem' }}>
              <div>
                <h4 style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>Batters</h4>
                <table style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
                  <thead><tr><th>Batter</th><th>R</th><th>B</th><th>4s</th><th>6s</th><th>SR</th></tr></thead>
                  <tbody>
                    {currentInning.batters.map((b, i) => (
                      <tr key={i} style={{ opacity: b.is_out ? 0.6 : 1 }}>
                        <td style={{ fontWeight: b.is_out ? 400 : 700 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <User size={14} />
                            {getPlayerName(b.player_id)}
                            {b.is_out && <span className="text-red text-sm">(Out)</span>}
                            {b.player_id === batterId && !b.is_out && <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>★ Strike</span>}
                            {b.player_id === nonStrikerId && !b.is_out && <span className="badge badge-blue" style={{ fontSize: '0.65rem' }}>Non-Strike</span>}
                          </div>
                        </td>
                        <td className="fw-700">{b.runs}</td>
                        <td>{b.balls_faced}</td>
                        <td>{b.fours}</td>
                        <td>{b.sixes}</td>
                        <td className="text-sm">{b.balls_faced > 0 ? ((b.runs / b.balls_faced) * 100).toFixed(1) : '0.0'}</td>
                      </tr>
                    ))}
                    {currentInning.batters.length === 0 && <tr><td colSpan={6} className="text-center text-muted">No batters yet</td></tr>}
                  </tbody>
                </table>
              </div>
              <div>
                <h4 style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>Bowlers</h4>
                <table style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
                  <thead><tr><th>Bowler</th><th>O</th><th>M</th><th>R</th><th>W</th><th>Econ</th></tr></thead>
                  <tbody>
                    {currentInning.bowlers.map((b, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 600 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <User size={14} />
                            {getPlayerName(b.player_id)}
                            {b.player_id === bowlerId && <span className="badge badge-accent" style={{ fontSize: '0.65rem' }}>Bowling</span>}
                          </div>
                        </td>
                        <td>{formatOvers(b.overs)}</td>
                        <td>{b.maidens}</td>
                        <td>{b.runs_conceded}</td>
                        <td className="fw-700 text-accent">{b.wickets}</td>
                        <td className="text-sm">{b.overs > 0 ? (b.runs_conceded / b.overs).toFixed(1) : '0.0'}</td>
                      </tr>
                    ))}
                    {currentInning.bowlers.length === 0 && <tr><td colSpan={6} className="text-center text-muted">No bowlers yet</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── Commentary + form ─────────────────────────────────────────────── */}
        <div className="card">
          <div className="card-header"><div className="card-title">Live Commentary</div></div>
          <div style={{ maxHeight: 300, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingRight: '0.5rem' }}>
            {match.commentary.length === 0 ? (
              <div className="empty-state">No commentary available</div>
            ) : match.commentary.slice().reverse().map((c, i) => (
              <div key={i} style={{
                display: 'flex', gap: '1rem', padding: '0.75rem',
                background: c.wicket ? 'rgba(239, 68, 68, 0.05)' : c.runs_scored >= 4 ? 'rgba(16, 185, 129, 0.05)' : 'var(--bg-elevated)',
                borderRadius: 'var(--radius-sm)',
                borderLeft: `3px solid ${c.wicket ? 'var(--red)' : c.runs_scored >= 4 ? 'var(--green)' : 'var(--border)'}`,
              }}>
                <div style={{ fontWeight: 700, color: 'var(--text-secondary)', minWidth: 40 }}>{formatOvers(c.over)}</div>
                <div style={{ flex: 1 }}>{c.ball_description}</div>
                {c.wicket && <div className="badge badge-red">W</div>}
                {!c.wicket && c.runs_scored > 0 && <div className="badge badge-blue">{c.runs_scored}</div>}
              </div>
            ))}
          </div>

          {/* ── Commentary input form (organizer only) ─────────────────────── */}
          {isLive && isOrganizer && (
            <div className="card" style={{ marginTop: '1.5rem' }}>
              {/* Bug 3: over/ball status header */}
              <div className="card-header">
                <div className="card-title">📝 Add Ball Commentary</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className="badge badge-blue">Over {currentOver}</span>
                  <span className="badge badge-gray">Ball {ballsInOver}/6</span>
                  {bowlerLocked && (
                    <span className="badge badge-accent" style={{ fontSize: '0.7rem' }}>🔒 Bowler Locked</span>
                  )}
                </div>
              </div>

              <form
                onSubmit={e => { e.preventDefault(); if (!ballDesc.trim()) return; commentaryMutation.mutate(undefined); }}
                style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}
              >
                {/* ── Quick Score Controls ─────────────────────────────── */}
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', padding: '0.75rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', flexShrink: 0 }}>⚡ Quick:</span>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={!batterId || !bowlerId || commentaryMutation.isPending}
                    onClick={() => commentaryMutation.mutate({ runs: 6, wicket: false, desc: `SIX! 🏏 ${getPlayerName(batterId)} hits it out of the park!` })}
                  >🏏 6</button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={!batterId || !bowlerId || commentaryMutation.isPending}
                    onClick={() => commentaryMutation.mutate({ runs: 4, wicket: false, desc: `FOUR! 🏏 ${getPlayerName(batterId)} finds the boundary!` })}
                  >🏏 4</button>
                  <button
                    type="button"
                    className="btn btn-sm"
                    style={{ background: 'var(--red)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '0.35rem 0.75rem', fontWeight: 600, cursor: 'pointer', opacity: (!batterId || !bowlerId || commentaryMutation.isPending) ? 0.5 : 1 }}
                    disabled={!batterId || !bowlerId || commentaryMutation.isPending}
                    onClick={() => commentaryMutation.mutate({ runs: 0, wicket: true, desc: `WICKET! 🏏 ${getPlayerName(batterId)} is OUT!` })}
                  >🚨 Out</button>
                  <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', marginLeft: 'auto' }}>
                    <input
                      id="quick-runs-input"
                      type="number"
                      min={0}
                      max={7}
                      step={1}
                      value={quickRuns}
                      onChange={e => setQuickRuns(Math.max(0, parseInt(e.target.value) || 0))}
                      style={{ width: 64, textAlign: 'center' }}
                      placeholder="Runs"
                    />
                    <button
                      type="button"
                      className="btn btn-outline btn-sm"
                      disabled={!batterId || !bowlerId || commentaryMutation.isPending}
                      onClick={() => {
                        if (!batterId || !bowlerId) return toast.error('Select Batter and Bowler first');
                        const d = quickRuns === 0
                          ? `Dot ball. ${getPlayerName(bowlerId)} beats the bat.`
                          : quickRuns === 1
                          ? `1 run. ${getPlayerName(batterId)} works it to the leg side.`
                          : `${quickRuns} runs off the bat!`;
                        commentaryMutation.mutate({ runs: quickRuns, wicket: false, desc: d });
                        setQuickRuns(1);
                      }}
                    >▶ Submit Run</button>
                  </div>
                </div>
                {/* ── Batters (striker + non-striker) + Swap Strike ──────── */}
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                  <div className="form-group" style={{ flex: 1, minWidth: 140, marginBottom: 0 }}>
                    <label className="form-label">
                      🏏 Striker
                      {batterId && <span className="badge badge-green" style={{ fontSize: '0.65rem', marginLeft: 4 }}>On Strike</span>}
                    </label>
                    {/* Bug 1: role-filtered; Bug 4: out players excluded */}
                    <select value={batterId} onChange={e => setBatterId(e.target.value)}>
                      <option value="">Select Striker</option>
                      {safeBatters
                        .filter(p => p.id !== nonStrikerId)
                        .map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                  </div>

                  {/* Bug 3: Swap Strike button */}
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ marginBottom: '0.1rem', whiteSpace: 'nowrap', flexShrink: 0 }}
                    disabled={!batterId && !nonStrikerId}
                    title="Swap striker and non-striker"
                    onClick={() => {
                      const prev = batterId;
                      setBatterId(nonStrikerId);
                      setNonStrikerId(prev);
                    }}
                  >
                    <ArrowLeftRight size={14} /> Swap Strike
                  </button>

                  <div className="form-group" style={{ flex: 1, minWidth: 140, marginBottom: 0 }}>
                    <label className="form-label">Non-Striker</label>
                    {/* Bug 1 + Bug 4 applied to non-striker too */}
                    <select value={nonStrikerId} onChange={e => setNonStrikerId(e.target.value)}>
                      <option value="">Select Non-Striker</option>
                      {safeBatters
                        .filter(p => p.id !== batterId)
                        .map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                  </div>
                </div>

                {/* ── Bowler (Bug 3: locked mid-over) ──────────────────── */}
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">
                    ⚾ Bowler
                    {bowlerLocked
                      ? <span className="text-muted text-sm" style={{ marginLeft: 6 }}>🔒 Locked until over ends ({6 - ballsInOver} ball{6 - ballsInOver !== 1 ? 's' : ''} left)</span>
                      : <span className="text-muted text-sm" style={{ marginLeft: 6 }}>Select bowler for this over</span>
                    }
                  </label>
                  {/* Bug 1: role-filtered; Bug 3: disabled mid-over */}
                  <select
                    value={bowlerId}
                    onChange={e => setBowlerId(e.target.value)}
                    disabled={bowlerLocked}
                    style={{ opacity: bowlerLocked ? 0.65 : 1, cursor: bowlerLocked ? 'not-allowed' : 'pointer' }}
                  >
                    <option value="">Select Bowler</option>
                    {safeBowlers.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>

                {/* ── Ball description ──────────────────────────────────── */}
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Ball Description</span>
                    <button
                      type="button"
                      onClick={() => {
                        if (!batterId || !bowlerId) return toast.error('Select Batter and Bowler first');
                        aiMutation.mutate();
                      }}
                      disabled={aiMutation.isPending}
                      style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}
                    >
                      <Sparkles size={14} /> {aiMutation.isPending ? 'Generating...' : 'Auto-Generate AI'}
                    </button>
                  </label>
                  <input
                    value={ballDesc}
                    onChange={e => setBallDesc(e.target.value)}
                    placeholder="e.g. Six! Dhoni hits it over mid-wicket!"
                    required
                  />
                </div>

                {/* ── Runs / Over display / Wicket ──────────────────────── */}
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                  <div className="form-group" style={{ flex: 1, minWidth: 80, marginBottom: 0 }}>
                    <label className="form-label">Runs</label>
                    <input type="number" min={0} max={6} value={runs} onChange={e => setRuns(+e.target.value)} />
                  </div>
                  {/* Bug 3: over is auto-managed — display only */}
                  <div className="form-group" style={{ flex: 1, minWidth: 100, marginBottom: 0 }}>
                    <label className="form-label">Over (auto)</label>
                    <input
                      type="text"
                      value={formatOvers(floatOver)}
                      readOnly
                      style={{ opacity: 0.65, cursor: 'not-allowed', background: 'var(--bg-elevated)' }}
                    />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem', paddingBottom: '0.1rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', color: isWicket ? 'var(--red)' : 'var(--text-secondary)', fontWeight: 600 }}>
                      <input type="checkbox" checked={isWicket} onChange={e => setIsWicket(e.target.checked)} />
                      Wicket!
                    </label>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button type="submit" className="btn btn-primary" disabled={commentaryMutation.isPending || !batterId || !bowlerId}>
                    {commentaryMutation.isPending ? 'Adding…' : '➕ Add Ball'}
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
