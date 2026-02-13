import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { getUsers, patchOVPNConfig } from '@/api/instances';
import { HAButton, HACard, HAIcon, HASelect, HATextField } from '@/ui/ha-wrappers';

interface OpenVPNTabProps {
  instanceName: string;
  proxyType: 'squid' | 'tls_tunnel';
  port: number;
  externalIp?: string;
}

export function OpenVPNTab({ instanceName, proxyType, port, externalIp }: OpenVPNTabProps) {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [patchedContent, setPatchedContent] = useState<string | null>(null);
  const [selectedUsername, setSelectedUsername] = useState('');
  const [manualPassword, setManualPassword] = useState('');
  const [includeAuth, setIncludeAuth] = useState(false);

  // Fetch users for Squid instances
  const usersQuery = useQuery({
    queryKey: ['users', instanceName],
    queryFn: () => getUsers(instanceName),
    enabled: proxyType === 'squid',
  });

  const patchMutation = useMutation({
    mutationFn: async () => {
      if (!uploadedFile) throw new Error('No file selected');

      const payload: {
        file: File;
        external_host?: string;
        username?: string;
        password?: string;
      } = { file: uploadedFile };
      if (externalIp) payload.external_host = externalIp;

      // For Squid, include auth if enabled
      if (proxyType === 'squid' && includeAuth && selectedUsername && manualPassword) {
        payload.username = selectedUsername;
        payload.password = manualPassword;
      }

      return patchOVPNConfig(instanceName, payload);
    },
    onSuccess: (data) => {
      setPatchedContent(data.patched_content);
    },
    onError: (error: Error) => {
      alert(`Failed to patch config: ${error.message || 'Unknown error'}`);
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.name.endsWith('.ovpn')) {
      setUploadedFile(file);
      setPatchedContent(null); // Reset preview
    } else {
      alert('Please select a valid .ovpn file');
    }
  };

  const handleDownload = () => {
    if (!patchedContent) return;

    const blob = new Blob([patchedContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${instanceName}_patched.ovpn`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopy = () => {
    if (!patchedContent) return;
    navigator.clipboard.writeText(patchedContent);
    alert('Copied to clipboard!');
  };

  const users = usersQuery.data?.users ?? [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '16px' }}>
      {/* Info Section */}
      <HACard title="How It Works">
        <div style={{ padding: '16px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              fontSize: '14px',
              lineHeight: '1.5',
            }}
          >
            <HAIcon
              icon="mdi:information"
              style={{ fontSize: '20px', flexShrink: 0, marginTop: '2px' }}
            />
            <div>
              {proxyType === 'squid' ? (
                <p>
                  Upload your OpenVPN config file (.ovpn) and we'll automatically add HTTP proxy
                  directives to route VPN traffic through this Squid proxy instance.
                </p>
              ) : (
                <p>
                  Upload your OpenVPN config file (.ovpn) and we'll extract your VPN server
                  address, update this instance's settings, and replace it with this TLS tunnel
                  endpoint to bypass DPI censorship.
                </p>
              )}
            </div>
          </div>
        </div>
      </HACard>

      {/* External IP Warning */}
      {!externalIp && (
        <HACard
          title="External IP Not Set"
          outlined
          style={{ borderLeft: '4px solid var(--warning-color, #ff9800)' }}
        >
          <div
            style={{
              padding: '16px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
            }}
          >
            <HAIcon
              icon="mdi:alert"
              style={{
                fontSize: '20px',
                flexShrink: 0,
                color: 'var(--warning-color, #ff9800)',
                marginTop: '2px',
              }}
            />
            <div style={{ fontSize: '14px', lineHeight: '1.5' }}>
              <p style={{ marginBottom: '8px' }}>
                You haven't configured an external IP/hostname for this instance. The patched
                config will use "localhost" which only works for local testing.
              </p>
              <p style={{ fontWeight: 500 }}>
                Action: Go to the General tab and set your external IP or hostname.
              </p>
            </div>
          </div>
        </HACard>
      )}

      {/* File Upload Section */}
      <HACard title="1. Upload OpenVPN Config">
        <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <input
              type="file"
              accept=".ovpn"
              onChange={handleFileChange}
              style={{
                fontSize: '14px',
                padding: '8px',
                width: '100%',
                cursor: 'pointer',
              }}
              data-testid="openvpn-file-input"
            />
          </div>
          {uploadedFile && (
            <div
              style={{
                fontSize: '12px',
                color: 'var(--secondary-text-color)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <HAIcon icon="mdi:file-check" style={{ fontSize: '16px' }} />
              Selected: {uploadedFile.name} ({(uploadedFile.size / 1024).toFixed(1)} KB)
            </div>
          )}
        </div>
      </HACard>

      {/* Auth Section (Squid only) */}
      {proxyType === 'squid' && (
        <HACard title="2. Authentication (Optional)">
          <div
            style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}
          >
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                fontSize: '14px',
              }}
            >
              <input
                type="checkbox"
                checked={includeAuth}
                onChange={(e) => setIncludeAuth(e.target.checked)}
                data-testid="openvpn-auth-checkbox"
              />
              Include authentication in patched config
            </label>

            {includeAuth && (
              <>
                {users && users.length > 0 && (
                  <HASelect
                    label="Select User"
                    value={selectedUsername}
                    options={[
                      { value: '', label: '-- Select a user --' },
                      ...users.map((u) => ({ value: u.username, label: u.username })),
                    ]}
                    onChange={(value) => setSelectedUsername(value)}
                    data-testid="openvpn-user-select"
                  />
                )}

                <HATextField
                  label="Username"
                  value={selectedUsername}
                  onChange={(e) => setSelectedUsername(e.target.value)}
                  helperText="Enter username for proxy authentication"
                  data-testid="openvpn-username-input"
                />

                <HATextField
                  label="Password"
                  type="password"
                  value={manualPassword}
                  onChange={(e) => setManualPassword(e.target.value)}
                  helperText="Credentials will be embedded directly in the .ovpn file"
                  data-testid="openvpn-password-input"
                />
              </>
            )}
          </div>
        </HACard>
      )}

      {/* Patch Button */}
      <div style={{ display: 'flex', gap: '12px' }}>
        <HAButton
          variant="primary"
          onClick={() => patchMutation.mutate()}
          disabled={!uploadedFile || patchMutation.isPending}
          loading={patchMutation.isPending}
          data-testid="openvpn-patch-button"
        >
          <HAIcon icon="mdi:file-edit" slot="start" />
          {proxyType === 'squid' ? 'Patch Config' : 'Extract & Patch Config'}
        </HAButton>
      </div>

      {/* Preview Section */}
      {patchedContent && (
        <HACard title="3. Patched Config Preview">
          <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <textarea
              readOnly
              value={patchedContent}
              style={{
                width: '100%',
                height: '300px',
                fontFamily: 'monospace',
                fontSize: '12px',
                padding: '12px',
                border: '1px solid var(--divider-color)',
                borderRadius: '8px',
                backgroundColor: 'var(--secondary-background-color)',
                color: 'var(--primary-text-color)',
                resize: 'vertical',
              }}
              data-testid="openvpn-preview"
            />

            <div style={{ display: 'flex', gap: '12px' }}>
              <HAButton variant="primary" onClick={handleDownload} data-testid="openvpn-download">
                <HAIcon icon="mdi:download" slot="start" />
                Download Patched Config
              </HAButton>
              <HAButton variant="secondary" onClick={handleCopy} data-testid="openvpn-copy">
                <HAIcon icon="mdi:content-copy" slot="start" />
                Copy to Clipboard
              </HAButton>
            </div>
          </div>
        </HACard>
      )}
    </div>
  );
}
