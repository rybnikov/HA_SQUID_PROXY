import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';

import { apiFetch } from '@/api/client';
import { HAButton, HAIcon } from '@/ui/ha-wrappers';

interface TlsTunnelTestTabProps {
  instanceName: string;
}

interface TestResult {
  success: boolean;
  message: string;
  details?: string;
}

async function testTunnel(instanceName: string, testType: 'cover' | 'forward'): Promise<TestResult> {
  const response = await apiFetch(`api/instances/${instanceName}/test-tunnel?type=${testType}`, {
    method: 'POST'
  });

  if (!response.ok) {
    const errorText = await response.text();
    return {
      success: false,
      message: 'Test failed',
      details: errorText
    };
  }

  return response.json() as Promise<TestResult>;
}

export function TlsTunnelTestTab({ instanceName }: TlsTunnelTestTabProps) {
  const [coverResult, setCoverResult] = useState<TestResult | null>(null);
  const [forwardResult, setForwardResult] = useState<TestResult | null>(null);

  const coverTestMutation = useMutation({
    mutationFn: () => testTunnel(instanceName, 'cover'),
    onSuccess: (data) => setCoverResult(data),
    onError: (error) => setCoverResult({
      success: false,
      message: 'Test failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    })
  });

  const forwardTestMutation = useMutation({
    mutationFn: () => testTunnel(instanceName, 'forward'),
    onSuccess: (data) => setForwardResult(data),
    onError: (error) => setForwardResult({
      success: false,
      message: 'Test failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    })
  });

  const renderResult = (result: TestResult | null) => {
    if (!result) return null;

    return (
      <div
        style={{
          marginTop: '12px',
          padding: '12px',
          borderRadius: '8px',
          backgroundColor: result.success
            ? 'rgba(67, 160, 71, 0.1)'
            : 'rgba(219, 68, 55, 0.1)',
          border: `1px solid ${result.success
            ? 'var(--success-color, #43a047)'
            : 'var(--error-color, #db4437)'}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <HAIcon
            icon={result.success ? 'mdi:check-circle' : 'mdi:alert-circle'}
            style={{
              color: result.success
                ? 'var(--success-color, #43a047)'
                : 'var(--error-color, #db4437)',
              fontSize: '20px'
            }}
          />
          <span style={{
            fontSize: '14px',
            fontWeight: 500,
            color: result.success
              ? 'var(--success-color, #43a047)'
              : 'var(--error-color, #db4437)'
          }}>
            {result.message}
          </span>
        </div>
        {result.details && (
          <div style={{
            fontSize: '12px',
            color: 'var(--secondary-text-color, #9b9b9b)',
            marginLeft: '28px',
            fontFamily: 'monospace',
            whiteSpace: 'pre-wrap'
          }}>
            {result.details}
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Cover Site Test */}
      <div>
        <div style={{ fontSize: '16px', fontWeight: 500, marginBottom: '8px' }}>
          Test Cover Site
        </div>
        <div style={{ fontSize: '14px', color: 'var(--secondary-text-color, #9b9b9b)', marginBottom: '12px' }}>
          Verify that DPI probes see the cover website when connecting without tls-crypt.
        </div>
        <HAButton
          variant="secondary"
          onClick={() => coverTestMutation.mutate()}
          loading={coverTestMutation.isPending}
          data-testid="test-cover-site-button"
        >
          <HAIcon icon="mdi:web" slot="start" />
          Test Cover Site
        </HAButton>
        {renderResult(coverResult)}
      </div>

      {/* VPN Forwarding Test */}
      <div>
        <div style={{ fontSize: '16px', fontWeight: 500, marginBottom: '8px' }}>
          Test VPN Forwarding
        </div>
        <div style={{ fontSize: '14px', color: 'var(--secondary-text-color, #9b9b9b)', marginBottom: '12px' }}>
          Test TCP connectivity to the VPN server destination to ensure traffic can be forwarded.
        </div>
        <HAButton
          variant="secondary"
          onClick={() => forwardTestMutation.mutate()}
          loading={forwardTestMutation.isPending}
          data-testid="test-vpn-forwarding-button"
        >
          <HAIcon icon="mdi:vpn" slot="start" />
          Test VPN Forwarding
        </HAButton>
        {renderResult(forwardResult)}
      </div>

      {/* Info box */}
      <div style={{
        padding: '12px 16px',
        borderRadius: '8px',
        backgroundColor: 'rgba(3,169,244,0.08)',
        border: '1px solid rgba(3,169,244,0.2)',
      }}>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
          <HAIcon icon="mdi:information-outline" style={{ color: 'var(--primary-color, #03a9f4)', flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '13px', color: 'var(--primary-text-color)', lineHeight: '1.5' }}>
            <strong>About these tests:</strong>
            <ul style={{ marginTop: '8px', paddingLeft: '20px' }}>
              <li style={{ marginBottom: '4px' }}>
                <strong>Cover Site:</strong> Sends HTTPS request without tls-crypt to verify the cover website responds correctly
              </li>
              <li>
                <strong>VPN Forwarding:</strong> Tests TCP connection to your VPN server to ensure packets can be forwarded
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
