import { useMutation } from '@tanstack/react-query';
import type { FormEvent } from 'react';
import { useState } from 'react';
import { z } from 'zod';

import { testConnectivity } from '@/api/instances';
import { HAButton, HAIcon, HATextField } from '@/ui/ha-wrappers';

interface TestTabProps {
  instanceName: string;
}

interface TestResult {
  status: 'success' | 'error';
  message: string;
}

interface FormErrors {
  username?: string;
  password?: string;
  target_url?: string;
}

const testCredentialsSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
  target_url: z
    .string()
    .optional()
    .refine((value) => value === undefined || value === '' || /^(https?:)\/\//.test(value), {
      message: 'Target URL must be a valid URL'
    })
});

export function TestTab({ instanceName }: TestTabProps) {
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [targetUrl, setTargetUrl] = useState('http://example.com');
  const [errors, setErrors] = useState<FormErrors>({});

  const testMutation = useMutation({
    mutationFn: (values: { username: string; password: string; target_url?: string }) =>
      testConnectivity(instanceName, values.username, values.password, values.target_url),
    onSuccess: (data) => {
      setTestResult({
        status: data.status === 'success' ? 'success' : 'error',
        message: data.message ?? 'Connection successful!'
      });
    },
    onError: (error) => {
      setTestResult({
        status: 'error',
        message: error instanceof Error ? error.message : 'Connection test failed'
      });
    }
  });

  const handleTest = (e: FormEvent) => {
    e.preventDefault();

    const result = testCredentialsSchema.safeParse({ username, password, target_url: targetUrl });
    if (!result.success) {
      const fieldErrors: FormErrors = {};
      result.error.issues.forEach((issue) => {
        const field = issue.path[0] as keyof FormErrors;
        if (field) {
          fieldErrors[field] = issue.message;
        }
      });
      setErrors(fieldErrors);
      return;
    }

    setErrors({});
    setTestResult(null);
    testMutation.mutate({ username, password, target_url: targetUrl || undefined });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <p style={{ fontSize: '14px', color: 'var(--secondary-text-color, #9b9b9b)', margin: 0 }}>
        Enter credentials for a user of this proxy instance. The proxy must be running.
      </p>

      <form style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} onSubmit={handleTest}>
        <HATextField
          label="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          data-testid="test-username-input"
        />
        {errors.username && (
          <p style={{ color: 'var(--error-color, #db4437)' }}>{errors.username}</p>
        )}

        <HATextField
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          data-testid="test-password-input"
        />
        {errors.password && (
          <p style={{ color: 'var(--error-color, #db4437)' }}>{errors.password}</p>
        )}

        <HATextField
          label="Target URL"
          type="url"
          value={targetUrl}
          placeholder="http://example.com"
          onChange={(e) => setTargetUrl(e.target.value)}
          data-testid="test-url-input"
        />
        {errors.target_url && (
          <p style={{ color: 'var(--error-color, #db4437)' }}>{errors.target_url}</p>
        )}

        <div style={{ display: 'flex' }}>
          <HAButton
            type="submit"
            variant="secondary"
            loading={testMutation.isPending}
            data-testid="test-button"
          >
            <HAIcon icon="mdi:connection" slot="start" />
            Test Connectivity
          </HAButton>
        </div>
      </form>

      {testResult && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '14px',
            backgroundColor: testResult.status === 'success'
              ? 'rgba(67, 160, 71, 0.12)'
              : 'rgba(219, 68, 55, 0.12)',
            color: testResult.status === 'success'
              ? 'var(--success-color, #43a047)'
              : 'var(--error-color, #db4437)',
          }}
          data-testid="test-result"
        >
          <div style={{ fontWeight: 500 }}>
            {testResult.status === 'success' ? 'Success' : 'Failed'}
          </div>
          <div>{testResult.message}</div>
        </div>
      )}
    </div>
  );
}
