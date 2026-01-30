import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { getInstances } from '@/api/instances';
import { Button } from '@/ui/Button';
import { Card } from '@/ui/Card';

export function ProxyDetailsPage() {
  const { name } = useParams();
  const navigate = useNavigate();
  const instancesQuery = useQuery({ queryKey: ['instances'], queryFn: getInstances });

  const instance = useMemo(
    () => instancesQuery.data?.instances.find((item) => item.name === name),
    [instancesQuery.data, name]
  );

  return (
    <div className="min-h-screen bg-app-bg px-6 py-10 text-text-primary">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        <header className="space-y-2">
          <p className="text-xs uppercase tracking-[0.5em] text-text-secondary">Proxy detail</p>
          <h1 className="text-3xl font-semibold">{name ?? 'Proxy instance'}</h1>
          <p className="text-sm text-text-secondary">Quick status and configuration overview.</p>
        </header>

        <Card title="Instance overview" subtitle={instance ? `Port ${instance.port}` : 'Loading...'}>
          {instance ? (
            <div className="grid gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-2">
                  <span
                    className={instance.running ? 'h-2 w-2 rounded-full bg-success' : 'h-2 w-2 rounded-full bg-danger'}
                  />
                  <span className={instance.running ? 'text-success' : 'text-danger'}>
                    {instance.running ? 'Running' : 'Stopped'}
                  </span>
                </span>
                <span className="text-text-secondary">Status</span>
              </div>
              <div className="text-text-secondary">
                HTTPS: <span className="text-text-primary">{instance.https_enabled ? 'Enabled' : 'Disabled'}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-text-secondary">No instance found for this route.</p>
          )}
        </Card>

        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/')}>
            Back to dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}
