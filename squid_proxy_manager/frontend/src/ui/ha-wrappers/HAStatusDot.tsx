interface HAStatusDotProps {
  status: 'running' | 'stopped' | 'error';
  label?: string;
}

const COLOR_MAP: Record<HAStatusDotProps['status'], string> = {
  running: 'var(--success-color, #43a047)',
  stopped: 'var(--secondary-text-color, #9b9b9b)',
  error: 'var(--error-color, #db4437)',
};

export function HAStatusDot({ status, label }: HAStatusDotProps) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
      }}
    >
      <span
        style={{
          width: '10px',
          height: '10px',
          borderRadius: '50%',
          backgroundColor: COLOR_MAP[status],
          flexShrink: 0,
        }}
        aria-label={label ?? status}
      />
      {label && (
        <span style={{ fontSize: '14px', fontWeight: 500, color: COLOR_MAP[status] }}>
          {label}
        </span>
      )}
    </span>
  );
}
