import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersApi } from '../services/api';
import type { User } from '../types';
import { User as UserIcon, Save, Key, Mail, Clock, ShieldCheck, Camera } from 'lucide-react';
import toast from 'react-hot-toast';
import { PageSkeleton } from '../components/Skeleton';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function MyProfilePage() {
  const { user: authUser } = useAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();

  const { data: user, isLoading } = useQuery<User>({
    queryKey: ['me'],
    queryFn: () => usersApi.me().then(r => r.data),
    enabled: !!authUser,
  });

  const [formData, setFormData] = useState({ full_name: '', bio: '', photo_url: '' });

  useEffect(() => {
    if (user) {
      setFormData({
        full_name: user.full_name,
        bio: (user as any).bio || '',
        photo_url: (user as any).photo_url || ''
      });
    }
  }, [user]);

  const updateMutation = useMutation({
    mutationFn: () => usersApi.updateMe(formData),
    onSuccess: (res) => {
      qc.setQueryData(['me'], res.data);
      toast.success('Profile updated successfully');
    },
    onError: () => toast.error('Failed to update profile')
  });

  if (isLoading) return <PageSkeleton />;
  if (!user) return <div className="empty-state">Unable to load profile data</div>;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">My Profile</h1>
          <div className="page-subtitle">Manage your personal information and security settings.</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><div className="card-title">Personal Information</div></div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ 
                width: 80, height: 80, borderRadius: '50%', background: 'var(--bg-elevated)', 
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2.5rem',
                border: '2px solid var(--border)', overflow: 'hidden', position: 'relative',
                flexShrink: 0
              }}>
                {formData.photo_url ? (
                  <img src={formData.photo_url} alt="Profile" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  <UserIcon size={40} color="var(--text-muted)" />
                )}
              </div>
              <div style={{ flex: 1 }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Photo URL</label>
                  <div className="flex gap-1" style={{ width: '100%' }}>
                    <div style={{ position: 'relative', flex: 1 }}>
                      <Camera size={16} style={{ position: 'absolute', left: 10, top: 12, color: 'var(--text-muted)' }} />
                      <input 
                        type="url" 
                        value={formData.photo_url} 
                        onChange={e => setFormData({ ...formData, photo_url: e.target.value })} 
                        placeholder="https://example.com/photo.jpg" 
                        style={{ paddingLeft: '2.2rem' }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input 
                value={formData.full_name} 
                onChange={e => setFormData({ ...formData, full_name: e.target.value })} 
                placeholder="John Doe" 
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Bio</label>
              <textarea 
                value={formData.bio} 
                onChange={e => setFormData({ ...formData, bio: e.target.value })} 
                placeholder="Tell us a little bit about yourself..."
                rows={3}
                style={{ resize: 'vertical' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
              <button 
                className="btn btn-primary" 
                onClick={() => updateMutation.mutate()} 
                disabled={updateMutation.isPending}
              >
                <Save size={16} /> 
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="card">
            <div className="card-header"><div className="card-title">Account Details</div></div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ width: 32, height: 32, borderRadius: 'var(--radius-sm)', background: 'rgba(59,130,246,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Mail size={16} color="var(--accent-light)" />
                </div>
                <div>
                  <div className="text-muted text-sm">Email Address</div>
                  <div className="fw-700">{user.email}</div>
                </div>
                {user.is_verified && (
                  <span className="badge badge-green" style={{ marginLeft: 'auto' }}><ShieldCheck size={12} /> Verified</span>
                )}
              </div>

              <div className="divider" style={{ margin: '0.5rem 0' }} />

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ width: 32, height: 32, borderRadius: 'var(--radius-sm)', background: 'rgba(139,92,246,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Key size={16} color="#a78bfa" />
                </div>
                <div>
                  <div className="text-muted text-sm">Roles</div>
                  <div style={{ display: 'flex', gap: '0.25rem', marginTop: '0.1rem', flexWrap: 'wrap' }}>
                    {user.roles.map(r => (
                      <span key={r} className="badge badge-blue">{r.replace('_', ' ')}</span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="divider" style={{ margin: '0.5rem 0' }} />

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ width: 32, height: 32, borderRadius: 'var(--radius-sm)', background: 'rgba(16,185,129,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Clock size={16} color="#34d399" />
                </div>
                <div>
                  <div className="text-muted text-sm">Member Since</div>
                  <div className="fw-700">{new Date(user.created_at).toLocaleDateString()}</div>
                </div>
              </div>

            </div>
          </div>

          <div className="card">
            <div className="card-header"><div className="card-title">Security & Credentials</div></div>
            <p className="text-muted text-sm" style={{ marginBottom: '1rem' }}>
              Ensure your account is secure. You can reset your password if you feel it has been compromised.
            </p>
            <button className="btn btn-secondary w-100" onClick={() => navigate('/reset-password')}>
              <Key size={16} /> Reset Password
            </button>
            <button className="btn btn-secondary w-100" style={{ marginTop: '0.75rem' }} disabled>
              <ShieldCheck size={16} /> Setup Two-Factor Auth (Commig Soon)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
