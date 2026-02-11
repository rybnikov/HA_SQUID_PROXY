import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { getOvpnSnippet } from '@/api/instances';
import { HAButton, HAIcon } from '@/ui/ha-wrappers';

interface ConnectionInfoTabProps {
  instanceName: string;
  port: number;
  forwardAddress: string;
}

export function ConnectionInfoTab({ instanceName, port, forwardAddress }: ConnectionInfoTabProps) {
  const [copied, setCopied] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const snippetQuery = useQuery({
    queryKey: ['ovpn-snippet', instanceName],
    queryFn: () => getOvpnSnippet(instanceName),
  });

  const handleCopy = () => {
    if (snippetQuery.data) {
      navigator.clipboard.writeText(snippetQuery.data);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* DPI Evasion Level */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '12px 16px',
          borderRadius: '8px',
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          border: '1px solid rgba(76, 175, 80, 0.3)',
        }}
      >
        <HAIcon icon="mdi:shield-check" style={{ color: '#4caf50', fontSize: '24px' }} />
        <div>
          <div style={{ fontWeight: 500, fontSize: '14px' }}>DPI Evasion: Medium-High</div>
          <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)' }}>
            Defeats protocol signatures, port-based blocking, and active probing
          </div>
        </div>
      </div>

      {/* Connection Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'var(--secondary-background-color, #282828)' }}>
          <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)', marginBottom: '4px' }}>Listen Port</div>
          <div style={{ fontSize: '16px', fontWeight: 500 }}>{port}</div>
        </div>
        <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'var(--secondary-background-color, #282828)' }}>
          <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)', marginBottom: '4px' }}>VPN Server</div>
          <div style={{ fontSize: '16px', fontWeight: 500, wordBreak: 'break-all' }}>{forwardAddress}</div>
        </div>
      </div>

      {/* OpenVPN Snippet */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <div style={{ fontWeight: 500, fontSize: '14px' }}>OpenVPN Configuration Snippet</div>
          <HAButton variant="ghost" size="sm" onClick={handleCopy} data-testid="copy-ovpn-snippet">
            <HAIcon icon={copied ? 'mdi:check' : 'mdi:content-copy'} slot="start" />
            {copied ? 'Copied!' : 'Copy'}
          </HAButton>
        </div>
        <pre
          style={{
            padding: '16px',
            borderRadius: '8px',
            backgroundColor: 'var(--secondary-background-color, #282828)',
            fontSize: '13px',
            lineHeight: 1.5,
            overflow: 'auto',
            maxHeight: '300px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
          data-testid="ovpn-snippet-content"
        >
          {snippetQuery.isLoading ? 'Loading...' : snippetQuery.data || '# Failed to load snippet'}
        </pre>
      </div>

      {/* How it works - collapsible */}
      <div>
        <div
          onClick={() => setShowDetails(!showDetails)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            padding: '8px 0',
          }}
        >
          <HAIcon
            icon={showDetails ? 'mdi:chevron-down' : 'mdi:chevron-right'}
            style={{ fontSize: '20px', color: 'var(--secondary-text-color)' }}
          />
          <span style={{ fontWeight: 500, fontSize: '14px' }}>How it works</span>
        </div>
        {showDetails && (
          <div style={{ padding: '12px 16px', fontSize: '13px', lineHeight: 1.6, color: 'var(--secondary-text-color)' }}>
            <p style={{ marginBottom: '8px' }}>
              This TLS tunnel uses nginx with SNI multiplexing to distinguish between OpenVPN traffic and regular HTTPS traffic:
            </p>
            <ul style={{ paddingLeft: '20px', marginBottom: '8px' }}>
              <li>nginx inspects the first bytes of each TCP connection</li>
              <li>If the first byte is 0x16 (TLS ClientHello) — routes to the cover website</li>
              <li>If the first byte is NOT 0x16 (OpenVPN with tls-crypt) — routes to your VPN server</li>
              <li>DPI active probes see a legitimate HTTPS website</li>
            </ul>
            <p style={{ fontWeight: 500, marginBottom: '4px' }}>What to tell your VPN provider:</p>
            <p>Enable tls-crypt on your OpenVPN server and provide the ta.key file. The tls-crypt key encrypts the entire OpenVPN handshake, making it invisible to DPI.</p>
          </div>
        )}
      </div>
    </div>
  );
}
