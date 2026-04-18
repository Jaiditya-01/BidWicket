import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { searchApi } from '../services/api';
import type { SearchResult } from '../types';

export default function SearchPage() {
  const [q, setQ] = useState('');

  const enabled = q.trim().length >= 2;
  const { data, isLoading } = useQuery({
    queryKey: ['search', q],
    queryFn: () => searchApi.search(q, 30).then(r => r.data),
    enabled,
  });

  const results: SearchResult[] = data?.results ?? [];

  const grouped = useMemo(() => {
    const map: Record<string, SearchResult[]> = {};
    for (const r of results) {
      (map[r.entity] ??= []).push(r);
    }
    return map;
  }, [results]);

  const linkFor = (r: SearchResult) => {
    if (r.entity === 'auction') return `/auctions/${r.id}`;
    if (r.entity === 'tournament') return '/tournaments';
    if (r.entity === 'team') return '/teams';
    if (r.entity === 'player') return '/players';
    if (r.entity === 'match') return '/matches';
    return '/';
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Search</h1>
          <p className="page-subtitle">Search tournaments, teams, players, auctions</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">Query</label>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <Search size={16} className="text-muted" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Type at least 2 characters…" />
          </div>
        </div>
      </div>

      {!enabled ? (
        <div className="empty-state"><div className="empty-state-icon">🔎</div><p>Start typing to search.</p></div>
      ) : isLoading ? (
        <div className="spinner" />
      ) : results.length === 0 ? (
        <div className="empty-state"><div className="empty-state-icon">😕</div><p>No results for “{q}”.</p></div>
      ) : (
        <div className="grid-2">
          {Object.entries(grouped).map(([entity, items]) => (
            <div key={entity} className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">{entity}</div>
                  <div className="card-subtitle">{items.length} results</div>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                {items.map((r) => (
                  <Link
                    key={r.id}
                    to={linkFor(r)}
                    className="card"
                    style={{
                      textDecoration: 'none',
                      padding: '0.6rem 0',
                      borderBottom: '1px solid var(--border)',
                      background: 'transparent',
                      border: 'none',
                    }}
                  >
                    <div style={{ fontWeight: 700 }}>{r.title}</div>
                    {r.subtitle && <div className="text-muted text-sm">{r.subtitle}</div>}
                    <div className="text-muted text-sm">ID: {r.id}</div>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
