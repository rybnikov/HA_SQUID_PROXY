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
}

export function GeneralTab({
  instance,
  onPortChange,
  onHttpsChange,
  port,
  httpsEnabled
}: GeneralTabProps) {
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);

  const updateMutation = useMutation({
    mutationFn: (payload: { port: number; https_enabled: boolean }) =>
      updateInstance(instance.name, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  });

  const isDirty = port !== instance.port || httpsEnabled !== instance.https_enabled;

  const handleSave = () => {
    updateMutation.mutate({
      port,
      https_enabled: httpsEnabled
    });
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
        label="Port"
        type="number"
        value={String(port)}
        min={1024}
        max={65535}
        onChange={(e) => onPortChange(Number(e.target.value))}
        data-testid="settings-port-input"
      />

      <HASwitch
        label="Enable HTTPS (SSL)"
        checked={httpsEnabled}
        onChange={(e) => onHttpsChange(e.target.checked)}
        data-testid="settings-https-switch"
      />

      <div style={{ display: 'flex', paddingTop: '8px' }}>
        <HAButton
          onClick={handleSave}
          loading={updateMutation.isPending}
          disabled={!isDirty || updateMutation.isPending}
          data-testid="settings-save-button"
        >
          <HAIcon icon={saved ? 'mdi:check' : 'mdi:content-save'} slot="start" />
          {saved ? 'Saved!' : 'Save Changes'}
        </HAButton>
      </div>
    </div>
  );
}
