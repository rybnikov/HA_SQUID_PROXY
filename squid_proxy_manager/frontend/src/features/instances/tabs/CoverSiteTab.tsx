import { useState } from 'react';

import { HAButton, HAIcon, HATextField } from '@/ui/ha-wrappers';

interface CoverSiteTabProps {
  instanceName: string;
  coverDomain: string;
  port: number;
  onCoverDomainChange: (domain: string) => void;
  onSave: () => void;
  saving: boolean;
  isDirty: boolean;
}

export function CoverSiteTab({
  instanceName,
  coverDomain,
  port,
  onCoverDomainChange,
  onSave,
  saving,
  isDirty,
}: CoverSiteTabProps) {
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    onSave();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Info banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
          padding: '12px 16px',
          borderRadius: '8px',
          backgroundColor: 'rgba(3, 169, 244, 0.08)',
          border: '1px solid rgba(3, 169, 244, 0.2)',
        }}
      >
        <HAIcon icon="mdi:information-outline" style={{ color: 'var(--primary-color, #03a9f4)', fontSize: '20px', flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '13px', color: 'var(--secondary-text-color)' }}>
          This website is shown to DPI systems that probe your server. It should look like a normal, legitimate website to avoid suspicion.
        </div>
      </div>

      {/* Cover Domain */}
      <HATextField
        label="Cover Domain"
        value={coverDomain}
        onChange={(e) => onCoverDomainChange(e.target.value)}
        helperText="Domain name for the cover website SSL certificate. Leave empty for self-signed."
        data-testid="cover-domain-input"
      />

      {/* SSL Certificate Status */}
      <div
        style={{
          padding: '12px 16px',
          borderRadius: '8px',
          backgroundColor: 'var(--secondary-background-color, #282828)',
        }}
      >
        <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)', marginBottom: '4px' }}>SSL Certificate</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <HAIcon icon="mdi:certificate" style={{ fontSize: '16px', color: 'var(--warning-color, #ff9800)' }} />
          <span style={{ fontSize: '14px' }}>Self-signed certificate</span>
        </div>
      </div>

      {/* Cover Site Preview Info */}
      <div
        style={{
          padding: '12px 16px',
          borderRadius: '8px',
          backgroundColor: 'var(--secondary-background-color, #282828)',
        }}
      >
        <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)', marginBottom: '4px' }}>Cover Site Content</div>
        <div style={{ fontSize: '14px' }}>Default "Under Construction" page</div>
        <div style={{ fontSize: '12px', color: 'var(--secondary-text-color)', marginTop: '4px' }}>
          The cover website serves a minimal HTML page to any browser or DPI probe that connects.
        </div>
      </div>

      {/* Save button */}
      <div style={{ display: 'flex', paddingTop: '8px' }}>
        <HAButton
          onClick={handleSave}
          loading={saving}
          disabled={!isDirty || saving}
          data-testid="cover-site-save-button"
        >
          <HAIcon icon={saved ? 'mdi:check' : 'mdi:content-save'} slot="start" />
          {saved ? 'Saved!' : 'Save Changes'}
        </HAButton>
      </div>
    </div>
  );
}
