import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  getInstances,
  startInstance,
  stopInstance
} from '@/api/instances';
import {
  HAButton,
  HACard,
  HAIcon,
  HAIconButton,
  HATopBar
} from '@/ui/ha-wrappers';

export function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const instancesQuery = useQuery({ queryKey: ['instances'], queryFn: getInstances });

  const instances = useMemo(
    () => instancesQuery.data?.instances ?? [],
    [instancesQuery.data?.instances]
  );

  const runningCount = useMemo(
    () => instances.filter((i) => i.running ?? i.status === 'running').length,
    [instances]
  );

  const startMutation = useMutation({
    mutationFn: (name: string) => startInstance(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['instances'] })
  });

  const stopMutation = useMutation({
    mutationFn: (name: string) => stopInstance(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['instances'] })
  });

  return (
    <div style={{ minHeight: '100vh' }}>
      <HATopBar
        title="Squid Proxy Manager"
        subtitle={`Instances: ${instances.length}  \u00b7  Running: ${runningCount}`}
        actions={
          <HAButton
            variant="primary"
            onClick={() => navigate('/proxies/new')}
            data-testid="add-instance-button"
          >
            <HAIcon icon="mdi:plus" slot="icon" />
            Add Instance
          </HAButton>
        }
      />

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px 16px 32px' }}>
        {instancesQuery.isLoading ? (
          <HACard title="Loading instances">
            <div style={{ padding: '16px', fontSize: '14px' }}>Loading...</div>
          </HACard>
        ) : instancesQuery.isError ? (
          <HACard title="Failed to load">
            <div style={{ padding: '16px', fontSize: '14px' }}>Unable to load instances.</div>
          </HACard>
        ) : instances.length === 0 ? (
          <HACard>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                padding: '48px 16px',
                textAlign: 'center',
              }}
            >
              <HAIcon
                icon="mdi:server-network"
                style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.5 }}
              />
              <div style={{ fontSize: '16px', fontWeight: 500, marginBottom: '8px' }}>
                No proxy instances
              </div>
              <div style={{ fontSize: '14px', color: 'var(--secondary-text-color, #9b9b9b)', marginBottom: '16px' }}>
                Create your first Squid proxy instance to get started.
              </div>
              <HAButton
                variant="primary"
                onClick={() => navigate('/proxies/new')}
                data-testid="empty-state-add-button"
              >
                <HAIcon icon="mdi:plus" slot="icon" />
                Create Instance
              </HAButton>
            </div>
          </HACard>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 400px), 1fr))', gap: '16px' }}>
            {instances.map((instance) => {
              const isRunning = instance.running ?? instance.status === 'running';
              return (
                <HACard key={instance.name} data-testid={`instance-card-${instance.name}`}>
                  {/* Clickable card body */}
                  <div
                    style={{ padding: '16px 16px 0', cursor: 'pointer' }}
                    onClick={() => navigate(`/proxies/${instance.name}/settings`)}
                  >
                    {/* Top row: status dot + name */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span
                          style={{
                            width: '10px',
                            height: '10px',
                            borderRadius: '50%',
                            flexShrink: 0,
                            backgroundColor: isRunning
                              ? 'var(--success-color, #43a047)'
                              : 'var(--error-color, #db4437)',
                          }}
                        />
                        <span style={{ fontSize: '16px', fontWeight: 500 }}>
                          {instance.name}
                        </span>
                      </div>
                      <span
                        style={{
                          fontSize: '12px',
                          color: isRunning
                            ? 'var(--success-color, #43a047)'
                            : 'var(--error-color, #db4437)',
                          fontWeight: 500,
                        }}
                      >
                        {isRunning ? 'Running' : 'Stopped'}
                      </span>
                    </div>

                    {/* Info row */}
                    <div
                      style={{
                        fontSize: '13px',
                        color: 'var(--secondary-text-color, #9b9b9b)',
                        marginTop: '6px',
                        marginLeft: '20px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <span>Port: <strong style={{ fontWeight: 500 }}>{instance.port}</strong></span>
                      <span style={{ margin: '0 6px', opacity: 0.4 }}>|</span>
                      <span>HTTPS: <strong style={{ fontWeight: 500 }}>{instance.https_enabled ? 'Enabled' : 'Disabled'}</strong></span>
                      <span style={{ margin: '0 6px', opacity: 0.4 }}>|</span>
                      <span>Users: <strong style={{ fontWeight: 500 }}>{instance.user_count ?? 0}</strong></span>
                    </div>
                  </div>

                  {/* Divider */}
                  <div
                    style={{
                      height: '1px',
                      backgroundColor: 'var(--divider-color, rgba(225,225,225,0.12))',
                      margin: '12px 16px',
                    }}
                  />

                  {/* Action row: compact buttons */}
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '0 16px 16px' }}>
                    <HAButton
                      variant={isRunning ? 'secondary' : 'success'}
                      size="sm"
                      onClick={() => startMutation.mutate(instance.name)}
                      disabled={isRunning || startMutation.isPending}
                      data-testid={`instance-start-chip-${instance.name}`}
                    >
                      Start
                    </HAButton>
                    <HAButton
                      variant={isRunning ? 'danger' : 'secondary'}
                      size="sm"
                      onClick={() => stopMutation.mutate(instance.name)}
                      disabled={!isRunning || stopMutation.isPending}
                      data-testid={`instance-stop-chip-${instance.name}`}
                    >
                      Stop
                    </HAButton>
                    <div style={{ flex: 1 }} />
                    <HAIconButton
                      icon="mdi:cog"
                      label="Settings"
                      onClick={() => navigate(`/proxies/${instance.name}/settings`)}
                      data-testid={`instance-settings-chip-${instance.name}`}
                    />
                  </div>
                </HACard>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
