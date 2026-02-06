import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { GeneralTab } from './tabs/GeneralTab';
import { HTTPSTab } from './tabs/HTTPSTab';
import { LogsTab } from './tabs/LogsTab';
import { TestTab } from './tabs/TestTab';
import { UsersTab } from './tabs/UsersTab';

import { deleteInstance, getInstances } from '@/api/instances';
import { HAButton, HACard, HADialog, HAIcon, HAStatusDot, HATopBar } from '@/ui/ha-wrappers';

export function InstanceSettingsPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

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

  const handleDelete = () => {
    deleteMutation.mutate();
    setShowDeleteDialog(false);
  };

  // Local state for editable fields
  const [port, setPort] = useState<number | null>(null);
  const [httpsEnabled, setHttpsEnabled] = useState<boolean | null>(null);

  const resolvedPort = port ?? instance?.port ?? 3128;
  const resolvedHttpsEnabled = httpsEnabled ?? instance?.https_enabled ?? false;

  const isRunning = instance?.running ?? instance?.status === 'running';

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
          <HAStatusDot
            status={isRunning ? 'running' : 'stopped'}
            label={isRunning ? 'Running' : 'Stopped'}
          />
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
              />
            </div>
          </HACard>

          {resolvedHttpsEnabled && (
            <HACard title="Certificate">
              <div style={{ padding: '16px' }}>
                <HTTPSTab instanceName={instance.name} httpsEnabled={resolvedHttpsEnabled} />
              </div>
            </HACard>
          )}

          <HACard title="Proxy Users">
            <div style={{ padding: '16px' }}>
              <UsersTab instanceName={instance.name} />
            </div>
          </HACard>

          <HACard title="Test Connectivity">
            <div style={{ padding: '16px' }}>
              <TestTab instanceName={instance.name} />
            </div>
          </HACard>

          <HACard title="Instance Logs">
            <div style={{ padding: '16px' }}>
              <LogsTab instanceName={instance.name} />
            </div>
          </HACard>

          <HACard
            title="Danger Zone"
            outlined
            style={{ borderLeft: '4px solid var(--error-color, #db4437)' }}
          >
            <div style={{ padding: '16px' }}>
              <p style={{ fontSize: '14px', marginBottom: '12px', color: 'var(--secondary-text-color, #9b9b9b)' }}>
                Permanently delete this proxy instance and all its configuration.
              </p>
              <HAButton
                variant="danger"
                onClick={() => setShowDeleteDialog(true)}
                disabled={deleteMutation.isPending}
                data-testid="settings-delete-button"
              >
                Delete Instance
              </HAButton>
            </div>
          </HACard>
        </div>
      </div>

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
