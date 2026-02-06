import { useEffect, useRef } from 'react';

import { HAIcon } from './HAIcon';

interface HAFabProps {
  label: string;
  icon: string;
  onClick: () => void;
  disabled?: boolean;
  'data-testid'?: string;
}

export function HAFab({ label, icon, onClick, disabled, 'data-testid': testId }: HAFabProps) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const handler = () => {
      if (!disabled) onClick();
    };

    el.addEventListener('click', handler);
    return () => el.removeEventListener('click', handler);
  }, [disabled, onClick]);

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 5,
      }}
    >
      <ha-button
        ref={ref}
        raised
        disabled={disabled}
        data-testid={testId}
      >
        <HAIcon icon={icon} slot="icon" />
        {label}
      </ha-button>
    </div>
  );
}
