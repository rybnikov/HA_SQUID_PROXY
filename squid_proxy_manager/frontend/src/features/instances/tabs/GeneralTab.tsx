import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { updateInstance, type ProxyInstance } from '@/api/instances';
import { HAButton, HAIcon, HASwitch, HATextField } from '@/ui/ha-wrappers';
import { updateInstanceSchema } from '../validation';

interface GeneralTabProps {
  instance: ProxyInstance;
  onPortChange: (port: number) => void;
  onHttpsChange: (enabled: boolean) => void;
  port: number;
  httpsEnabled: boolean;
  proxyType?: string;
  forwardAddress?: string;
  coverDomain?: string;
  externalIp?: string;
  onForwardAddressChange?: (addr: string) => void;
  onCoverDomainChange?: (domain: string) => void;
  onExternalIpChange?: (ip: string) => void;
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
  externalIp = '',
  onForwardAddressChange,
  onCoverDomainChange,
  onExternalIpChange
}: GeneralTabProps) {
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [errors, setErrors] = useState<{ port?: string; forward_address?: string; cover_domain?: string; external_ip?: string }>({});

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
    (isTlsTunnel && coverDomain !== (instance.cover_domain ?? '')) ||
    externalIp !== (instance.external_ip ?? '');

  const handleSave = () => {
    const payload: Record<string, unknown> = { port, external_ip: externalIp };
    if (isTlsTunnel) {
      payload.forward_address = forwardAddress;
      payload.cover_domain = coverDomain;
    }

    // Validate payload
    const result = updateInstanceSchema.safeParse(payload);
    if (!result.success) {
      const fieldErrors: typeof errors = {};
      result.error.issues.forEach((issue) => {
        const field = issue.path[0] as keyof typeof errors;
        if (field) {
          fieldErrors[field] = issue.message;
        }
      });
      setErrors(fieldErrors);
      return;
    }

    setErrors({});
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
      {errors.port && (
        <p style={{ fontSize: '12px', color: 'var(--error-color, #db4437)', marginTop: '-8px' }}>
          {errors.port}
        </p>
      )}

      <HATextField
        label="External IP / Hostname"
        value={externalIp}
        onChange={(e) => onExternalIpChange?.(e.target.value)}
        placeholder="proxy.example.com or 192.168.1.100"
        helperText="External address for OpenVPN config patching (optional)"
        data-testid="settings-external-ip-input"
      />
      {errors.external_ip && (
        <p style={{ fontSize: '12px', color: 'var(--error-color, #db4437)', marginTop: '-8px' }}>
          {errors.external_ip}
        </p>
      )}

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
            label="VPN Server Destination"
            value={forwardAddress}
            onChange={(e) => onForwardAddressChange?.(e.target.value)}
            placeholder="vpn.example.com:1194"
            helperText="Format: hostname or hostname:port (defaults to :443 if omitted)"
            data-testid="settings-forward-address-input"
          />
          {errors.forward_address && (
            <p style={{ fontSize: '12px', color: 'var(--error-color, #db4437)', marginTop: '-8px' }}>
              {errors.forward_address}
            </p>
          )}
          <HATextField
            label="Cover Domain"
            value={coverDomain}
            onChange={(e) => onCoverDomainChange?.(e.target.value)}
            placeholder="example.com"
            helperText="Domain for SSL certificate (optional)"
            data-testid="settings-cover-domain-input"
          />
          {errors.cover_domain && (
            <p style={{ fontSize: '12px', color: 'var(--error-color, #db4437)', marginTop: '-8px' }}>
              {errors.cover_domain}
            </p>
          )}
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
