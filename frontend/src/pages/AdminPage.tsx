import { useQuery } from '@tanstack/react-query';
import { Download, Shield } from 'lucide-react';
import { adminApi, usersApi } from '../services/api';
import type { AdminOverview, User } from '../types';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="stat-card">
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

function MiniBars({ data }: { data: Array<{ label: string; value: number }> }) {
  const max = Math.max(1, ...data.map(d => d.value));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
      {data.map((d) => (
        <div key={d.label}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
            <div style={{ fontWeight: 700 }}>{d.label}</div>
            <div className="text-muted">{d.value}</div>
          </div>
          <div style={{ height: 8, background: 'var(--border)', borderRadius: 999 }}>
            <div
              style={{
                height: 8,
                width: `${Math.round((d.value / max) * 100)}%`,
                background: 'var(--accent)',
                borderRadius: 999,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AdminPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin_overview'],
    queryFn: () => adminApi.overview().then(r => r.data),
  });

  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['admin_users'],
    queryFn: () => usersApi.list().then(r => r.data),
  });

  const queryClient = useQueryClient();
  const roleMutation = useMutation({
    mutationFn: ({ id, roles }: { id: string, roles: string[] }) => usersApi.updateRoles(id, roles),
    onSuccess: () => {
      toast.success('Roles updated');
      queryClient.invalidateQueries({ queryKey: ['admin_users'] });
    },
    onError: () => toast.error('Failed to update roles')
  });

  const ov: AdminOverview | undefined = data;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Admin Dashboard</h1>
          <p className="page-subtitle">System overview and exports</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <Shield size={18} />
        </div>
      </div>

      {isLoading ? (
        <div className="spinner" />
      ) : !ov ? (
        <div className="empty-state"><div className="empty-state-icon">🛡️</div><p>No data.</p></div>
      ) : (
        <>
          <div className="grid-4" style={{ marginBottom: '1rem' }}>
            <Stat label="Users" value={ov.users} />
            <Stat label="Tournaments" value={ov.tournaments} />
            <Stat label="Teams" value={ov.teams} />
            <Stat label="Players" value={ov.players} />
          </div>
          <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
            <Stat label="Matches" value={ov.matches} />
            <Stat label="Auctions" value={ov.auctions} />
            <Stat label="Auction Items" value={ov.auction_items} />
            <Stat label="Bids" value={ov.bids} />
          </div>

          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Exports</div>
                <div className="card-subtitle">Download CSV exports</div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <a className="btn btn-secondary" href={adminApi.exportUsersCsvUrl()} target="_blank" rel="noreferrer"><Download size={16} /> Users CSV</a>
              <a className="btn btn-secondary" href={adminApi.exportBidsCsvUrl()} target="_blank" rel="noreferrer"><Download size={16} /> Bids CSV</a>
              <a className="btn btn-secondary" href={adminApi.exportTournamentsCsvUrl()} target="_blank" rel="noreferrer"><Download size={16} /> Tournaments CSV</a>
              <a className="btn btn-secondary" href={adminApi.exportPlayersCsvUrl()} target="_blank" rel="noreferrer"><Download size={16} /> Players CSV</a>
              <a className="btn btn-secondary" href={adminApi.exportMatchesCsvUrl()} target="_blank" rel="noreferrer"><Download size={16} /> Matches CSV</a>
            </div>
          </div>

          <div className="card" style={{ marginTop: '1rem' }}>
            <div className="card-header">
              <div>
                <div className="card-title">Activity snapshot</div>
                <div className="card-subtitle">Relative volumes</div>
              </div>
            </div>
            <MiniBars
              data={[
                { label: 'Users', value: ov.users },
                { label: 'Tournaments', value: ov.tournaments },
                { label: 'Teams', value: ov.teams },
                { label: 'Players', value: ov.players },
                { label: 'Matches', value: ov.matches },
                { label: 'Auctions', value: ov.auctions },
                { label: 'Bids', value: ov.bids },
              ]}
            />
          </div>

          <div className="card" style={{ marginTop: '1.5rem' }}>
            <div className="card-header">
              <div className="card-title">User Role Management</div>
            </div>
            {usersLoading ? (
               <div className="spinner" />
            ) : (
               <div className="table-wrap">
                 <table>
                   <thead>
                     <tr>
                       <th>User</th>
                       <th>Email</th>
                       <th>Current Roles</th>
                       <th>Actions</th>
                     </tr>
                   </thead>
                   <tbody>
                     {(usersData || []).map((u: User) => (
                       <tr key={u.id}>
                         <td><div className="fw-700">{u.full_name}</div></td>
                         <td>{u.email}</td>
                         <td>
                           <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                             {u.roles.map(r => <span key={r} className="badge badge-blue">{r}</span>)}
                           </div>
                         </td>
                         <td>
                           {!u.roles.includes('admin') && (
                              <button 
                                className="btn btn-secondary btn-sm" 
                                onClick={() => roleMutation.mutate({ id: u.id, roles: ['admin', 'organizer', 'team_owner', 'viewer'] })}
                                disabled={roleMutation.isPending}
                              >
                                Make Admin
                              </button>
                           )}
                           {u.roles.includes('admin') && (
                              <button 
                                className="btn btn-danger btn-sm" 
                                onClick={() => roleMutation.mutate({ id: u.id, roles: ['viewer'] })}
                                disabled={roleMutation.isPending}
                              >
                                Revoke Admin
                              </button>
                           )}
                         </td>
                       </tr>
                     ))}
                   </tbody>
                 </table>
               </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
