import { cn } from '@/utils/cn';

type BadgeTone = 'success' | 'warning' | 'danger' | 'info';

interface BadgeProps {
  label: string;
  tone?: BadgeTone;
}

const toneStyles: Record<BadgeTone, string> = {
  success: 'bg-success/20 text-success',
  warning: 'bg-warning/20 text-warning',
  danger: 'bg-danger/20 text-danger',
  info: 'bg-primary/20 text-primary'
};

export function Badge({ label, tone = 'info' }: BadgeProps) {
  return (
    <span className={cn('rounded-pill px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em]', toneStyles[tone])}>
      {label}
    </span>
  );
}
