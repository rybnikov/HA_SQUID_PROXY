import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { HAButton, HAIcon } from '@/ui/ha-wrappers';
import { apiFetch } from '@/api/client';

interface RawConfigTabProps {
  instanceName: string;
  proxyType: 'squid' | 'tls_tunnel';
}

async function getConfig(instanceName: string): Promise<{ config: string }> {
  return apiFetch(`api/instances/${instanceName}/raw-config`);
}

async function updateConfig(instanceName: string, config: string): Promise<{ status: string }> {
  return apiFetch(`api/instances/${instanceName}/raw-config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config })
  });
}

export function RawConfigTab({ instanceName, proxyType }: RawConfigTabProps) {
  const queryClient = useQueryClient();
  const [editedConfig, setEditedConfig] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const configQuery = useQuery({
    queryKey: ['raw-config', instanceName],
    queryFn: () => getConfig(instanceName),
  });

  const updateMutation = useMutation({
    mutationFn: (config: string) => updateConfig(instanceName, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['raw-config', instanceName] });
      setSaved(true);
      setEditedConfig(null);
      setTimeout(() => setSaved(false), 2000);
    }
  });

  const currentConfig = editedConfig ?? configQuery.data?.config ?? '';
  const isDirty = editedConfig !== null && editedConfig !== configQuery.data?.config;

  // Add line numbers to the config
  const lines = currentConfig.split('\n');
  const lineNumbers = lines.map((_, i) => i + 1).join('\n');

  const configFileName = proxyType === 'tls_tunnel' ? 'nginx_stream.conf' : 'squid.conf';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h3 style={{ margin: '0 0 4px 0', fontSize: '16px', fontWeight: 500 }}>
            {configFileName}
          </h3>
          <p style={{ margin: 0, fontSize: '14px', color: 'var(--secondary-text-color)' }}>
            Edit the raw configuration file. Changes will regenerate the config on save.
          </p>
        </div>
        <HAButton
          onClick={() => {
            if (editedConfig !== null) {
              updateMutation.mutate(editedConfig);
            }
          }}
          loading={updateMutation.isPending}
          disabled={!isDirty || updateMutation.isPending}
          data-testid="raw-config-save-button"
        >
          <HAIcon icon={saved ? 'mdi:check' : 'mdi:content-save'} slot="start" />
          {saved ? 'Saved!' : 'Save Changes'}
        </HAButton>
      </div>

      {configQuery.isLoading && (
        <p style={{ fontSize: '14px', color: 'var(--secondary-text-color)' }}>
          Loading configuration...
        </p>
      )}

      {configQuery.isError && (
        <div style={{
          padding: '12px',
          backgroundColor: 'rgba(219, 68, 55, 0.1)',
          borderRadius: '8px',
          borderLeft: '4px solid var(--error-color)'
        }}>
          <p style={{ fontSize: '14px', color: 'var(--error-color)', margin: 0 }}>
            Failed to load configuration
          </p>
        </div>
      )}

      {configQuery.data && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'auto 1fr',
            border: '1px solid var(--divider-color)',
            borderRadius: '8px',
            overflow: 'hidden',
            backgroundColor: 'var(--secondary-background-color)',
          }}
        >
          {/* Line numbers */}
          <div
            style={{
              padding: '12px 8px',
              textAlign: 'right',
              fontFamily: 'monospace',
              fontSize: '13px',
              color: 'var(--secondary-text-color)',
              backgroundColor: 'var(--card-background-color)',
              borderRight: '1px solid var(--divider-color)',
              userSelect: 'none',
              lineHeight: '1.5',
            }}
          >
            {lineNumbers}
          </div>

          {/* Config editor */}
          <textarea
            value={currentConfig}
            onChange={(e) => setEditedConfig(e.target.value)}
            spellCheck={false}
            style={{
              width: '100%',
              minHeight: '500px',
              fontFamily: 'monospace',
              fontSize: '13px',
              padding: '12px',
              border: 'none',
              backgroundColor: 'transparent',
              color: 'var(--primary-text-color)',
              resize: 'vertical',
              lineHeight: '1.5',
              outline: 'none',
            }}
            data-testid="raw-config-editor"
          />
        </div>
      )}

      {updateMutation.isError && (
        <div style={{
          padding: '12px',
          backgroundColor: 'rgba(219, 68, 55, 0.1)',
          borderRadius: '8px',
          borderLeft: '4px solid var(--error-color)'
        }}>
          <p style={{ fontSize: '14px', color: 'var(--error-color)', margin: 0 }}>
            Failed to save configuration. Please check syntax and try again.
          </p>
        </div>
      )}

      <div style={{
        padding: '12px',
        backgroundColor: 'rgba(255, 152, 0, 0.1)',
        borderRadius: '8px',
        borderLeft: '4px solid var(--warning-color)'
      }}>
        <div style={{ display: 'flex', gap: '12px' }}>
          <HAIcon icon="mdi:alert" style={{ flexShrink: 0, color: 'var(--warning-color)' }} />
          <div>
            <p style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: 500 }}>
              Warning: Advanced Users Only
            </p>
            <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '14px', color: 'var(--secondary-text-color)' }}>
              <li>Manual edits may break the proxy if syntax is incorrect</li>
              <li>The instance will be restarted after saving</li>
              <li>Use the Settings tabs for standard configuration changes</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
