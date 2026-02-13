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
import { MermaidDiagram } from '@/ui/MermaidDiagram';

const createFormSchema = z.object({
  name: z.string().min(1, 'Instance name is required').regex(/^[a-zA-Z0-9._-]+$/, {
    message: 'Use letters, numbers, dots, hyphens, or underscores'
  }),
  proxy_type: z.enum(['squid', 'tls_tunnel']),
  port: z.number().int().min(1024).max(65535),
  https_enabled: z.boolean(),
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
  message: 'VPN Server Destination is required for TLS Tunnel',
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
    },
    onError: (error: any) => {
      // Show backend error to user
      const errorMessage = error?.message || 'Unknown error occurred';
      alert(`Failed to create instance:\n\n${errorMessage}`);
      // Scroll to top to show any field-specific errors
      window.scrollTo({ top: 0, behavior: 'smooth' });
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

      // Scroll to top to show validation errors
      window.scrollTo({ top: 0, behavior: 'smooth' });

      // Show alert on mobile to ensure user sees validation errors
      if (window.innerWidth < 768) {
        const errorMessages = Object.entries(fieldErrors)
          .map(([field, message]) => `${field}: ${message}`)
          .join('\n');
        alert(`Please fix the following errors:\n\n${errorMessages}`);
      }
      return;
    }

    setErrors({});
    await createMutation.mutateAsync({
      name: result.data.name,
      proxy_type: result.data.proxy_type,
      port: result.data.port,
      https_enabled: result.data.https_enabled,
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
                  <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)', marginTop: '4px' }}>HTTP/HTTPS forward proxy with user authentication, access logging, and encrypted connections</div>
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
                  <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)', marginTop: '4px' }}>Stealth VPN relay that defeats DPI censorship by disguising traffic as a normal HTTPS website</div>
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
                value={formValues.port === 0 ? '' : String(formValues.port)}
                onChange={(e) => {
                  const val = e.target.value;
                  setFormValues((prev) => ({
                    ...prev,
                    port: val === '' ? 0 : Number(val)
                  }));
                }}
                helperText={isTlsTunnel ? 'Port 1024-65535 (configure router to forward 443 to this port)' : 'Port 1024-65535'}
                data-testid="create-port-input"
              />
              {errors.port && (
                <p style={{ fontSize: '12px', color: 'var(--error-color, #db4437)' }}>{errors.port}</p>
              )}

              {isTlsTunnel && (
                <>
                  <HATextField
                    label="VPN Server Destination"
                    value={formValues.forward_address || ''}
                    onChange={(e) => setFormValues((prev) => ({ ...prev, forward_address: e.target.value }))}
                    placeholder="vpn.example.com:1194"
                    helperText="Your VPN server address (host:port) where OpenVPN traffic will be forwarded"
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
                    helperText="Domain shown to DPI probes. Leave empty for self-signed certificate."
                    data-testid="create-cover-domain-input"
                  />

                  <div style={{
                    padding: '16px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(3,169,244,0.08)',
                    border: '1px solid rgba(3,169,244,0.2)',
                  }}>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start', marginBottom: '16px' }}>
                      <HAIcon icon="mdi:information-outline" style={{ color: 'var(--primary-color, #03a9f4)', flexShrink: 0, marginTop: '2px' }} />
                      <div style={{ fontSize: '13px', color: 'var(--primary-text-color)', lineHeight: '1.5' }}>
                        <strong>How TLS Tunnel Works:</strong>
                      </div>
                    </div>

                    <MermaidDiagram chart={`
graph TD
    A["OpenVPN Client"] -->|TLS w/tls-crypt| B["TLS Tunnel<br/>(nginx:443)"]
    B --> C{Traffic Routing}
    C -->|Has tls-crypt header| D["VPN Server<br/>(OpenVPN)"]
    C -->|No tls-crypt header<br/>DPI Scanner| E["Cover Website<br/>(nginx default)"]

    style A fill:#03a9f4,stroke:#03a9f4,stroke-width:2px,color:#fff
    style B fill:#4caf50,stroke:#4caf50,stroke-width:2px,color:#fff
    style C fill:#ff9800,stroke:#ff9800,stroke-width:2px,color:#fff
    style D fill:#43a047,stroke:#43a047,stroke-width:2px,color:#fff
    style E fill:#9e9e9e,stroke:#9e9e9e,stroke-width:2px,color:#fff
                    `} />

                    <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)', lineHeight: '1.5', marginTop: '12px' }}>
                      The tunnel listens on port 443 and intelligently routes traffic. OpenVPN clients using tls-crypt are forwarded to your VPN server,
                      while DPI scanners see only a legitimate HTTPS website.
                    </div>
                  </div>
                </>
              )}

              {isSquid && (
                <HASwitch
                  label="Enable HTTPS (SSL)"
                  checked={httpsEnabled}
                  onChange={(e) => setFormValues((prev) => ({ ...prev, https_enabled: e.target.checked }))}
                  data-testid="create-https-switch"
                />
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

          <div style={{
            display: 'flex',
            gap: '12px',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingTop: '16px',
            marginTop: '8px',
            flexWrap: 'wrap',
          }}>
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
              Create Instance
            </HAButton>
          </div>
        </div>
      </div>
    </div>
  );
}
