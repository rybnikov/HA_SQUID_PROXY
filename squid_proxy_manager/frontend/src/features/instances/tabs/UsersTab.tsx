import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { userSchema, type UserFormValues } from '../validation';

import { addUser, getUsers, removeUser } from '@/api/instances';
import { HAButton, HADialog, HAIcon, HATextField } from '@/ui/ha-wrappers';

interface UsersTabProps {
  instanceName: string;
}

export function UsersTab({ instanceName }: UsersTabProps) {
  const queryClient = useQueryClient();
  const [userToDelete, setUserToDelete] = useState<string | null>(null);

  const usersQuery = useQuery({
    queryKey: ['users', instanceName],
    queryFn: () => getUsers(instanceName)
  });

  const addMutation = useMutation({
    mutationFn: ({ username, password }: UserFormValues) =>
      addUser(instanceName, username, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', instanceName] });
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      form.reset();
    }
  });

  const removeMutation = useMutation({
    mutationFn: (username: string) => removeUser(instanceName, username),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', instanceName] });
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      setUserToDelete(null);
    }
  });

  const form = useForm<UserFormValues>({
    resolver: zodResolver(userSchema),
    defaultValues: { username: '', password: '' }
  });

  const handleAddUser = form.handleSubmit((values) => {
    addMutation.mutate(values);
  });

  const handleDeleteUser = () => {
    if (userToDelete) {
      removeMutation.mutate(userToDelete);
    }
  };

  const users = usersQuery.data?.users ?? [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <form style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} onSubmit={handleAddUser}>
        <HATextField
          label="Username"
          value={form.watch('username')}
          onChange={(e) => form.setValue('username', e.target.value)}
          data-testid="user-username-input"
        />
        {form.formState.errors.username && (
          <p style={{ color: 'var(--error-color, #db4437)' }}>
            {form.formState.errors.username.message}
          </p>
        )}

        <HATextField
          label="Password"
          type="password"
          value={form.watch('password')}
          onChange={(e) => form.setValue('password', e.target.value)}
          data-testid="user-password-input"
        />
        {form.formState.errors.password && (
          <p style={{ color: 'var(--error-color, #db4437)' }}>
            {form.formState.errors.password.message}
          </p>
        )}

        <div style={{ display: 'flex' }}>
          <HAButton
            type="submit"
            variant="secondary"
            loading={addMutation.isPending}
            data-testid="user-add-button"
          >
            Add User
          </HAButton>
        </div>
      </form>

      <div style={{ borderTop: '1px solid var(--divider-color, rgba(225,225,225,0.12))', paddingTop: '16px' }}>
        <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '8px' }}>Current Users</div>
        {usersQuery.isLoading ? (
          <div style={{ fontSize: '14px' }}>Loading users...</div>
        ) : usersQuery.isError ? (
          <div style={{ fontSize: '14px', color: 'var(--error-color, #db4437)' }}>Failed to load users</div>
        ) : users.length === 0 ? (
          <div style={{ fontSize: '14px', color: 'var(--secondary-text-color, #9b9b9b)' }}>
            No users configured for this instance.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }} data-testid="user-list">
            {users.map((user) => (
              <div
                key={user.username}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  backgroundColor: 'var(--secondary-background-color, #282828)',
                }}
                data-testid={`user-chip-${user.username}`}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <HAIcon icon="mdi:account" style={{ fontSize: '18px', opacity: 0.6 }} />
                  <span style={{ fontSize: '14px' }}>{user.username}</span>
                </div>
                <HAButton
                  variant="ghost"
                  size="sm"
                  onClick={() => setUserToDelete(user.username)}
                  data-testid={`user-delete-${user.username}`}
                >
                  Remove
                </HAButton>
              </div>
            ))}
          </div>
        )}
      </div>

      <HADialog
        id="delete-user-dialog"
        title="Delete User"
        isOpen={userToDelete !== null}
        onClose={() => setUserToDelete(null)}
        footer={
          <div style={{ display: 'flex', gap: '8px' }}>
            <HAButton variant="ghost" onClick={() => setUserToDelete(null)}>Cancel</HAButton>
            <HAButton
              variant="danger"
              onClick={handleDeleteUser}
              loading={removeMutation.isPending}
              data-testid="user-delete-confirm-button"
            >
              Delete
            </HAButton>
          </div>
        }
      >
        <div style={{ padding: '16px' }}>
          <p>Are you sure you want to delete user &quot;{userToDelete}&quot;?</p>
        </div>
      </HADialog>
    </div>
  );
}
