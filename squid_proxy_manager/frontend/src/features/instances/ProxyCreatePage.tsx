import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';

import { createInstance, type ProxyType } from '@/api/instances';
import {
  HAButton,
  HACard,
  HAIcon,
  HAIconButton,
  HASwitch,
  HATextField,
  HATopBar
} from '@/ui/ha-wrappers';

const createFormSchema = z.object({
  name: z.string().min(1, 'Instance name is required').regex(/^[a-zA-Z0-9._-]+$/, {
    message: 'Use letters, numbers, dots, hyphens, or underscores'
  }),
  proxy_type: z.enum(['squid', 'tls_tunnel']),
  port: z.number().int().min(1024).max(65535),
  https_enabled: z.boolean(),
  dpi_prevention: z.boolean(),
  users: z.array(z.object({
    username: z.string().min(1),
    password: z.string().min(6)
  })),
  forward_address: z.string().optional(),
  cover_domain: z.string().optional(),
}).refine((data) => {
  if (data.proxy_type === 'tls_tunnel') {
    return !!data.forward_address && data.forward_address.length > 0;
  }
  return true;
}, {
  message: 'VPN Server Address is required for TLS Tunnel',
  path: ['forward_address'],
});

type CreateFormValues = z.infer<typeof createFormSchema>;

interface FormErrors {
  name?: string;
  port?: string;
  forward_address?: string;
}

export function ProxyCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');

  const [formValues, setFormValues] = useState<CreateFormValues>({
    name: '',
    proxy_type: 'squid',
    port: 3128,
    https_enabled: false,
    dpi_prevention: false,
    users: [],
    forward_address: '',
    cover_domain: '',
  });
  const [errors, setErrors] = useState<FormErrors>({});

  const httpsEnabled = formValues.https_enabled;
  const users = formValues.users;
  const isSquid = formValues.proxy_type === 'squid';
  const isTlsTunnel = formValues.proxy_type === 'tls_tunnel';

  const createMutation = useMutation({
    mutationFn: createInstance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      navigate('/');
    }
  });

  const handleProxyTypeChange = (type: ProxyType) => {
    setFormValues((prev) => ({
      ...prev,
      proxy_type: type,
      port: type === 'squid' ? 3128 : 8443,
    }));
    setErrors({});
  };

  const handleCreate = async () => {
    const result = createFormSchema.safeParse(formValues);
    if (!result.success) {
      const fieldErrors: FormErrors = {};
      result.error.issues.forEach((issue) => {
        const field = issue.path[0] as keyof FormErrors;
        if (field) {
          fieldErrors[field] = issue.message;
        }
      });
      setErrors(fieldErrors);
      return;
    }

    setErrors({});
    await createMutation.mutateAsync({
      name: result.data.name,
      proxy_type: result.data.proxy_type,
      port: result.data.port,
      https_enabled: result.data.https_enabled,
      dpi_prevention: result.data.dpi_prevention,
      users: result.data.users,
      forward_address: result.data.forward_address || undefined,
      cover_domain: result.data.cover_domain || undefined,
    });
  };

  const handleAddUser = () => {
    if (newUsername && newPassword && newPassword.length >= 6) {
      setFormValues((prev) => ({
        ...prev,
        users: [...prev.users, { username: newUsername, password: newPassword }]
      }));
      setNewUsername('');
      setNewPassword('');
    }
  };

  const handleRemoveUser = (index: number) => {
    setFormValues((prev) => ({
      ...prev,
      users: prev.users.filter((_, i) => i !== index)
    }));
  };

  return (
    <div style={{ minHeight: '100vh' }}>
      <HATopBar title="New Proxy Instance" onBack={() => navigate('/')} />

      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '16px 16px 32px' }}>
        <div style={{ display: 'grid', gap: '16px' }}>

          {/* Proxy Type Selector */}
          <HACard title="Proxy Type">
            <div style={{ padding: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div
                  data-testid="proxy-type-squid"
                  onClick={() => handleProxyTypeChange('squid')}
                  style={{
                    padding: '16px',
                    borderRadius: '12px',
                    border: `2px solid ${isSquid ? 'var(--primary-color, #03a9f4)' : 'var(--divider-color, rgba(225,225,225,0.12))'}`,
                    backgroundColor: isSquid ? 'rgba(3,169,244,0.08)' : 'transparent',
                    cursor: 'pointer',
                    textAlign: 'center',
                  }}
                >
                  <HAIcon icon="mdi:server-network" style={{ fontSize: '32px', marginBottom: '8px', color: isSquid ? 'var(--primary-color)' : 'var(--secondary-text-color)' }} />
                  <div style={{ fontWeight: 500, fontSize: '14px' }}>Squid Proxy</div>
                  <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)', marginTop: '4px' }}>HTTP/HTTPS forward proxy</div>
                </div>
                <div
                  data-testid="proxy-type-tls-tunnel"
                  onClick={() => handleProxyTypeChange('tls_tunnel')}
                  style={{
                    padding: '16px',
                    borderRadius: '12px',
                    border: `2px solid ${isTlsTunnel ? 'var(--primary-color, #03a9f4)' : 'var(--divider-color, rgba(225,225,225,0.12))'}`,
                    backgroundColor: isTlsTunnel ? 'rgba(3,169,244,0.08)' : 'transparent',
                    cursor: 'pointer',
                    textAlign: 'center',
                  }}
                >
                  <HAIcon icon="mdi:shield-lock-outline" style={{ fontSize: '32px', marginBottom: '8px', color: isTlsTunnel ? 'var(--primary-color)' : 'var(--secondary-text-color)' }} />
                  <div style={{ fontWeight: 500, fontSize: '14px' }}>TLS Tunnel</div>
                  <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)', marginTop: '4px' }}>Stealth VPN tunnel via TLS</div>
                </div>
              </div>
            </div>
          </HACard>

          <HACard title="Instance Details" data-testid="create-instance-form">
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <HATextField
                label="Instance Name"
                value={formValues.name}
                onChange={(e) => setFormValues((prev) => ({ ...prev, name: e.target.value }))}
                helperText="Letters, numbers, dots, hyphens, or underscores"
                data-testid="create-name-input"
              />
              {errors.name && (
                <p style={{ fontSize: '12px', color: 'var(--error-color, #db4437)' }}>{errors.name}</p>
              )}

              <HATextField
                label={isTlsTunnel ? 'Listen Port' : 'Port'}
                type="number"
                value={String(formValues.port)}
                min={1024}
                max={65535}
                onChange={(e) => setFormValues((prev) => ({ ...prev, port: Number(e.target.value) || (isTlsTunnel ? 8443 : 3128) }))}
                helperText={isTlsTunnel ? 'Configure your router to forward external:443 to this port' : undefined}
                data-testid="create-port-input"
              />
              {errors.port && (
                <p style={{ fontSize: '12px', color: 'var(--error-color, #db4437)' }}>{errors.port}</p>
              )}

              {isTlsTunnel && (
                <>
                  <HATextField
                    label="VPN Server Address"
                    value={formValues.forward_address || ''}
                    onChange={(e) => setFormValues((prev) => ({ ...prev, forward_address: e.target.value }))}
                    placeholder="vpn.example.com:1194"
                    data-testid="create-forward-address-input"
                  />
                  {errors.forward_address && (
                    <p style={{ fontSize: '12px', color: 'var(--error-color, #db4437)' }}>{errors.forward_address}</p>
                  )}

                  <HATextField
                    label="Cover Domain"
                    value={formValues.cover_domain || ''}
                    onChange={(e) => setFormValues((prev) => ({ ...prev, cover_domain: e.target.value }))}
                    placeholder="example.com"
                    helperText="Domain for cover website SSL cert. Leave empty for self-signed."
                    data-testid="create-cover-domain-input"
                  />

                  <div style={{
                    padding: '12px 16px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(3,169,244,0.08)',
                    border: '1px solid rgba(3,169,244,0.2)',
                  }}>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                      <HAIcon icon="mdi:information-outline" style={{ color: 'var(--primary-color, #03a9f4)', flexShrink: 0, marginTop: '2px' }} />
                      <p style={{ fontSize: '13px', color: 'var(--primary-text-color)', margin: 0, lineHeight: '1.5' }}>
                        Creates an nginx TLS tunnel on port 443. OpenVPN clients connect with tls-crypt. DPI probes see a normal HTTPS website.
                      </p>
                    </div>
                  </div>
                </>
              )}

              {isSquid && (
                <>
                  <HASwitch
                    label="Enable HTTPS (SSL)"
                    checked={httpsEnabled}
                    onChange={(e) => setFormValues((prev) => ({ ...prev, https_enabled: e.target.checked }))}
                    data-testid="create-https-switch"
                  />

                  <HASwitch
                    label="DPI Prevention"
                    checked={formValues.dpi_prevention}
                    onChange={(e) => setFormValues((prev) => ({ ...prev, dpi_prevention: e.target.checked }))}
                    data-testid="create-dpi-switch"
                  />
                  {formValues.dpi_prevention && (
                    <p style={{ fontSize: '12px', color: 'var(--secondary-text-color, #9b9b9b)', marginTop: '-8px' }}>
                      Strips proxy-identifying headers, hides Squid version, uses modern TLS, and mimics browser connections to avoid DPI detection.
                    </p>
                  )}
                </>
              )}
            </div>
          </HACard>

          {isSquid && (
            <HACard title="Initial Users">
              <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <HATextField
                    label="Username"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    data-testid="create-user-username-input"
                  />
                  <HATextField
                    label="Password"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    helperText="Minimum 6 characters"
                    data-testid="create-user-password-input"
                  />
                  <div style={{ display: 'flex' }}>
                    <HAButton
                      variant="secondary"
                      onClick={handleAddUser}
                      disabled={!newUsername || newPassword.length < 6}
                      data-testid="create-user-add-button"
                    >
                      <HAIcon icon="mdi:account-plus" slot="start" />
                      Add User
                    </HAButton>
                  </div>
                </div>

                {users.length > 0 && (
                  <div style={{ borderTop: '1px solid var(--divider-color, rgba(225,225,225,0.12))', paddingTop: '16px' }}>
                    <p style={{ fontSize: '14px', fontWeight: 500, marginBottom: '8px' }}>Users to create:</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {users.map((user, index) => (
                        <div
                          key={index}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '8px 12px',
                            borderRadius: '8px',
                            backgroundColor: 'var(--secondary-background-color, #282828)',
                          }}
                        >
                          <span style={{ fontSize: '14px' }}>{user.username}</span>
                          <HAIconButton
                            icon="mdi:close"
                            label="Remove"
                            onClick={() => handleRemoveUser(index)}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {users.length === 0 && (
                  <p style={{ fontSize: '14px', color: 'var(--secondary-text-color, #9b9b9b)' }}>
                    No users added yet. You can add users now or configure them later from instance settings.
                  </p>
                )}
              </div>
            </HACard>
          )}

          <div style={{ display: 'flex', gap: '8px', justifyContent: 'space-between', paddingTop: '16px', marginTop: '8px' }}>
            <HAButton variant="ghost" onClick={() => navigate('/')}>
              <HAIcon icon="mdi:arrow-left" slot="start" />
              Cancel
            </HAButton>
            <HAButton
              variant="primary"
              onClick={handleCreate}
              loading={createMutation.isPending}
              data-testid="create-submit-button"
            >
              <HAIcon icon="mdi:plus" slot="start" />
              Create Instance
            </HAButton>
          </div>
        </div>
      </div>
    </div>
  );
}
