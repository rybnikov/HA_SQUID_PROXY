import type { ReactNode } from 'react';

import { HAIconButton } from './HAIconButton';

interface HATopBarProps {
  title: string;
  subtitle?: string;
  onBack?: () => void;
  actions?: ReactNode;
}

export function HATopBar({ title, subtitle, onBack, actions }: HATopBarProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        minHeight: '56px',
        padding: '0 12px',
        gap: '4px',
        backgroundColor: 'var(--app-header-background-color, #1c1c1c)',
        borderBottom: '1px solid var(--divider-color, rgba(225,225,225,0.12))',
      }}
    >
      {onBack && (
        <HAIconButton
          icon="mdi:arrow-left"
          label="Back"
          onClick={onBack}
        />
      )}
      <div
        style={{
          flex: 1,
          overflow: 'hidden',
          paddingLeft: onBack ? '0' : '4px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
        }}
      >
        <h1
          style={{
            fontSize: '20px',
            fontWeight: 400,
            margin: 0,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <span
            style={{
              fontSize: '14px',
              fontWeight: 400,
              color: 'var(--secondary-text-color, #9b9b9b)',
              marginTop: '2px',
            }}
          >
            {subtitle}
          </span>
        )}
      </div>
      {actions && <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>{actions}</div>}
    </div>
  );
}
