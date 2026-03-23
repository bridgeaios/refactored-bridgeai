interface LoadingSpinnerProps {
  label?: string;
  size?: number;
}

export function LoadingSpinner({ label = 'Loading...', size = 24 }: LoadingSpinnerProps) {
  return (
    <div
      role="status"
      aria-label={label}
      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
    >
      <span
        aria-hidden="true"
        style={{
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: '50%',
          border: '3px solid rgba(100, 116, 139, 0.3)',
          borderTopColor: '#0f172a',
        }}
      />
      <span>{label}</span>
    </div>
  );
}
