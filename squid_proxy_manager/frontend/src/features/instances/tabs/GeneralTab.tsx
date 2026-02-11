import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { updateInstance, type ProxyInstance } from '@/api/instances';
import { HAButton, HAIcon, HASwitch, HATextField } from '@/ui/ha-wrappers';

interface GeneralTabProps {
  instance: ProxyInstance;
  onPortChange: (port: number) => void;
  onHttpsChange: (enabled: boolean) => void;
  port: number;
  httpsEnabled: boolean;
  proxyType?: string;
  forwardAddress?: string;
  coverDomain?: string;
  onForwardAddressChange?: (addr: string) => void;
  onCoverDomainChange?: (domain: string) => void;
}

export function GeneralTab({
  instance,
  onPortChange,
  onHttpsChange,
  port,
  httpsEnabled,
  proxyType = 'squid',
  forwardAddress = '',
  coverDomain = '',
  onForwardAddressChange,
  onCoverDomainChange
}: GeneralTabProps) {
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);

  const updateMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      updateInstance(instance.name, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  });

  // Toggle mutations fire immediately on change
  const toggleMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      updateInstance(instance.name, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    }
  });

  const isTlsTunnel = proxyType === 'tls_tunnel';

  const textFieldsDirty =
    port !== instance.port ||
    (isTlsTunnel && forwardAddress !== (instance.forward_address ?? '')) ||
    (isTlsTunnel && coverDomain !== (instance.cover_domain ?? ''));

  const handleSave = () => {
    const payload: Record<string, unknown> = { port };
    if (isTlsTunnel) {
      payload.forward_address = forwardAddress;
      payload.cover_domain = coverDomain;
    }
    updateMutation.mutate(payload);
  };

  const handleHttpsToggle = (checked: boolean) => {
    onHttpsChange(checked);
    toggleMutation.mutate({ https_enabled: checked });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <HATextField
        label="Instance Name"
        value={instance.name}
        disabled
        data-testid="settings-name-input"
      />

      <HATextField
        label={isTlsTunnel ? 'Listen Port' : 'Port'}
        type="number"
        value={String(port)}
        min={1024}
        max={65535}
        onChange={(e) => onPortChange(Number(e.target.value))}
        data-testid="settings-port-input"
      />

      {!isTlsTunnel && (
        <HASwitch
          label="Enable HTTPS (SSL)"
          checked={httpsEnabled}
          onChange={(e) => handleHttpsToggle(e.target.checked)}
          disabled={toggleMutation.isPending}
          data-testid="settings-https-switch"
        />
      )}

      {isTlsTunnel && (
        <>
          <HATextField
            label="VPN Server Address"
            value={forwardAddress}
            onChange={(e) => onForwardAddressChange?.(e.target.value)}
            data-testid="settings-forward-address-input"
          />
          <HATextField
            label="Cover Domain"
            value={coverDomain}
            onChange={(e) => onCoverDomainChange?.(e.target.value)}
            data-testid="settings-cover-domain-input"
          />
        </>
      )}

      <div style={{ display: 'flex', paddingTop: '8px' }}>
        <HAButton
          onClick={handleSave}
          loading={updateMutation.isPending}
          disabled={!textFieldsDirty || updateMutation.isPending}
          data-testid="settings-save-button"
        >
          <HAIcon icon={saved ? 'mdi:check' : 'mdi:content-save'} slot="start" />
          {saved ? 'Saved!' : 'Save Changes'}
        </HAButton>
      </div>
    </div>
  );
}
