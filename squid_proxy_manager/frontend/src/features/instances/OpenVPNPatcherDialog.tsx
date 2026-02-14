import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { getUsers, patchOVPNConfig } from '@/api/instances';
import { HAButton, HACard, HADialog, HAIcon, HASelect, HASwitch, HATextField } from '@/ui/ha-wrappers';

interface User {
  username: string;
}

interface OpenVPNPatcherDialogProps {
  isOpen: boolean;
  onClose: () => void;
  instanceName: string;
  proxyType: 'squid' | 'tls_tunnel';
  port: number;
  externalIp?: string;
}

export function OpenVPNPatcherDialog({
  isOpen,
  onClose,
  instanceName,
  proxyType,
  externalIp,
}: OpenVPNPatcherDialogProps) {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [patchedContent, setPatchedContent] = useState<string | null>(null);
  const [selectedUsername, setSelectedUsername] = useState('');
  const [manualPassword, setManualPassword] = useState('');
  const [includeAuth, setIncludeAuth] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [copySuccess, setCopySuccess] = useState(false);

  // Fetch users for Squid instances
  const usersQuery = useQuery({
    queryKey: ['users', instanceName],
    queryFn: () => getUsers(instanceName),
    enabled: proxyType === 'squid' && isOpen,
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
    onSuccess: (data: { patched_content: string }) => {
      setPatchedContent(data.patched_content);
      setFileError(null);
      setApiError(null);
    },
    onError: (error: Error) => {
      setApiError(error.message || 'Failed to patch config');
      setPatchedContent(null);
    },
  });

  const handleFileChange = (e: { target: HTMLInputElement }) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.name.endsWith('.ovpn')) {
        setUploadedFile(file);
        setPatchedContent(null); // Reset preview
        setFileError(null);
      } else {
        setFileError('Please select a valid .ovpn file');
        setUploadedFile(null);
      }
    }
  };

  const triggerFileInput = () => {
    document.getElementById('openvpn-file-input-hidden')?.click();
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
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 3000);
  };

  const handleClose = () => {
    // Reset state on close
    setUploadedFile(null);
    setPatchedContent(null);
    setFileError(null);
    setApiError(null);
    setCopySuccess(false);
    setSelectedUsername('');
    setManualPassword('');
    setIncludeAuth(false);
    onClose();
  };

  const users: User[] = usersQuery.data?.users ?? [];

  return (
    <HADialog
      id="openvpn-patcher-dialog"
      title="OpenVPN Config Patcher"
      isOpen={isOpen}
      onClose={handleClose}
      maxWidth="700px"
      data-testid="openvpn-dialog"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '16px' }}>
        {/* Info Card */}
        <HACard outlined>
          <div style={{ padding: '12px', display: 'flex', gap: '12px' }}>
            <HAIcon icon="mdi:information" style={{ flexShrink: 0 }} />
            <p style={{ fontSize: '14px', color: 'var(--secondary-text-color)', margin: 0 }}>
              {proxyType === 'squid'
                ? 'Upload your OpenVPN config file (.ovpn) and we will automatically add HTTP proxy directives to route VPN traffic through this Squid proxy instance.'
                : 'Upload your OpenVPN config file (.ovpn) and we will extract your VPN server address, update this instance settings, and replace it with this TLS tunnel endpoint to bypass DPI censorship.'}
            </p>
          </div>
        </HACard>

        {/* External IP Warning (conditional) */}
        {!externalIp && (
          <HACard outlined style={{ borderLeft: '4px solid var(--warning-color)' }}>
            <div style={{ padding: '12px', display: 'flex', gap: '12px' }}>
              <HAIcon icon="mdi:alert" style={{ flexShrink: 0 }} />
              <div style={{ fontSize: '14px' }}>
                <p style={{ margin: '0 0 8px 0' }}>
                  External IP not set. Config will use &quot;localhost&quot; which only works for local testing.
                </p>
                <p style={{ fontWeight: 500, margin: 0 }}>
                  Action: Set external IP in General settings.
                </p>
              </div>
            </div>
          </HACard>
        )}

        {/* Upload Section */}
        <HACard header="Upload OpenVPN Config">
          <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <input
              id="openvpn-file-input-hidden"
              type="file"
              accept=".ovpn"
              onChange={handleFileChange}
              style={{ display: 'none' }}
              data-testid="openvpn-file-input"
            />
            <HAButton
              variant="secondary"
              onClick={triggerFileInput}
              data-testid="openvpn-file-select-button"
            >
              <HAIcon icon="mdi:file-upload" slot="start" />
              {uploadedFile ? 'Change File' : 'Select .ovpn File'}
            </HAButton>

            {uploadedFile && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '14px',
                  color: 'var(--secondary-text-color)',
                }}
              >
                <HAIcon icon="mdi:file-check" />
                <span>
                  {uploadedFile.name} ({(uploadedFile.size / 1024).toFixed(1)} KB)
                </span>
              </div>
            )}

            {fileError && (
              <p style={{ fontSize: '14px', color: 'var(--error-color)', margin: 0 }}>
                {fileError}
              </p>
            )}
          </div>
        </HACard>

        {/* Auth Section (Squid only) */}
        {proxyType === 'squid' && (
          <HACard header="Authentication (Optional)">
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <HASwitch
                  label="Include authentication"
                  checked={includeAuth}
                  onChange={(e) => setIncludeAuth(e.target.checked)}
                  data-testid="openvpn-auth-toggle"
                />
              </div>

              {includeAuth && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {users.length > 0 && (
                    <HASelect
                      label="Select User"
                      value={selectedUsername}
                      options={[
                        { value: '', label: '-- Select user --' },
                        ...users.map((u: User) => ({ value: u.username, label: u.username })),
                      ]}
                      onChange={(value) => setSelectedUsername(value)}
                      data-testid="openvpn-user-select"
                    />
                  )}

                  <HATextField
                    label="Username"
                    value={selectedUsername}
                    onChange={(e) => setSelectedUsername(e.target.value)}
                    helperText="Credentials will be embedded in .ovpn file"
                    data-testid="openvpn-username-input"
                  />

                  <HATextField
                    label="Password"
                    type="password"
                    value={manualPassword}
                    onChange={(e) => setManualPassword(e.target.value)}
                    data-testid="openvpn-password-input"
                  />
                </div>
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
            {proxyType === 'squid' ? 'Patch Config' : 'Extract & Patch'}
          </HAButton>
        </div>

        {/* Preview Section (after patch) */}
        {patchedContent && (
          <HACard header="Patched Config Preview">
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
                  Download
                </HAButton>
                <HAButton variant="secondary" onClick={handleCopy} data-testid="openvpn-copy">
                  <HAIcon icon="mdi:content-copy" slot="start" />
                  Copy
                </HAButton>
              </div>

              {copySuccess && (
                <p style={{ fontSize: '14px', color: 'var(--success-color)', margin: 0 }}>
                  ✓ Copied to clipboard
                </p>
              )}
            </div>
          </HACard>
        )}

        {/* Error state for patch mutation */}
        {patchMutation.isError && (
          <HACard
            outlined
            style={{ borderLeft: '4px solid var(--error-color)' }}
            data-testid="error-card"
          >
            <div style={{ padding: '12px', display: 'flex', gap: '12px' }}>
              <HAIcon icon="mdi:alert-circle" style={{ flexShrink: 0 }} />
              <p style={{ fontSize: '14px', color: 'var(--error-color)', margin: 0 }}>
                {apiError || 'Failed to patch config'}
              </p>
            </div>
          </HACard>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          gap: '12px',
          justifyContent: 'flex-end',
          padding: '16px',
          borderTop: '1px solid var(--divider-color)',
        }}
      >
        <HAButton variant="secondary" onClick={handleClose} data-testid="openvpn-dialog-close">
          Close
        </HAButton>
      </div>
    </HADialog>
  );
}
