import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  getInstances,
  startInstance,
  stopInstance
} from '@/api/instances';
import {
  HAButton,
  HACard,
  HAFab,
  HAIcon,
  HATopBar
} from '@/ui/ha-wrappers';

export function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const instancesQuery = useQuery({ queryKey: ['instances'], queryFn: getInstances });
  const [searchQuery, setSearchQuery] = useState('');

  const instances = useMemo(
    () => instancesQuery.data?.instances ?? [],
    [instancesQuery.data?.instances]
  );

  const runningCount = useMemo(
    () => instances.filter((i) => i.running ?? i.status === 'running').length,
    [instances]
  );

  const filteredInstances = useMemo(
    () =>
      searchQuery.trim()
        ? instances.filter((i) =>
            i.name.toLowerCase().includes(searchQuery.trim().toLowerCase()) ||
            String(i.port).includes(searchQuery.trim())
          )
        : instances,
    [instances, searchQuery]
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
      />

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px 16px 80px' }}>
        {/* Search bar */}
        {!instancesQuery.isLoading && !instancesQuery.isError && instances.length > 0 && (
          <div
            style={{
              position: 'relative',
              marginBottom: '16px',
            }}
          >
            <div
              style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                display: 'flex',
                alignItems: 'center',
                color: 'var(--secondary-text-color, #9b9b9b)',
                pointerEvents: 'none',
              }}
            >
              <HAIcon icon="mdi:magnify" style={{ width: '20px', height: '20px', fontSize: '16px' }} />
            </div>
            <input
              type="text"
              placeholder="Search instances..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              data-testid="dashboard-search-input"
              onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--primary-color, #03a9f4)'; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--divider-color, rgba(225,225,225,0.12))'; }}
              style={{
                width: '100%',
                padding: '10px 12px 10px 40px',
                border: '1px solid var(--divider-color, rgba(225,225,225,0.12))',
                borderRadius: '28px',
                backgroundColor: 'var(--card-background-color, #1c1c1c)',
                color: 'var(--primary-text-color, #e1e1e1)',
                fontSize: '14px',
                outline: 'none',
                boxSizing: 'border-box',
                transition: 'border-color 0.15s',
              }}
            />
          </div>
        )}

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
                Create your first proxy instance to get started.
              </div>
              <HAButton
                variant="primary"
                onClick={() => navigate('/proxies/new')}
                data-testid="empty-state-add-button"
              >
                Create Instance
              </HAButton>
            </div>
          </HACard>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 350px), 1fr))',
              gap: '16px',
            }}
          >
            {filteredInstances.map((instance) => {
              const isRunning = instance.running ?? instance.status === 'running';
              return (
                <HACard key={instance.name} data-testid={`instance-card-${instance.name}`}>
                  {/* Clickable top section */}
                  <div
                    style={{
                      padding: '16px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                    }}
                    onClick={() => navigate(`/proxies/${instance.name}/settings`)}
                    data-testid={`instance-settings-chip-${instance.name}`}
                  >
                    {/* Icon area with status-colored background */}
                    <div
                      data-testid={`instance-status-indicator-${instance.name}`}
                      style={{
                        position: 'relative',
                        width: '40px',
                        height: '40px',
                        borderRadius: '12px',
                        backgroundColor: isRunning
                          ? 'rgba(67, 160, 71, 0.15)'
                          : 'rgba(158, 158, 158, 0.15)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <HAIcon
                        icon={instance.proxy_type === 'tls_tunnel' ? 'mdi:shield-lock-outline' : 'mdi:server-network'}
                        style={{
                          width: '22px',
                          height: '22px',
                          fontSize: '18px',
                          color: isRunning
                            ? 'var(--success-color, #43a047)'
                            : 'var(--secondary-text-color, #9b9b9b)',
                        }}
                      />
                      {/* Green status dot overlay */}
                      {isRunning && (
                        <span
                          style={{
                            position: 'absolute',
                            top: '-2px',
                            right: '-2px',
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            backgroundColor: 'var(--success-color, #43a047)',
                            border: '2px solid var(--card-background-color, #1c1c1c)',
                          }}
                        />
                      )}
                    </div>

                    {/* Instance name */}
                    <div
                      style={{
                        flex: 1,
                        fontSize: '16px',
                        fontWeight: 500,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        color: 'var(--primary-text-color, #e1e1e1)',
                      }}
                    >
                      {instance.name}
                    </div>

                    {/* Proxy type badge */}
                    {instance.proxy_type === 'tls_tunnel' ? (
                      <span
                        data-testid={`instance-type-badge-${instance.name}`}
                        style={{
                          fontSize: '11px',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          backgroundColor: 'rgba(76, 175, 80, 0.15)',
                          color: 'var(--success-color, #4caf50)',
                          fontWeight: 500,
                          whiteSpace: 'nowrap',
                        }}>
                        TLS Tunnel
                      </span>
                    ) : (
                      <span
                        data-testid={`instance-type-badge-${instance.name}`}
                        style={{
                          fontSize: '11px',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          backgroundColor: 'rgba(3, 169, 244, 0.15)',
                          color: 'var(--primary-color, #03a9f4)',
                          fontWeight: 500,
                          whiteSpace: 'nowrap',
                        }}>
                        Squid Proxy
                      </span>
                    )}

                    {/* Chevron */}
                    <HAIcon
                      icon="mdi:chevron-right"
                      style={{
                        width: '24px',
                        height: '24px',
                        fontSize: '20px',
                        color: 'var(--secondary-text-color, #9b9b9b)',
                        flexShrink: 0,
                      }}
                    />
                  </div>

                  {/* Divider */}
                  <div
                    style={{
                      height: '1px',
                      backgroundColor: 'var(--divider-color, rgba(225,225,225,0.12))',
                      margin: '0 16px',
                    }}
                  />

                  {/* Bottom section: port info + action buttons */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 8px 8px 16px',
                      minHeight: '48px',
                    }}
                  >
                    {/* Port info */}
                    <div>
                      <span
                        style={{
                          fontSize: '14px',
                          fontWeight: 500,
                          color: 'var(--primary-color, #009ac7)',
                        }}
                      >
                        Port {instance.port}
                      </span>
                      {instance.proxy_type === 'tls_tunnel' && instance.forward_address && (
                        <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)', marginTop: '2px' }}>
                          {'→ '}{instance.forward_address}
                        </div>
                      )}
                    </div>

                    {/* Start/Stop button - show only the relevant action */}
                    {isRunning ? (
                      <HAButton
                        variant="danger"
                        size="sm"
                        outlined
                        onClick={() => stopMutation.mutate(instance.name)}
                        disabled={stopMutation.isPending}
                        loading={stopMutation.isPending}
                        data-testid={`instance-stop-chip-${instance.name}`}
                      >
                        <HAIcon icon="mdi:stop" slot="start" />
                        Stop
                      </HAButton>
                    ) : (
                      <HAButton
                        variant="success"
                        size="sm"
                        onClick={() => startMutation.mutate(instance.name)}
                        disabled={startMutation.isPending}
                        loading={startMutation.isPending}
                        data-testid={`instance-start-chip-${instance.name}`}
                      >
                        <HAIcon icon="mdi:play" slot="start" />
                        Start
                      </HAButton>
                    )}
                  </div>
                </HACard>
              );
            })}
          </div>
        )}
      </div>

      {/* FAB for adding instances - only show when instances exist */}
      {instances.length > 0 && (
        <HAFab
          label="Add Instance"
          icon="mdi:plus"
          onClick={() => navigate('/proxies/new')}
          data-testid="add-instance-button"
        />
      )}
    </div>
  );
}
