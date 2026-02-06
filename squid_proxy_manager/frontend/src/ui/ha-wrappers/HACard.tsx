import type { HTMLAttributes, ReactNode } from 'react';

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

export function HACard({
  title,
  subtitle,
  action,
  children,
  className,
  outlined = true,
  header,
  statusTone = 'loaded',
  ...props
}: HACardProps) {
  const resolvedHeader = header ?? title;

  return (
    <ha-card
      header={resolvedHeader}
      outlined={outlined}
      className={className}
      data-status-tone={statusTone}
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
