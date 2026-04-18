import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Check, MailOpen, Bell } from 'lucide-react';
import { notificationsApi } from '../services/api';
import type { Notification } from '../types';

export default function NotificationsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationsApi.list({ limit: 100, skip: 0 }).then(r => r.data),
  });

  const items: Notification[] = data?.items ?? [];

  const markAll = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      toast.success('All notifications marked as read');
      qc.invalidateQueries({ queryKey: ['notifications'] });
      qc.invalidateQueries({ queryKey: ['notifications_unread_count'] });
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Failed'),
  });

  const markRead = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] });
      qc.invalidateQueries({ queryKey: ['notifications_unread_count'] });
    },
  });

  const unreadCount = items.filter(n => !n.is_read).length;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Notifications</h1>
          <p className="page-subtitle">{unreadCount} unread</p>
        </div>
        <button className="btn btn-secondary" onClick={() => markAll.mutate()} disabled={markAll.isPending}>
          <MailOpen size={16} /> Mark all read
        </button>
      </div>

      {isLoading ? (
        <div className="spinner" />
      ) : items.length === 0 ? (
        <div className="empty-state"><div className="empty-state-icon">🔔</div><p>No notifications yet.</p></div>
      ) : (
        <div className="card">
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {items.map((n) => (
              <div
                key={n.id}
                style={{
                  padding: '0.9rem 0',
                  borderBottom: '1px solid var(--border)',
                  opacity: n.is_read ? 0.75 : 1,
                  display: 'flex',
                  gap: '0.75rem',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                  <div style={{ marginTop: '0.15rem' }}><Bell size={16} /></div>
                  <div>
                    <div style={{ fontWeight: 700 }}>{n.title}</div>
                    <div className="text-muted text-sm" style={{ marginTop: '0.15rem' }}>{n.message}</div>
                    <div className="text-muted text-sm" style={{ marginTop: '0.35rem' }}>{new Date(n.created_at).toLocaleString()}</div>
                  </div>
                </div>
                {!n.is_read && (
                  <button
                    className="btn btn-success btn-sm"
                    onClick={() => markRead.mutate(n.id)}
                    disabled={markRead.isPending}
                  >
                    <Check size={13} /> Read
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
