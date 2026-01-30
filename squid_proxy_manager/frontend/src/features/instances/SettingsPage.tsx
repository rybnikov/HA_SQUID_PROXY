import { Button } from '@/ui/Button';
import { Card } from '@/ui/Card';

export function SettingsPage() {
  return (
    <div className="min-h-screen bg-surface px-6 py-10 text-foreground">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <header className="space-y-2">
          <p className="text-xs uppercase tracking-[0.5em] text-muted-foreground">Settings</p>
          <h1 className="text-3xl font-semibold">Global preferences</h1>
          <p className="text-sm text-muted-foreground">
            Global defaults and diagnostics will appear here in a future update.
          </p>
        </header>

        <Card title="Environment" subtitle="Ingress & runtime details">
          <div className="text-sm text-muted-foreground">
            Settings are managed per proxy instance today. Use the dashboard to configure ports,
            HTTPS, users, and logs.
          </div>
        </Card>

        <Button variant="secondary" onClick={() => window.history.back()}>
          Back
        </Button>
      </div>
    </div>
  );
}
