import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useMemo, useRef, useState } from 'react';

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
}

// OpenVPN config keywords for syntax highlighting
const OVPN_KEYWORDS = new Set([
  'client', 'dev', 'proto', 'remote', 'resolv-retry', 'nobind',
  'persist-key', 'persist-tun', 'cipher', 'auth', 'verb',
  'tls-crypt', 'tls-auth', 'ca', 'cert', 'key',
  'http-proxy', 'route', 'redirect-gateway', 'keepalive',
  'comp-lzo', 'remote-cert-tls', 'pull', 'tun-mtu', 'float',
  'http-proxy-option', 'http-proxy-retry', 'tls-timeout',
  'connect-retry-max', 'server', 'ifconfig', 'push',
  'topology', 'sndbuf', 'rcvbuf', 'mssfix',
]);

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/** Compute which line indices in `patched` are new (not in `original`) using LCS. */
function computeAddedLines(original: string, patched: string): Set<number> {
  const origLines = original.split('\n');
  const patchLines = patched.split('\n');
  const m = origLines.length;
  const n = patchLines.length;

  // LCS dynamic programming
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array<number>(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (origLines[i - 1] === patchLines[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to find added lines in patched
  const added = new Set<number>();
  let i = m;
  let j = n;
  while (i > 0 && j > 0) {
    if (origLines[i - 1] === patchLines[j - 1]) {
      i--;
      j--;
    } else if (dp[i - 1][j] > dp[i][j - 1]) {
      i--; // removed from original
    } else {
      added.add(j - 1); // added in patched
      j--;
    }
  }
  while (j > 0) {
    added.add(j - 1);
    j--;
  }

  return added;
}

function highlightOvpn(text: string, addedLines?: Set<number>): string {
  return text
    .split('\n')
    .map((line, idx) => {
      let highlighted: string;

      // Comment lines
      if (line.trimStart().startsWith('#') || line.trimStart().startsWith(';')) {
        highlighted = `<span class="ovpn-comment">${escapeHtml(line)}</span>`;
      // Inline tags like <ca>, </ca>, <cert>, etc.
      } else if (/^\s*<\/?[a-zA-Z-]+>\s*$/.test(line)) {
        highlighted = `<span class="ovpn-keyword">${escapeHtml(line)}</span>`;
      } else {
        // Tokenize the line
        highlighted = line.replace(
          /("(?:[^"\\]|\\.)*")|('(?:[^'\\]|\\.)*')|(\b\d+\b)|([a-zA-Z][a-zA-Z0-9_-]*)/g,
          (match, doubleStr, singleStr, num, word) => {
            if (doubleStr || singleStr) {
              return `<span class="ovpn-string">${escapeHtml(match)}</span>`;
            }
            if (num) {
              return `<span class="ovpn-number">${escapeHtml(match)}</span>`;
            }
            if (word && OVPN_KEYWORDS.has(word)) {
              return `<span class="ovpn-keyword">${escapeHtml(match)}</span>`;
            }
            return escapeHtml(match);
          }
        );
      }

      // Wrap with diff background if this line was added/changed
      if (addedLines?.has(idx)) {
        const isRemovedDirective = line.includes('# removed for');
        const cls = isRemovedDirective ? 'ovpn-diff-removed' : 'ovpn-diff-added';
        highlighted = `<span class="${cls}">${highlighted}</span>`;
      }

      return highlighted;
    })
    .join('\n');
}

export function OpenVPNPatcherDialog({
  isOpen,
  onClose,
  instanceName,
  proxyType,
}: OpenVPNPatcherDialogProps) {
  const queryClient = useQueryClient();
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [patchedContent, setPatchedContent] = useState<string | null>(null);
  const [selectedUsername, setSelectedUsername] = useState('');
  const [manualPassword, setManualPassword] = useState('');
  const [includeAuth, setIncludeAuth] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [copySuccess, setCopySuccess] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [extractedVpnServer, setExtractedVpnServer] = useState<string | null>(null);
  const [externalAddress, setExternalAddress] = useState('');
  const [downloadFilename, setDownloadFilename] = useState(`${instanceName}_patched.ovpn`);
  const [originalContent, setOriginalContent] = useState<string | null>(null);
  const preRef = useRef<HTMLPreElement>(null);

  // Compute diff between original and patched content
  const addedLines = useMemo(() => {
    if (!originalContent || !patchedContent) return undefined;
    return computeAddedLines(originalContent, patchedContent);
  }, [originalContent, patchedContent]);

  // Read file text for diff comparison
  const readFileForDiff = (file: File) => {
    const reader = new FileReader();
    reader.onload = (ev) => {
      setOriginalContent(ev.target?.result as string);
    };
    reader.readAsText(file);
  };

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
      if (externalAddress) payload.external_host = externalAddress;

      // For Squid, include auth if enabled
      if (proxyType === 'squid' && includeAuth && selectedUsername && manualPassword) {
        payload.username = selectedUsername;
        payload.password = manualPassword;
      }

      return patchOVPNConfig(instanceName, payload);
    },
    onSuccess: (data: { patched_content: string; vpn_server?: string }) => {
      setPatchedContent(data.patched_content);
      setFileError(null);
      setApiError(null);

      // For TLS tunnel, show extracted VPN server and invalidate instances query
      if (proxyType === 'tls_tunnel' && data.vpn_server) {
        setExtractedVpnServer(data.vpn_server);
        queryClient.invalidateQueries({ queryKey: ['instances'] });
      }
    },
    onError: (error: Error) => {
      setApiError(error.message || 'Failed to patch config');
      setPatchedContent(null);
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.name.endsWith('.ovpn')) {
        setUploadedFile(file);
        setPatchedContent(null); // Reset preview
        setFileError(null);
        readFileForDiff(file);
      } else {
        setFileError('Please select a valid .ovpn file');
        setUploadedFile(null);
      }
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      if (file.name.endsWith('.ovpn')) {
        setUploadedFile(file);
        setPatchedContent(null);
        setFileError(null);
        readFileForDiff(file);
      } else {
        setFileError('Please select a valid .ovpn file');
        setUploadedFile(null);
      }
    }
  };

  const handleDownload = () => {
    if (!patchedContent) return;

    const blob = new Blob([patchedContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = downloadFilename || `${instanceName}_patched.ovpn`;
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
    setExtractedVpnServer(null);
    setExternalAddress('');
    setDownloadFilename(`${instanceName}_patched.ovpn`);
    setOriginalContent(null);
    // Reset mutation state to clear any previous errors
    patchMutation.reset();
    onClose();
  };

  const handleScroll = useCallback((e: React.UIEvent<HTMLTextAreaElement>) => {
    const target = e.currentTarget;
    if (preRef.current) {
      preRef.current.scrollTop = target.scrollTop;
      preRef.current.scrollLeft = target.scrollLeft;
    }
  }, []);

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
        {/* Syntax highlighting styles */}
        <style>{`
          .ovpn-keyword { color: var(--primary-color, #03a9f4); }
          .ovpn-comment { color: var(--secondary-text-color, #9b9b9b); font-style: italic; }
          .ovpn-string { color: var(--success-color, #4caf50); }
          .ovpn-number { color: var(--warning-color, #ff9800); }
          .ovpn-diff-added { background: rgba(76, 175, 80, 0.18); }
          .ovpn-diff-removed { background: rgba(219, 68, 55, 0.18); text-decoration: line-through; }
        `}</style>

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

        {/* External Address Input */}
        <HATextField
          label="External Address"
          value={externalAddress}
          onChange={(e) => setExternalAddress(e.target.value)}
          placeholder="proxy.example.com or proxy.example.com:4443"
          helperText="Your server's public IP or hostname. Include :port if different from listen port."
          data-testid="openvpn-external-address-input"
        />

        {/* External Address Warning/Error (conditional) */}
        {!externalAddress && proxyType === 'tls_tunnel' && (
          <HACard outlined style={{ borderLeft: '4px solid var(--error-color)' }} data-testid="openvpn-external-ip-error">
            <div style={{ padding: '12px', display: 'flex', gap: '12px' }}>
              <HAIcon icon="mdi:alert-circle" style={{ flexShrink: 0, color: 'var(--error-color)' }} />
              <div style={{ fontSize: '14px' }}>
                <p style={{ margin: 0, color: 'var(--error-color)' }}>
                  External address is required for TLS tunnel. Without it, the patched config will contain &quot;localhost&quot; which won&apos;t work for clients connecting to this tunnel.
                </p>
              </div>
            </div>
          </HACard>
        )}
        {!externalAddress && proxyType === 'squid' && (
          <HACard outlined style={{ borderLeft: '4px solid var(--warning-color)' }}>
            <div style={{ padding: '12px', display: 'flex', gap: '12px' }}>
              <HAIcon icon="mdi:alert" style={{ flexShrink: 0 }} />
              <div style={{ fontSize: '14px' }}>
                <p style={{ margin: 0 }}>
                  External address not set. Config will use &quot;localhost&quot; which only works for local testing.
                </p>
              </div>
            </div>
          </HACard>
        )}

        {/* Upload Section */}
        <HACard header="Upload OpenVPN Config">
          <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <input
              id="openvpn-file-upload"
              type="file"
              accept=".ovpn"
              onChange={handleFileChange}
              style={{ display: 'none' }}
              data-testid="openvpn-file-input"
            />

            {/* Drag and drop zone */}
            <label
              htmlFor="openvpn-file-upload"
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              data-testid="openvpn-drop-zone"
              style={{
                display: 'block',
                border: isDragging
                  ? '2px dashed var(--primary-color)'
                  : '2px dashed var(--divider-color)',
                borderRadius: '8px',
                padding: '24px',
                textAlign: 'center',
                cursor: 'pointer',
                backgroundColor: isDragging
                  ? 'var(--primary-color-opacity-10)'
                  : 'var(--card-background-color)',
                transition: 'all 0.2s ease',
              }}
            >
              <HAIcon
                icon="mdi:cloud-upload"
                style={{ fontSize: '48px', color: 'var(--secondary-text-color)' }}
              />
              <p style={{ margin: '8px 0 4px 0', fontSize: '16px', fontWeight: 500 }}>
                {uploadedFile ? uploadedFile.name : 'Drop .ovpn file here or click to browse'}
              </p>
              <p style={{ margin: 0, fontSize: '14px', color: 'var(--secondary-text-color)' }}>
                {uploadedFile
                  ? `${(uploadedFile.size / 1024).toFixed(1)} KB`
                  : 'Supports OpenVPN config files (.ovpn)'}
              </p>
            </label>

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
            disabled={!uploadedFile || patchMutation.isPending || (proxyType === 'tls_tunnel' && !externalAddress)}
            loading={patchMutation.isPending}
            data-testid="openvpn-patch-button"
          >
            <HAIcon icon="mdi:file-edit" slot="start" />
            {proxyType === 'squid' ? 'Patch Config' : 'Extract & Patch'}
          </HAButton>
        </div>

        {/* VPN Server Extraction Success (TLS Tunnel only) */}
        {extractedVpnServer && proxyType === 'tls_tunnel' && (
          <HACard outlined style={{ borderLeft: '4px solid var(--success-color)' }}>
            <div style={{ padding: '12px', display: 'flex', gap: '12px' }}>
              <HAIcon icon="mdi:check-circle" style={{ flexShrink: 0, color: 'var(--success-color)' }} />
              <div style={{ fontSize: '14px' }}>
                <p style={{ margin: '0 0 4px 0', fontWeight: 500 }}>
                  VPN Server Extracted Successfully
                </p>
                <p style={{ margin: 0, color: 'var(--secondary-text-color)' }}>
                  Destination updated to: <strong>{extractedVpnServer}</strong>
                </p>
              </div>
            </div>
          </HACard>
        )}

        {/* Preview Section (after patch) - editable with syntax highlighting */}
        {patchedContent && (
          <HACard header="Patched Config Preview">
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{
                position: 'relative',
                minHeight: '300px',
                border: '1px solid var(--divider-color)',
                borderRadius: '8px',
                overflow: 'hidden',
                backgroundColor: 'var(--secondary-background-color)',
              }}>
                {/* Highlighted pre behind textarea */}
                <pre
                  ref={preRef}
                  aria-hidden
                  data-testid="openvpn-preview-highlight"
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    margin: 0,
                    padding: '12px',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    lineHeight: '1.5',
                    whiteSpace: 'pre',
                    overflow: 'hidden',
                    pointerEvents: 'none',
                    color: 'var(--primary-text-color)',
                  }}
                  dangerouslySetInnerHTML={{ __html: highlightOvpn(patchedContent, addedLines) }}
                />

                {/* Transparent editable textarea on top */}
                <textarea
                  value={patchedContent}
                  onChange={(e) => setPatchedContent(e.target.value)}
                  onScroll={handleScroll}
                  spellCheck={false}
                  style={{
                    position: 'relative',
                    width: '100%',
                    minHeight: '300px',
                    height: '100%',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    padding: '12px',
                    border: 'none',
                    backgroundColor: 'transparent',
                    color: 'transparent',
                    caretColor: 'var(--primary-text-color)',
                    resize: 'vertical',
                    lineHeight: '1.5',
                    outline: 'none',
                    whiteSpace: 'pre',
                    overflow: 'auto',
                  }}
                  data-testid="openvpn-preview"
                />
              </div>

              <HATextField
                label="Download Filename"
                value={downloadFilename}
                onChange={(e) => setDownloadFilename(e.target.value)}
                placeholder={`${instanceName}_patched.ovpn`}
                data-testid="openvpn-download-filename"
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
