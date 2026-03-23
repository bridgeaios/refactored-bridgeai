import { FC } from 'react'

interface LoadingSpinnerProps {
  size?: number
}

export const LoadingSpinner: FC<LoadingSpinnerProps> = ({ size = 80 }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" className="loading-spinner">
    <defs>
      <linearGradient id="bridgeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#2563eb" />
        <stop offset="100%" stopColor="#7c3aed" />
      </linearGradient>
    </defs>
    <rect x="20" y="35" width="60" height="8" rx="4" fill="url(#bridgeGrad)" />
    <rect x="35" y="20" width="8" height="60" rx="4" fill="url(#bridgeGrad)" />
    <circle cx="50" cy="50" r="25" fill="none" stroke="url(#bridgeGrad)" strokeWidth="4" opacity="0.3" />
    <circle cx="50" cy="50" r="18" fill="none" stroke="url(#bridgeGrad)" strokeWidth="2" opacity="0.5" />
    <circle cx="50" cy="50" r="10" fill="url(#bridgeGrad)" />
  </svg>
)

interface DataFlowProps {
  width?: number
  height?: number
}

export const DataFlow: FC<DataFlowProps> = ({ width = 120, height = 80 }) => (
  <svg width={width} height={height} viewBox="0 0 120 80">
    <defs>
      <linearGradient id="flowGrad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stopColor="#2563eb" />
        <stop offset="100%" stopColor="#7c3aed" />
      </linearGradient>
    </defs>
    <line x1="20" y1="20" x2="100" y2="20" stroke="#e5e7eb" strokeWidth="2" className="data-flow-line" />
    <line x1="20" y1="40" x2="100" y2="40" stroke="#e5e7eb" strokeWidth="2" className="data-flow-line" style={{ animationDelay: '0.3s' }} />
    <line x1="20" y1="60" x2="100" y2="60" stroke="#e5e7eb" strokeWidth="2" className="data-flow-line" style={{ animationDelay: '0.6s' }} />
    <circle cx="20" cy="20" r="6" fill="#2563eb" className="network-node" />
    <circle cx="60" cy="20" r="6" fill="#7c3aed" className="network-node" />
    <circle cx="100" cy="20" r="6" fill="#10b981" className="network-node" />
    <circle cx="20" cy="40" r="6" fill="#f59e0b" className="network-node" />
    <circle cx="60" cy="40" r="6" fill="#2563eb" className="network-node" />
    <circle cx="100" cy="40" r="6" fill="#ef4444" className="network-node" />
    <circle cx="20" cy="60" r="6" fill="#7c3aed" className="network-node" />
    <circle cx="60" cy="60" r="6" fill="#10b981" className="network-node" />
    <circle cx="100" cy="60" r="6" fill="#2563eb" className="network-node" />
    <rect className="data-particle" x="25" y="17" width="8" height="6" rx="3" fill="#2563eb" style={{ animationDelay: '0s' }} />
    <rect className="data-particle" x="65" y="37" width="8" height="6" rx="3" fill="#f59e0b" style={{ animationDelay: '0.5s' }} />
    <rect className="data-particle" x="25" y="57" width="8" height="6" rx="3" fill="#7c3aed" style={{ animationDelay: '1s' }} />
  </svg>
)

interface TwinPulseProps {
  size?: number
}

export const TwinPulse: FC<TwinPulseProps> = ({ size = 80 }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" className="twin-pulse">
    <defs>
      <linearGradient id="twinGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#ef4444" />
        <stop offset="100%" stopColor="#f59e0b" />
      </linearGradient>
    </defs>
    <path d="M10 50 Q25 50 30 30 Q35 10 50 10 Q65 10 70 30 Q75 50 90 50" 
          fill="none" stroke="url(#twinGrad)" strokeWidth="4" strokeLinecap="round" />
    <path d="M10 50 Q25 50 30 70 Q35 90 50 90 Q65 90 70 70 Q75 50 90 50" 
          fill="none" stroke="url(#twinGrad)" strokeWidth="4" strokeLinecap="round" opacity="0.5" />
    <circle cx="50" cy="50" r="15" fill="url(#twinGrad)" />
    <circle cx="50" cy="50" r="8" fill="white" />
  </svg>
)

interface MissionProgressProps {
  progress: number
  size?: number
}

export const MissionProgress: FC<MissionProgressProps> = ({ progress = 75, size = 80 }) => {
  const offset = 283 - (283 * progress) / 100
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" className="mission-progress">
      <circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" strokeWidth="8" />
      <circle 
        cx="50" cy="50" r="45" 
        fill="none" 
        stroke="url(#bridgeGrad)" 
        strokeWidth="8"
        strokeLinecap="round"
        className="mission-progress-circle"
        style={{ '--progress-offset': offset } as React.CSSProperties}
      />
      <text x="50" y="55" textAnchor="middle" fontSize="16" fontWeight="bold" fill="#1f2937">
        {progress}%
      </text>
    </svg>
  )
}

interface LeaderboardTrophyProps {
  rank?: number
  size?: number
}

export const LeaderboardTrophy: FC<LeaderboardTrophyProps> = ({ rank = 1, size = 60 }) => {
  const getColor = () => {
    if (rank === 1) return '#fbbf24'
    if (rank === 2) return '#c0c0c0'
    if (rank === 3) return '#cd7f32'
    return '#6b7280'
  }
  const color = getColor()
  
  return (
    <svg width={size} height={size} viewBox="0 0 60 60" className="trophy-icon">
      <defs>
        <linearGradient id="shimmerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="white" stopOpacity="0" />
          <stop offset="50%" stopColor="white" stopOpacity="0.8" />
          <stop offset="100%" stopColor="white" stopOpacity="0" />
        </linearGradient>
        <clipPath id="trophyClip">
          <path d="M15 25 Q15 10 30 10 Q45 10 45 25 L45 35 Q45 40 40 40 L20 40 Q15 40 15 35 Z" />
        </clipPath>
      </defs>
      <path d="M15 25 Q15 10 30 10 Q45 10 45 25 L45 35 Q45 40 40 40 L20 40 Q15 40 15 35 Z" 
            fill={color} stroke={color} strokeWidth="2" />
      <path d="M22 40 L22 48 Q22 52 30 52 Q38 52 38 48 L38 40" 
            fill={color} stroke={color} strokeWidth="2" />
      <rect x="18" y="52" width="24" height="4" rx="2" fill={color} />
      <path d="M25 18 L25 28 M35 18 L35 28" stroke="white" strokeWidth="2" opacity="0.5" />
      <ellipse cx="30" cy="25" rx="8" ry="4" fill="white" opacity="0.3" />
      <rect x="15" y="20" width="30" height="20" fill="url(#shimmerGrad)" className="trophy-shimmer" clipPath="url(#trophyClip)" />
    </svg>
  )
}
