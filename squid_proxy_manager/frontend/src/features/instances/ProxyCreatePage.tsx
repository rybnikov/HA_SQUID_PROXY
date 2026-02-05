import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';

import { createInstance } from '@/api/instances';
import {
  HAButton,
  HACard,
  HASwitch,
  HATextField,
  HATopBar
} from '@/ui/ha-wrappers';

const createFormSchema = z.object({
  name: z.string().min(1, 'Instance name is required').regex(/^[a-zA-Z0-9._-]+$/, {
    message: 'Use letters, numbers, dots, hyphens, or underscores'
  }),
  port: z.number().int().min(1024).max(65535),
  https_enabled: z.boolean(),
  users: z.array(z.object({
    username: z.string().min(1),
    password: z.string().min(6)
  }))
});

type CreateFormValues = z.infer<typeof createFormSchema>;

interface FormErrors {
  name?: string;
  port?: string;
}

export function ProxyCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');

  const [formValues, setFormValues] = useState<CreateFormValues>({
    name: '',
    port: 3128,
    https_enabled: false,
    users: []
  });
  const [errors, setErrors] = useState<FormErrors>({});

  const httpsEnabled = formValues.https_enabled;
  const users = formValues.users;

  const createMutation = useMutation({
    mutationFn: createInstance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      navigate('/');
    }
  });

  const handleCreate = async () => {
    const result = createFormSchema.safeParse(formValues);
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
    await createMutation.mutateAsync({
      name: result.data.name,
      port: result.data.port,
      https_enabled: result.data.https_enabled,
      users: result.data.users
    });
  };

  const handleAddUser = () => {
    if (newUsername && newPassword && newPassword.length >= 6) {
      setFormValues((prev) => ({
        ...prev,
        users: [...prev.users, { username: newUsername, password: newPassword }]
      }));
      setNewUsername('');
      setNewPassword('');
    }
  };

  const handleRemoveUser = (index: number) => {
    setFormValues((prev) => ({
      ...prev,
      users: prev.users.filter((_, i) => i !== index)
    }));
  };

  return (
    <div style={{ minHeight: '100vh' }}>
      <HATopBar title="New Proxy Instance" onBack={() => navigate('/')} />

      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '16px 16px 32px' }}>
        <div style={{ display: 'grid', gap: '16px' }}>
          <HACard title="Instance Details" data-testid="create-instance-form">
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <HATextField
                label="Instance Name"
                value={formValues.name}
                onChange={(e) => setFormValues((prev) => ({ ...prev, name: e.target.value }))}
                helperText="Letters, numbers, dots, hyphens, or underscores"
                data-testid="create-name-input"
              />
              {errors.name && (
                <p style={{ fontSize: '12px', color: 'var(--error-color, #db4437)' }}>{errors.name}</p>
              )}

              <HATextField
                label="Port"
                type="number"
                value={String(formValues.port)}
                min={1024}
                max={65535}
                onChange={(e) => setFormValues((prev) => ({ ...prev, port: Number(e.target.value) || 3128 }))}
                data-testid="create-port-input"
              />
              {errors.port && (
                <p style={{ fontSize: '12px', color: 'var(--error-color, #db4437)' }}>{errors.port}</p>
              )}

              <HASwitch
                label="Enable HTTPS (SSL)"
                checked={httpsEnabled}
                onChange={(e) => setFormValues((prev) => ({ ...prev, https_enabled: e.target.checked }))}
                data-testid="create-https-switch"
              />
            </div>
          </HACard>

          <HACard title="Initial Users">
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <HATextField
                  label="Username"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  data-testid="create-user-username-input"
                />
                <HATextField
                  label="Password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  helperText="Minimum 6 characters"
                  data-testid="create-user-password-input"
                />
                <HAButton
                  variant="secondary"
                  onClick={handleAddUser}
                  disabled={!newUsername || newPassword.length < 6}
                  data-testid="create-user-add-button"
                >
                  Add User
                </HAButton>
              </div>

              {users.length > 0 && (
                <div style={{ borderTop: '1px solid var(--divider-color, rgba(225,225,225,0.12))', paddingTop: '16px' }}>
                  <p style={{ fontSize: '14px', fontWeight: 500, marginBottom: '8px' }}>Users to create:</p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {users.map((user, index) => (
                      <div
                        key={index}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          backgroundColor: 'var(--secondary-background-color, #282828)',
                        }}
                      >
                        <span style={{ fontSize: '14px' }}>{user.username}</span>
                        <HAButton
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveUser(index)}
                        >
                          Remove
                        </HAButton>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {users.length === 0 && (
                <p style={{ fontSize: '14px', color: 'var(--secondary-text-color, #9b9b9b)' }}>
                  No users added yet. You can add users now or configure them later from instance settings.
                </p>
              )}
            </div>
          </HACard>

          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', paddingTop: '16px', marginTop: '8px' }}>
            <HAButton variant="ghost" onClick={() => navigate('/')}>
              Cancel
            </HAButton>
            <HAButton
              variant="primary"
              onClick={handleCreate}
              loading={createMutation.isPending}
              data-testid="create-submit-button"
            >
              Create Instance
            </HAButton>
          </div>
        </div>
      </div>
    </div>
  );
}
