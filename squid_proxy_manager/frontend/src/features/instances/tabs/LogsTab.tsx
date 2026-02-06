import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { CSSProperties, ReactNode } from 'react';
import { useEffect, useState, useCallback } from 'react';

import { clearLogs, getLogs } from '@/api/instances';
import { HAButton, HAIcon, HASwitch, HATextField } from '@/ui/ha-wrappers';

interface LogsTabProps {
  instanceName: string;
}

type LogType = 'access' | 'cache';

const TAB_STYLE_BASE: CSSProperties = {
  padding: '6px 16px',
  fontSize: '13px',
  fontWeight: 500,
  cursor: 'pointer',
  border: 'none',
  borderBottom: '2px solid transparent',
  background: 'none',
  color: 'var(--secondary-text-color, #9b9b9b)',
  transition: 'color 0.15s, border-color 0.15s',
};

const TAB_STYLE_ACTIVE: CSSProperties = {
  ...TAB_STYLE_BASE,
  color: 'var(--primary-color, #03a9f4)',
  borderBottomColor: 'var(--primary-color, #03a9f4)',
};

/** Colorize a Squid cache/debug log line.
 *  Formats:
 *    "YYYY/MM/DD HH:MM:SS kid1| message"
 *    "YYYY/MM/DD HH:MM:SS| message"
 *    "--- Starting Squid at ... ---"
 *    "Command: /usr/sbin/squid ..."
 */
function colorizeCacheLine(line: string): ReactNode {
  // Match: timestamp + optional kidN + pipe + message
  const parts = line.match(
    /^(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2}:\d{2})\s*(?:(kid\d+))?\|\s*(.*)$/
  );
  if (parts) {
    const [, timestamp, kid, message] = parts;

    const lower = message.toLowerCase();
    const isError = lower.startsWith('error') || lower.startsWith('fatal');
    const isWarning = lower.startsWith('warning') || lower.startsWith('warn');
    const isDebug = lower.startsWith('debug') || /^\d+,\d+/.test(message);

    const msgColor = isError
      ? 'var(--error-color, #db4437)'
      : isWarning
        ? 'var(--warning-color, #ffcb6b)'
        : isDebug
          ? 'var(--secondary-text-color, #888)'
          : 'var(--primary-text-color, #e1e1e1)';

    return (
      <>
        <span style={{ color: 'var(--secondary-text-color, #888)', fontWeight: 700 }}>{timestamp}</span>
        {' '}
        {kid && (
          <>
            <span style={{ color: 'var(--primary-color, #03a9f4)' }}>{kid}</span>
          </>
        )}
        <span style={{ color: 'var(--secondary-text-color, #888)' }}>|</span>
        {' '}
        <span style={{ color: msgColor }}>{message}</span>
      </>
    );
  }

  // Separator lines like "--- Starting Squid at ... ---"
  if (line.startsWith('---')) {
    return <span style={{ color: 'var(--accent-color, #c792ea)' }}>{line}</span>;
  }

  // Command lines like "Command: /usr/sbin/squid ..."
  if (line.startsWith('Command:')) {
    return <span style={{ color: 'var(--warning-color, #ffcb6b)' }}>{line}</span>;
  }

  return line;
}

/** Colorize a Squid access log line. */
function colorizeAccessLine(line: string): ReactNode {
  // Squid access log format:
  // timestamp elapsed client action/code size method URL user hierarchy type
  const parts = line.match(
    /^(\S+)\s+(\S+)\s+(\S+)\s+(TCP_\S+\/\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)$/
  );
  if (!parts) return line;

  const [, timestamp, elapsed, client, statusCode, size, method, url, user, hierarchy, contentType] = parts;
  const isError = statusCode.includes('/4') || statusCode.includes('/5');

  return (
    <>
      <span style={{ color: 'var(--secondary-text-color, #888)' }}>{timestamp}</span>
      {' '}
      <span style={{ color: 'var(--secondary-text-color, #888)' }}>{elapsed}</span>
      {' '}
      <span style={{ color: 'var(--primary-color, #03a9f4)' }}>{client}</span>
      {' '}
      <span style={{ color: isError ? 'var(--error-color, #db4437)' : 'var(--success-color, #43a047)' }}>{statusCode}</span>
      {' '}
      <span style={{ color: 'var(--secondary-text-color, #888)' }}>{size}</span>
      {' '}
      <span style={{ color: 'var(--accent-color, #c792ea)' }}>{method}</span>
      {' '}
      <span style={{ color: 'var(--primary-text-color, #e1e1e1)' }}>{url}</span>
      {' '}
      <span style={{ color: 'var(--warning-color, #ffcb6b)' }}>{user}</span>
      {' '}
      <span style={{ color: 'var(--secondary-text-color, #888)' }}>{hierarchy}</span>
      {' '}
      <span style={{ color: 'var(--secondary-text-color, #888)' }}>{contentType}</span>
    </>
  );
}

export function LogsTab({ instanceName }: LogsTabProps) {
  const queryClient = useQueryClient();
  const [logType, setLogType] = useState<LogType>('access');
  const [searchFilter, setSearchFilter] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);

  const logsQuery = useQuery({
    queryKey: ['logs', instanceName, logType],
    queryFn: () => getLogs(instanceName, logType),
    refetchInterval: autoRefresh ? 5000 : false
  });

  const clearMutation = useMutation({
    mutationFn: () => clearLogs(instanceName, logType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logs', instanceName, logType] });
    }
  });

  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['logs', instanceName, logType] });
  }, [queryClient, instanceName, logType]);

  useEffect(() => {
    handleRefresh();
  }, [logType, handleRefresh]);

  const logs = logsQuery.data ?? '';
  const lines = logs.split('\n').filter(Boolean);
  const filteredLines = searchFilter
    ? lines.filter((line) => line.toLowerCase().includes(searchFilter.toLowerCase()))
    : lines;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%' }}>
      {/* Tab bar */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid var(--divider-color, rgba(225,225,225,0.12))',
          gap: '4px',
        }}
        data-testid="logs-type-select"
      >
        <button
          type="button"
          style={logType === 'access' ? TAB_STYLE_ACTIVE : TAB_STYLE_BASE}
          onClick={() => setLogType('access')}
        >
          Access Log
        </button>
        <button
          type="button"
          style={logType === 'cache' ? TAB_STYLE_ACTIVE : TAB_STYLE_BASE}
          onClick={() => setLogType('cache')}
        >
          Cache Log
        </button>
      </div>

      {/* Controls row */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center' }}>
        <HATextField
          label=""
          value={searchFilter}
          placeholder="Filter logs..."
          onChange={(e) => setSearchFilter(e.target.value)}
          data-testid="logs-search-input"
        />

        <HASwitch
          label="Auto-refresh"
          checked={autoRefresh}
          onChange={(e) => setAutoRefresh(e.target.checked)}
          data-testid="logs-autorefresh-switch"
        />

        <div style={{ flex: 1 }} />

        <HAButton
          variant="secondary"
          size="sm"
          onClick={handleRefresh}
          disabled={logsQuery.isFetching}
        >
          <HAIcon icon="mdi:refresh" slot="start" />
          Refresh
        </HAButton>
        <HAButton
          variant="secondary"
          size="sm"
          onClick={() => clearMutation.mutate()}
          loading={clearMutation.isPending}
          data-testid="logs-clear-button"
        >
          <HAIcon icon="mdi:delete-sweep" slot="start" />
          Clear
        </HAButton>
      </div>

      {/* Log viewer */}
      {logsQuery.isLoading ? (
        <div style={{ fontSize: '14px' }}>Loading logs...</div>
      ) : logsQuery.isError ? (
        <div style={{ fontSize: '14px', color: 'var(--error-color, #db4437)' }}>Failed to load logs</div>
      ) : filteredLines.length === 0 ? (
        <div style={{ fontSize: '14px', color: 'var(--secondary-text-color, #9b9b9b)' }}>
          No log entries found.
        </div>
      ) : (
        <div
          style={{
            fontSize: '11px',
            fontFamily: "'Roboto Mono', 'Fira Code', 'Consolas', monospace",
            backgroundColor: 'var(--code-editor-background-color, rgba(0, 0, 0, 0.15))',
            color: 'var(--primary-text-color, #e1e1e1)',
            padding: '12px',
            borderRadius: '8px',
            overflow: 'auto',
            flex: 1,
            minHeight: '200px',
            lineHeight: 1.6,
          }}
          data-testid="logs-viewer"
        >
          {filteredLines.map((line, i) => (
            <div key={i} style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {logType === 'access' ? colorizeAccessLine(line) : colorizeCacheLine(line)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
