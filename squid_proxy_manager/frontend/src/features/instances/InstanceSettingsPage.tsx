import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { ConnectionInfoTab } from './tabs/ConnectionInfoTab';
import { CoverSiteTab } from './tabs/CoverSiteTab';
import { GeneralTab } from './tabs/GeneralTab';
import { HTTPSTab } from './tabs/HTTPSTab';
import { LogsTab } from './tabs/LogsTab';
import { TestTab } from './tabs/TestTab';
import { TlsTunnelTestTab } from './tabs/TlsTunnelTestTab';
import { UsersTab } from './tabs/UsersTab';

import { deleteInstance, getInstances, startInstance, stopInstance, updateInstance } from '@/api/instances';
import { HAButton, HACard, HADialog, HAIcon, HATopBar } from '@/ui/ha-wrappers';

export function InstanceSettingsPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showLogsDialog, setShowLogsDialog] = useState(false);

  const instancesQuery = useQuery({
    queryKey: ['instances'],
    queryFn: getInstances
  });

  const instance = useMemo(
    () => instancesQuery.data?.instances.find((item) => item.name === name),
    [instancesQuery.data, name]
  );

  const deleteMutation = useMutation({
    mutationFn: () => deleteInstance(name!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      navigate('/');
    }
  });

  const startMutation = useMutation({
    mutationFn: () => startInstance(name!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    }
  });

  const stopMutation = useMutation({
    mutationFn: () => stopInstance(name!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    }
  });

  const handleDelete = () => {
    deleteMutation.mutate();
    setShowDeleteDialog(false);
  };

  // Local state for editable fields
  const [port, setPort] = useState<number | null>(null);
  const [httpsEnabled, setHttpsEnabled] = useState<boolean | null>(null);
  const [forwardAddress, setForwardAddress] = useState<string | null>(null);
  const [coverDomain, setCoverDomain] = useState<string | null>(null);

  const resolvedPort = port ?? instance?.port ?? 3128;
  const resolvedHttpsEnabled = httpsEnabled ?? instance?.https_enabled ?? false;
  const resolvedForwardAddress = forwardAddress ?? instance?.forward_address ?? '';
  const resolvedCoverDomain = coverDomain ?? instance?.cover_domain ?? '';

  const isRunning = instance?.running ?? instance?.status === 'running';
  const proxyType = instance?.proxy_type ?? 'squid';
  const isTlsTunnel = proxyType === 'tls_tunnel';

  // Cover site save mutation
  const coverSiteMutation = useMutation({
    mutationFn: (payload: { cover_domain: string }) =>
      updateInstance(name!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    }
  });

  const coverSiteIsDirty = resolvedCoverDomain !== (instance?.cover_domain ?? '');

  const handleCoverSiteSave = () => {
    coverSiteMutation.mutate({ cover_domain: resolvedCoverDomain });
  };

  if (instancesQuery.isLoading) {
    return (
      <div style={{ minHeight: '100vh' }}>
        <HATopBar title="Loading..." onBack={() => navigate('/')} />
        <div style={{ maxWidth: '800px', margin: '0 auto', padding: '16px 16px' }}>
          <HACard title="Loading...">
            <div style={{ padding: '16px', fontSize: '14px' }}>Loading instance settings...</div>
          </HACard>
        </div>
      </div>
    );
  }

  if (!instance) {
    return (
      <div style={{ minHeight: '100vh' }}>
        <HATopBar title="Not Found" onBack={() => navigate('/')} />
        <div style={{ maxWidth: '800px', margin: '0 auto', padding: '16px 16px' }}>
          <HACard title="Not Found">
            <div style={{ padding: '16px', fontSize: '14px' }}>Instance &quot;{name}&quot; not found.</div>
          </HACard>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh' }}>
      <HATopBar
        title={instance.name}
        onBack={() => navigate('/')}
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Status chip: colored dot + label in a compact pill */}
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 12px 4px 8px',
                borderRadius: '16px',
                backgroundColor: isRunning
                  ? 'rgba(67, 160, 71, 0.15)'
                  : 'rgba(158, 158, 158, 0.12)',
                lineHeight: 1,
              }}
              data-testid="settings-status-chip"
            >
              <span
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: isRunning
                    ? 'var(--success-color, #43a047)'
                    : 'var(--secondary-text-color, #9b9b9b)',
                  flexShrink: 0,
                }}
              />
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 500,
                  color: isRunning
                    ? 'var(--success-color, #43a047)'
                    : 'var(--secondary-text-color, #9b9b9b)',
                  whiteSpace: 'nowrap',
                }}
              >
                {isRunning ? 'Running' : 'Stopped'}
              </span>
            </span>

            {/* Single toggle action button: shows Start or Stop based on state */}
            {isRunning ? (
              <HAButton
                variant="danger"
                size="sm"
                outlined
                onClick={() => stopMutation.mutate()}
                disabled={stopMutation.isPending}
                loading={stopMutation.isPending}
                data-testid="settings-stop-button"
              >
                <HAIcon icon="mdi:stop" slot="start" />
                Stop
              </HAButton>
            ) : (
              <HAButton
                variant="success"
                size="sm"
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending}
                loading={startMutation.isPending}
                data-testid="settings-start-button"
              >
                <HAIcon icon="mdi:play" slot="start" />
                Start
              </HAButton>
            )}
          </div>
        }
      />

      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '16px 16px 32px' }}>
        <div style={{ display: 'grid', gap: '16px' }}>
          <HACard title="Configuration" data-testid="settings-tabs">
            <div style={{ padding: '16px' }}>
              <GeneralTab
                instance={instance}
                port={resolvedPort}
                httpsEnabled={resolvedHttpsEnabled}
                onPortChange={setPort}
                onHttpsChange={setHttpsEnabled}
                proxyType={proxyType}
                forwardAddress={resolvedForwardAddress}
                coverDomain={resolvedCoverDomain}
                onForwardAddressChange={setForwardAddress}
                onCoverDomainChange={setCoverDomain}
              />
            </div>
          </HACard>

          {!isTlsTunnel && resolvedHttpsEnabled && (
            <HACard title="Certificate">
              <div style={{ padding: '16px' }}>
                <HTTPSTab instanceName={instance.name} httpsEnabled={resolvedHttpsEnabled} />
              </div>
            </HACard>
          )}

          {!isTlsTunnel && (
            <HACard title="Proxy Users">
              <div style={{ padding: '16px' }}>
                <UsersTab instanceName={instance.name} />
              </div>
            </HACard>
          )}

          {!isTlsTunnel && (
            <HACard title="Test Connectivity">
              <div style={{ padding: '16px' }}>
                <TestTab instanceName={instance.name} />
              </div>
            </HACard>
          )}

          {isTlsTunnel && (
            <HACard title="Connection Info">
              <div style={{ padding: '16px' }}>
                <ConnectionInfoTab
                  instanceName={instance.name}
                  port={resolvedPort}
                  forwardAddress={resolvedForwardAddress}
                />
              </div>
            </HACard>
          )}

          {isTlsTunnel && (
            <HACard title="Cover Site">
              <div style={{ padding: '16px' }}>
                <CoverSiteTab
                  instanceName={instance.name}
                  coverDomain={resolvedCoverDomain}
                  port={resolvedPort}
                  onCoverDomainChange={(domain) => setCoverDomain(domain)}
                  onSave={handleCoverSiteSave}
                  saving={coverSiteMutation.isPending}
                  isDirty={coverSiteIsDirty}
                />
              </div>
            </HACard>
          )}

          {isTlsTunnel && (
            <HACard title="Test TLS Tunnel">
              <div style={{ padding: '16px' }}>
                <TlsTunnelTestTab instanceName={instance.name} />
              </div>
            </HACard>
          )}

          <HACard>
            <div
              style={{
                padding: '16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ fontSize: '16px', fontWeight: 500, marginBottom: '4px' }}>
                  Instance Logs
                </div>
                <div style={{ fontSize: '14px', color: 'var(--secondary-text-color, #9b9b9b)' }}>
                  View access and cache logs for this instance.
                </div>
              </div>
              <HAButton
                variant="secondary"
                onClick={() => setShowLogsDialog(true)}
                data-testid="settings-view-logs-button"
              >
                <HAIcon icon="mdi:text-box-outline" slot="start" />
                View Logs
              </HAButton>
            </div>
          </HACard>

          <HACard
            outlined
            style={{ borderLeft: '4px solid var(--error-color, #db4437)' }}
          >
            <div
              style={{
                padding: '16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '16px',
              }}
            >
              <div>
                <div style={{ fontSize: '16px', fontWeight: 500, marginBottom: '4px' }}>
                  Danger Zone
                </div>
                <div style={{ fontSize: '14px', color: 'var(--secondary-text-color, #9b9b9b)' }}>
                  Permanently delete this proxy instance and all its configuration.
                </div>
              </div>
              <HAButton
                variant="danger"
                onClick={() => setShowDeleteDialog(true)}
                disabled={deleteMutation.isPending}
                data-testid="settings-delete-button"
              >
                <HAIcon icon="mdi:delete" slot="start" />
                Delete
              </HAButton>
            </div>
          </HACard>
        </div>
      </div>

      <HADialog
        id="logs-dialog"
        title="Instance Logs"
        isOpen={showLogsDialog}
        onClose={() => setShowLogsDialog(false)}
        maxWidth="900px"
      >
        <div style={{ padding: '0 16px 16px', height: '60vh', display: 'flex', flexDirection: 'column' }}>
          <LogsTab instanceName={instance.name} proxyType={proxyType} />
        </div>
      </HADialog>

      <HADialog
        id="delete-confirm-dialog"
        title="Delete Instance"
        isOpen={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
        footer={
          <div style={{ display: 'flex', gap: '8px' }}>
            <HAButton variant="ghost" onClick={() => setShowDeleteDialog(false)}>Cancel</HAButton>
            <HAButton
              variant="danger"
              onClick={handleDelete}
              loading={deleteMutation.isPending}
              data-testid="delete-confirm-button"
            >
              <HAIcon icon="mdi:delete" slot="start" />
              Delete
            </HAButton>
          </div>
        }
      >
        <div style={{ padding: '16px', display: 'flex', gap: '12px' }}>
          <HAIcon icon="mdi:alert-circle" style={{ color: 'var(--error-color, #db4437)', fontSize: '24px', flexShrink: 0 }} />
          <div>
            <p>Are you sure you want to delete the instance &quot;{instance.name}&quot;?</p>
            <p style={{ fontSize: '14px', marginTop: '8px', color: 'var(--secondary-text-color, #9b9b9b)' }}>
              This will permanently remove the instance, its configuration, users, and certificates. This action cannot be undone.
            </p>
          </div>
        </div>
      </HADialog>
    </div>
  );
}
