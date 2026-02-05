import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { getCertificateInfo, regenerateCertificates } from '@/api/instances';
import { HAButton } from '@/ui/ha-wrappers';

interface HTTPSTabProps {
  instanceName: string;
  httpsEnabled: boolean;
}

export function HTTPSTab({ instanceName, httpsEnabled }: HTTPSTabProps) {
  const queryClient = useQueryClient();

  const certQuery = useQuery({
    queryKey: ['certificate', instanceName],
    queryFn: () => getCertificateInfo(instanceName),
    enabled: httpsEnabled
  });

  const regenerateMutation = useMutation({
    mutationFn: () => regenerateCertificates(instanceName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificate', instanceName] });
    }
  });

  if (!httpsEnabled) {
    return (
      <div style={{ fontSize: '14px', color: 'var(--secondary-text-color, #9b9b9b)' }}>
        HTTPS is not enabled. Enable it in the Configuration section above.
      </div>
    );
  }

  const cert = certQuery.data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {certQuery.isLoading ? (
        <div style={{ fontSize: '14px' }}>Loading certificate info...</div>
      ) : certQuery.isError ? (
        <div style={{ fontSize: '14px', color: 'var(--error-color, #db4437)' }}>
          Failed to load certificate info
        </div>
      ) : cert?.status === 'missing' ? (
        <div style={{ fontSize: '14px' }}>
          No certificate found. Certificate will be auto-generated when the instance starts.
        </div>
      ) : cert?.status === 'invalid' ? (
        <div style={{ fontSize: '14px', color: 'var(--error-color, #db4437)' }}>
          Invalid certificate: {cert.error}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 16px', fontSize: '14px' }}>
          <span style={{ fontWeight: 500, color: 'var(--secondary-text-color, #9b9b9b)' }}>Status</span>
          <span style={{ color: 'var(--success-color, #43a047)' }}>Valid</span>
          <span style={{ fontWeight: 500, color: 'var(--secondary-text-color, #9b9b9b)' }}>Common Name</span>
          <span>{cert?.common_name ?? 'N/A'}</span>
          <span style={{ fontWeight: 500, color: 'var(--secondary-text-color, #9b9b9b)' }}>Valid From</span>
          <span>{cert?.not_valid_before ? new Date(cert.not_valid_before).toLocaleDateString() : 'N/A'}</span>
          <span style={{ fontWeight: 500, color: 'var(--secondary-text-color, #9b9b9b)' }}>Valid Until</span>
          <span>{cert?.not_valid_after ? new Date(cert.not_valid_after).toLocaleDateString() : 'N/A'}</span>
        </div>
      )}

      <div>
        <HAButton
          variant="secondary"
          onClick={() => regenerateMutation.mutate()}
          loading={regenerateMutation.isPending}
          data-testid="cert-regenerate-button"
        >
          Regenerate Certificate
        </HAButton>
        <p style={{ fontSize: '13px', marginTop: '8px', color: 'var(--secondary-text-color, #9b9b9b)' }}>
          This will generate a new self-signed certificate. The instance may need to be restarted.
        </p>
      </div>
    </div>
  );
}
