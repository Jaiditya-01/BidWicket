import React from 'react';
import './Skeleton.css';

interface SkeletonProps {
  type?: 'text' | 'title' | 'avatar' | 'card' | 'thumbnail';
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ type = 'text', className = '', style }: SkeletonProps) {
  return (
    <div
      className={`skeleton skeleton-${type} ${className}`}
      style={style}
    />
  );
}

export function PageSkeleton() {
  return (
    <div className="fade-in" style={{ padding: '2rem' }}>
      <Skeleton type="title" style={{ width: '40%', marginBottom: '2rem' }} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
        <Skeleton type="card" />
        <Skeleton type="card" />
        <Skeleton type="card" />
        <Skeleton type="card" />
      </div>
    </div>
  );
}
