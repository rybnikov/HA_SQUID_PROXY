import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useRef, useState } from 'react';

import { requestJson } from '@/api/client';
import { HAButton, HAIcon } from '@/ui/ha-wrappers';

interface RawConfigTabProps {
  instanceName: string;
  proxyType: 'squid' | 'tls_tunnel';
}

async function getConfig(instanceName: string): Promise<{ config: string }> {
  return requestJson<{ config: string }>(`api/instances/${instanceName}/raw-config`);
}

async function updateConfig(instanceName: string, config: string): Promise<{ status: string }> {
  return requestJson<{ status: string }>(`api/instances/${instanceName}/raw-config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config })
  });
}

// Keywords for nginx/squid config syntax highlighting
const KEYWORDS = new Set([
  // nginx stream
  'stream', 'upstream', 'server', 'listen', 'proxy_pass', 'ssl_preread',
  'map', 'default', 'include', 'worker_processes', 'events', 'worker_connections',
  'error_log', 'pid', 'proxy_protocol', 'proxy_timeout', 'proxy_connect_timeout',
  'ssl_certificate', 'ssl_certificate_key', 'resolver', 'log_format', 'access_log',
  'proxy_bind', 'zone', 'preread_timeout', 'preread_buffer_size',
  // squid
  'http_port', 'https_port', 'acl', 'http_access', 'cache_dir', 'cache_mem',
  'maximum_object_size', 'minimum_object_size', 'cache_log', 'access_log',
  'auth_param', 'authenticate_program', 'authenticate_children', 'authenticate_realm',
  'coredump_dir', 'refresh_pattern', 'dns_nameservers', 'forwarded_for',
  'via', 'reply_header_access', 'request_header_access', 'visible_hostname',
  'cache_effective_user', 'cache_effective_group', 'logfile_rotate',
  'allow', 'deny', 'all', 'localnet', 'localhost', 'manager', 'src', 'port',
  'basic', 'on', 'off', 'none', 'transparent', 'tls_cert', 'tls_key',
]);

function highlightConfig(text: string): string {
  return text
    .split('\n')
    .map((line) => {
      // Comment lines
      if (line.trimStart().startsWith('#')) {
        return `<span class="cfg-comment">${escapeHtml(line)}</span>`;
      }

      // Tokenize the line
      return line.replace(
        /("(?:[^"\\]|\\.)*")|('(?:[^'\\]|\\.)*')|(\b\d+\b)|(\{|\})|([a-zA-Z_][\w]*)/g,
        (match, doubleStr, singleStr, num, brace, word) => {
          if (doubleStr || singleStr) {
            return `<span class="cfg-string">${escapeHtml(match)}</span>`;
          }
          if (num) {
            return `<span class="cfg-number">${escapeHtml(match)}</span>`;
          }
          if (brace) {
            return `<span class="cfg-brace">${escapeHtml(match)}</span>`;
          }
          if (word && KEYWORDS.has(word)) {
            return `<span class="cfg-keyword">${escapeHtml(match)}</span>`;
          }
          return escapeHtml(match);
        }
      );
    })
    .join('\n');
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

export function RawConfigTab({ instanceName, proxyType }: RawConfigTabProps) {
  const queryClient = useQueryClient();
  const [editedConfig, setEditedConfig] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const lineNumbersRef = useRef<HTMLDivElement>(null);
  const preRef = useRef<HTMLPreElement>(null);

  const configQuery = useQuery({
    queryKey: ['raw-config', instanceName],
    queryFn: () => getConfig(instanceName),
  });

  const updateMutation = useMutation({
    mutationFn: (config: string) => updateConfig(instanceName, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['raw-config', instanceName] });
      setSaved(true);
      setEditedConfig(null);
      setTimeout(() => setSaved(false), 2000);
    }
  });

  const currentConfig = editedConfig ?? configQuery.data?.config ?? '';
  const isDirty = editedConfig !== null && editedConfig !== configQuery.data?.config;

  // Add line numbers to the config
  const lines = currentConfig.split('\n');
  const lineNumbers = lines.map((_, i) => i + 1).join('\n');

  const configFileName = proxyType === 'tls_tunnel' ? 'nginx_stream.conf' : 'squid.conf';

  const handleScroll = useCallback((e: React.UIEvent<HTMLTextAreaElement>) => {
    const target = e.currentTarget;
    if (preRef.current) {
      preRef.current.scrollTop = target.scrollTop;
      preRef.current.scrollLeft = target.scrollLeft;
    }
    if (lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = target.scrollTop;
    }
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <style>{`
        .cfg-keyword { color: var(--primary-color, #03a9f4); }
        .cfg-comment { color: var(--secondary-text-color, #9b9b9b); font-style: italic; }
        .cfg-string { color: var(--success-color, #4caf50); }
        .cfg-number { color: var(--warning-color, #ff9800); }
        .cfg-brace { color: var(--primary-color, #03a9f4); font-weight: bold; }
      `}</style>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h3 style={{ margin: '0 0 4px 0', fontSize: '16px', fontWeight: 500 }}>
            {configFileName}
          </h3>
          <p style={{ margin: 0, fontSize: '14px', color: 'var(--secondary-text-color)' }}>
            Edit the raw configuration file. Changes will regenerate the config on save.
          </p>
        </div>
        <HAButton
          onClick={() => {
            if (editedConfig !== null) {
              updateMutation.mutate(editedConfig);
            }
          }}
          loading={updateMutation.isPending}
          disabled={!isDirty || updateMutation.isPending}
          data-testid="raw-config-save-button"
        >
          <HAIcon icon={saved ? 'mdi:check' : 'mdi:content-save'} slot="start" />
          {saved ? 'Saved!' : 'Save Changes'}
        </HAButton>
      </div>

      {configQuery.isLoading && (
        <p style={{ fontSize: '14px', color: 'var(--secondary-text-color)' }}>
          Loading configuration...
        </p>
      )}

      {configQuery.isError && (
        <div style={{
          padding: '12px',
          backgroundColor: 'rgba(219, 68, 55, 0.1)',
          borderRadius: '8px',
          borderLeft: '4px solid var(--error-color)'
        }}>
          <p style={{ fontSize: '14px', color: 'var(--error-color)', margin: 0 }}>
            Failed to load configuration
          </p>
        </div>
      )}

      {configQuery.data && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'auto 1fr',
            border: '1px solid var(--divider-color)',
            borderRadius: '8px',
            overflow: 'hidden',
            backgroundColor: 'var(--secondary-background-color)',
          }}
        >
          {/* Line numbers */}
          <div
            ref={lineNumbersRef}
            style={{
              padding: '12px 8px',
              textAlign: 'right',
              fontFamily: 'monospace',
              fontSize: '13px',
              color: 'var(--secondary-text-color)',
              backgroundColor: 'var(--card-background-color)',
              borderRight: '1px solid var(--divider-color)',
              userSelect: 'none',
              lineHeight: '1.5',
              overflow: 'hidden',
              whiteSpace: 'pre',
            }}
          >
            {lineNumbers}
          </div>

          {/* Config editor with syntax highlighting overlay */}
          <div style={{ position: 'relative', minHeight: '500px' }}>
            {/* Highlighted pre behind textarea */}
            <pre
              ref={preRef}
              aria-hidden
              data-testid="raw-config-highlight"
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                margin: 0,
                padding: '12px',
                fontFamily: 'monospace',
                fontSize: '13px',
                lineHeight: '1.5',
                whiteSpace: 'pre',
                overflow: 'hidden',
                pointerEvents: 'none',
                color: 'var(--primary-text-color)',
              }}
              dangerouslySetInnerHTML={{ __html: highlightConfig(currentConfig) }}
            />

            {/* Transparent textarea on top */}
            <textarea
              value={currentConfig}
              onChange={(e) => setEditedConfig(e.target.value)}
              onScroll={handleScroll}
              spellCheck={false}
              style={{
                position: 'relative',
                width: '100%',
                minHeight: '500px',
                height: '100%',
                fontFamily: 'monospace',
                fontSize: '13px',
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
              data-testid="raw-config-editor"
            />
          </div>
        </div>
      )}

      {updateMutation.isError && (
        <div style={{
          padding: '12px',
          backgroundColor: 'rgba(219, 68, 55, 0.1)',
          borderRadius: '8px',
          borderLeft: '4px solid var(--error-color)'
        }}>
          <p style={{ fontSize: '14px', color: 'var(--error-color)', margin: 0 }}>
            Failed to save configuration. Please check syntax and try again.
          </p>
        </div>
      )}

      <div style={{
        padding: '12px',
        backgroundColor: 'rgba(255, 152, 0, 0.1)',
        borderRadius: '8px',
        borderLeft: '4px solid var(--warning-color)'
      }}>
        <div style={{ display: 'flex', gap: '12px' }}>
          <HAIcon icon="mdi:alert" style={{ flexShrink: 0, color: 'var(--warning-color)' }} />
          <div>
            <p style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: 500 }}>
              Warning: Advanced Users Only
            </p>
            <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '14px', color: 'var(--secondary-text-color)' }}>
              <li>Manual edits may break the proxy if syntax is incorrect</li>
              <li>The instance will be restarted after saving</li>
              <li>Use the Settings tabs for standard configuration changes</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
