import { cn } from '@/utils/cn';

type BadgeTone = 'success' | 'warning' | 'danger' | 'info';

interface BadgeProps {
  label: string;
  tone?: BadgeTone;
}

const toneStyles: Record<BadgeTone, string> = {
  success: 'bg-success text-success',
  warning: 'bg-warning text-warning',
  danger: 'bg-danger text-danger',
  info: 'bg-info text-info'
};

export function Badge({ label, tone = 'info' }: BadgeProps) {
  const [dotColor, textColor] = toneStyles[tone].split(' ');
  return (
    <span className="inline-flex items-center gap-2 text-xs font-medium">
      <span className={cn('h-2 w-2 rounded-full', dotColor)} />
      <span className={cn('uppercase tracking-[0.2em]', textColor)}>{label}</span>
    </span>
  );
}
