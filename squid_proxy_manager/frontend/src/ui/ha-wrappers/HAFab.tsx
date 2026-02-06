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
      }}
    >
      <HAButton
        raised
        variant="primary"
        disabled={disabled}
        onClick={onClick}
        data-testid={testId}
      >
        <HAIcon icon={icon} slot="icon" />
        {label}
      </HAButton>
    </div>
  );
}
