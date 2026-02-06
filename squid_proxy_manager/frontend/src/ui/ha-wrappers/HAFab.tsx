import { HAButton } from './HAButton';
import { HAIcon } from './HAIcon';

interface HAFabProps {
  label: string;
  icon: string;
  onClick: () => void;
  disabled?: boolean;
  'data-testid'?: string;
}

export function HAFab({ label, icon, onClick, disabled, 'data-testid': testId }: HAFabProps) {
  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 5,
        borderRadius: '28px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3), 0 1px 4px rgba(0, 0, 0, 0.2)',
        overflow: 'hidden',
      }}
    >
      <HAButton
        raised
        variant="primary"
        disabled={disabled}
        onClick={onClick}
        data-testid={testId}
        style={{ borderRadius: '28px' }}
      >
        <HAIcon icon={icon} slot="start" />
        {label}
      </HAButton>
    </div>
  );
}
