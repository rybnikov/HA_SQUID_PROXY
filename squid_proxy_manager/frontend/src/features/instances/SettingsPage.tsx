import { Button } from '@/ui/Button';
import { Card } from '@/ui/Card';

export function SettingsPage() {
  return (
    <div className="min-h-screen bg-app-bg px-4 sm:px-6 py-6 sm:py-10 text-text-primary">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <header className="space-y-2">
          <p className="text-xs uppercase tracking-[0.5em] text-text-secondary">Settings</p>
          <h1 className="text-2xl sm:text-3xl font-semibold">Global preferences</h1>
          <p className="text-sm text-text-secondary">
            Global defaults and diagnostics will appear here in a future update.
          </p>
        </header>

        <Card title="Environment" subtitle="Ingress & runtime details">
          <div className="text-sm text-text-secondary">
            Settings are managed per proxy instance today. Use the dashboard to configure ports,
            HTTPS, users, and logs.
          </div>
        </Card>

        <Button variant="secondary" className="w-full sm:w-auto rounded-full px-6" onClick={() => window.history.back()}>
          Back
        </Button>
      </div>
    </div>
  );
}
