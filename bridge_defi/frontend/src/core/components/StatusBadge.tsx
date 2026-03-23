interface StatusBadgeProps {
  status: 'online' | 'degraded' | 'offline' | 'unknown';
  label: string;
}

const colorByStatus: Record<StatusBadgeProps['status'], string> = {
  online: '#166534',
  degraded: '#92400e',
  offline: '#991b1b',
  unknown: '#334155',
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        borderRadius: '999px',
        border: `1px solid ${colorByStatus[status]}`,
        color: colorByStatus[status],
        fontSize: '0.75rem',
        padding: '0.2rem 0.6rem',
      }}
    >
      {label}
    </span>
  );
}
