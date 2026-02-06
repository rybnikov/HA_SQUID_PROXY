import type { CSSProperties, HTMLAttributes, ReactNode } from 'react';

interface HACardProps extends HTMLAttributes<HTMLElement> {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  outlined?: boolean;
  header?: string;
  statusTone?: 'loaded' | 'not_loaded' | 'error';
}

const hasHaCard = typeof customElements !== 'undefined' && Boolean(customElements.get('ha-card'));

export function HACard({
  title,
  subtitle,
  action,
  children,
  className,
  outlined = true,
  header,
  statusTone = 'loaded',
  style,
  ...props
}: HACardProps) {
  const resolvedHeader = header ?? title;

  if (hasHaCard) {
    return (
      <ha-card
        header={resolvedHeader}
        outlined={outlined}
        className={className}
        data-status-tone={statusTone}
        style={style}
        {...props}
      >
        {subtitle || action ? (
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px', padding: '8px 16px 0' }}>
            <div>{subtitle ? <p>{subtitle}</p> : null}</div>
            {action}
          </div>
        ) : null}
        {children}
      </ha-card>
    );
  }

  // Fallback: styled div that mimics ha-card — merge base + prop styles
  const baseStyle: CSSProperties = {
    backgroundColor: 'var(--card-background-color, #1c1c1c)',
    borderRadius: '12px',
    border: outlined ? '1px solid var(--divider-color, rgba(225,225,225,0.12))' : 'none',
    overflow: 'hidden',
  };

  return (
    <div
      className={className}
      data-status-tone={statusTone}
      {...(props as HTMLAttributes<HTMLDivElement>)}
      style={{ ...baseStyle, ...(style as CSSProperties) }}
    >
      {resolvedHeader ? (
        <h2 style={{
          fontSize: '18px',
          fontWeight: 500,
          margin: 0,
          padding: '12px 16px 0',
          lineHeight: '36px',
          color: 'var(--primary-text-color, #e1e1e1)',
        }}>
          {resolvedHeader}
        </h2>
      ) : null}
      {subtitle || action ? (
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px', padding: '8px 16px 0' }}>
          <div>{subtitle ? <p>{subtitle}</p> : null}</div>
          {action}
        </div>
      ) : null}
      {children}
    </div>
  );
}
