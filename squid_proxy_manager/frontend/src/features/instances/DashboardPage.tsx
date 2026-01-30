import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';

import {
  createInstanceSchema,
  testCredentialsSchema,
  updateInstanceSchema,
  userSchema,
  type CreateInstanceFormInput,
  type TestCredentialsValues,
  type UpdateInstanceFormInput,
  type UserFormValues
} from './validation';

import {
  addUser,
  clearLogs,
  createInstance,
  deleteInstance,
  getCertificateInfo,
  getInstances,
  getLogs,
  getUsers,
  regenerateCertificates,
  removeUser,
  startInstance,
  stopInstance,
  testConnectivity,
  updateInstance
} from '@/api/instances';
import type { ProxyInstance } from '@/api/instances';
import { Button } from '@/ui/Button';
import { Card } from '@/ui/Card';
import { Checkbox } from '@/ui/Checkbox';
import { Input } from '@/ui/Input';
import { Modal } from '@/ui/Modal';
import { cn } from '@/utils/cn';

function ServerIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <rect x="3" y="4" width="18" height="6" rx="2" stroke="currentColor" strokeWidth="2" />
      <rect x="3" y="14" width="18" height="6" rx="2" stroke="currentColor" strokeWidth="2" />
      <circle cx="7" cy="7" r="1" fill="currentColor" />
      <circle cx="7" cy="17" r="1" fill="currentColor" />
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function PlayIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d="M8 6l10 6-10 6V6z" stroke="currentColor" strokeWidth="1.8" fill="none" />
    </svg>
  );
}

function StopIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <rect x="7" y="7" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M12 8a4 4 0 100 8 4 4 0 000-8zm8 4a7.93 7.93 0 01-.2 1.7l2.1 1.6-2 3.4-2.5-1a8.2 8.2 0 01-2.9 1.7l-.4 2.7h-4l-.4-2.7a8.2 8.2 0 01-2.9-1.7l-2.5 1-2-3.4 2.1-1.6A7.93 7.93 0 014 12c0-.6.07-1.16.2-1.7L2.1 8.7l2-3.4 2.5 1a8.2 8.2 0 012.9-1.7l.4-2.7h4l.4 2.7a8.2 8.2 0 012.9 1.7l2.5-1 2 3.4-2.1 1.6c.13.54.2 1.1.2 1.7z"
        stroke="currentColor"
        strokeWidth="1.4"
      />
    </svg>
  );
}

const createDefaults: CreateInstanceFormInput = {
  name: '',
  port: 3128,
  https_enabled: false
};

export function DashboardPage() {
  const queryClient = useQueryClient();
  const instancesQuery = useQuery({
    queryKey: ['instances'],
    queryFn: getInstances,
    refetchInterval: 10_000
  });

  const instances = useMemo(() => instancesQuery.data?.instances ?? [], [instancesQuery.data]);
  const runningCount = useMemo(() => instances.filter((instance) => instance.running).length, [instances]);

  const [isAddOpen, setAddOpen] = useState(false);
  const [isSettingsOpen, setSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState<
    'main' | 'users' | 'certificate' | 'logs' | 'test' | 'status' | 'delete'
  >('main');
  const [selectedInstance, setSelectedInstance] = useState<ProxyInstance | null>(null);

  const logType: 'cache' | 'access' = 'access';
  const [logContent, setLogContent] = useState('Loading logs...');
  const [userError, setUserError] = useState('');
  const [testResult, setTestResult] = useState('');
  const [deleteError, setDeleteError] = useState('');

  const createForm = useForm<CreateInstanceFormInput>({
    resolver: zodResolver(createInstanceSchema),
    defaultValues: createDefaults,
    mode: 'onTouched'
  });

  const settingsForm = useForm<UpdateInstanceFormInput>({
    resolver: zodResolver(updateInstanceSchema),
    defaultValues: {
      port: createDefaults.port,
      https_enabled: createDefaults.https_enabled
    },
    mode: 'onTouched'
  });

  const userForm = useForm<UserFormValues>({
    resolver: zodResolver(userSchema),
    defaultValues: { username: '', password: '' },
    mode: 'onTouched'
  });

  const testForm = useForm<TestCredentialsValues>({
    resolver: zodResolver(testCredentialsSchema),
    defaultValues: { username: '', password: '', target_url: '' },
    mode: 'onTouched'
  });

  const createHttpsEnabled = useWatch({ control: createForm.control, name: 'https_enabled' });
  const editHttpsEnabled = useWatch({ control: settingsForm.control, name: 'https_enabled' });

  const usersQuery = useQuery({
    queryKey: ['users', selectedInstance?.name],
    queryFn: () => (selectedInstance ? getUsers(selectedInstance.name) : Promise.resolve({ users: [] })),
    enabled: isSettingsOpen && settingsTab === 'users' && Boolean(selectedInstance)
  });

  const certificateQuery = useQuery<Awaited<ReturnType<typeof getCertificateInfo>>>({
    queryKey: ['cert', selectedInstance?.name],
    queryFn: () =>
      selectedInstance
        ? getCertificateInfo(selectedInstance.name)
        : Promise.resolve({ status: 'missing' }),
    enabled: isSettingsOpen && settingsTab === 'certificate' && Boolean(selectedInstance)
  });

  const createMutation = useMutation({
    mutationFn: createInstance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      setAddOpen(false);
    }
  });

  const startMutation = useMutation({
    mutationFn: startInstance,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['instances'] })
  });

  const stopMutation = useMutation({
    mutationFn: stopInstance,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['instances'] })
  });

  const updateMutation = useMutation({
    mutationFn: ({
      name,
      payload
    }: {
      name: string;
      payload: { port: number; https_enabled: boolean };
    }) => updateInstance(name, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      setSettingsOpen(false);
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteInstance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      setSettingsOpen(false);
    }
  });

  const addUserMutation = useMutation({
    mutationFn: ({ name, username, password }: { name: string; username: string; password: string }) =>
      addUser(name, username, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', selectedInstance?.name] });
      userForm.reset({ username: '', password: '' });
      setUserError('');
    }
  });

  const removeUserMutation = useMutation({
    mutationFn: ({ name, username }: { name: string; username: string }) => removeUser(name, username),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users', selectedInstance?.name] })
  });

  const testMutation = useMutation({
    mutationFn: ({
      name,
      username,
      password,
      target_url
    }: {
      name: string;
      username: string;
      password: string;
      target_url?: string;
    }) => testConnectivity(name, username, password, target_url)
  });

  const regenerateMutation = useMutation({
    mutationFn: regenerateCertificates,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['instances'] })
  });

  const clearLogsMutation = useMutation({
    mutationFn: ({ name, type }: { name: string; type: 'cache' | 'access' }) => clearLogs(name, type),
    onSuccess: () => {
      if (selectedInstance) {
        void handleSelectLog(selectedInstance, logType);
      }
    }
  });

  const handleSelectLog = async (instance: ProxyInstance, type: 'cache' | 'access') => {
    setLogContent('Loading logs...');
    const response = await getLogs(instance.name, type);
    setLogContent(response);
  };

  const handleOpenSettings = (
    instance: ProxyInstance,
    tab: 'main' | 'users' | 'certificate' | 'logs' | 'test' | 'status' | 'delete' = 'main'
  ) => {
    setSelectedInstance(instance);
    settingsForm.reset({
      port: instance.port,
      https_enabled: instance.https_enabled
    });
    testForm.reset({ username: '', password: '', target_url: '' });
    setSettingsTab(tab);
    setSettingsOpen(true);
    setUserError('');
    setDeleteError('');
    setTestResult('');
    setLogContent('Loading logs...');
  };

  const handleChangeSettingsTab = (
    tab: 'main' | 'users' | 'certificate' | 'logs' | 'test' | 'status' | 'delete'
  ) => {
    setSettingsTab(tab);
    if (tab === 'logs') {
      setLogContent('Loading logs...');
    }
    if (tab === 'test') {
      testForm.reset({ username: '', password: '', target_url: '' });
      setTestResult('');
    }
    if (tab === 'users') {
      setUserError('');
    }
    if (tab === 'delete') {
      setDeleteError('');
    }
  };

  useEffect(() => {
    if (isSettingsOpen && settingsTab === 'logs' && selectedInstance) {
      void handleSelectLog(selectedInstance, logType);
    }
  }, [isSettingsOpen, settingsTab, selectedInstance, logType]);

  const handleCreate = createForm.handleSubmit(async (values) => {
    const parsed = createInstanceSchema.parse(values);
    const payload = {
      name: parsed.name,
      port: parsed.port,
      https_enabled: parsed.https_enabled,
      users: []
    };

    await createMutation.mutateAsync(payload);
    createForm.reset(createDefaults);
  });

  const handleUpdate = settingsForm.handleSubmit(async (values) => {
    if (!selectedInstance) return;
    const parsed = updateInstanceSchema.parse(values);
    await updateMutation.mutateAsync({
      name: selectedInstance.name,
      payload: {
        port: parsed.port,
        https_enabled: parsed.https_enabled
      }
    });
  });

  const handleAddUser = userForm.handleSubmit(async (values) => {
    if (!selectedInstance) return;
    try {
      await addUserMutation.mutateAsync({
        name: selectedInstance.name,
        username: values.username,
        password: values.password
      });
    } catch (error) {
      const message =
        typeof error === 'object' && error && 'message' in error
          ? String((error as { message: string }).message)
          : 'Unable to add user.';
      setUserError(message);
    }
  });

  const handleRemoveUser = async (username: string) => {
    if (!selectedInstance) return;
    await removeUserMutation.mutateAsync({ name: selectedInstance.name, username });
  };

  const handleDelete = async () => {
    if (!selectedInstance) return;
    setDeleteError('');
    try {
      await deleteMutation.mutateAsync(selectedInstance.name);
    } catch (error) {
      const message =
        typeof error === 'object' && error && 'message' in error
          ? String((error as { message: string }).message)
          : 'Unable to delete instance.';
      setDeleteError(message);
    }
  };

  const handleTest = testForm.handleSubmit(async (values) => {
    if (!selectedInstance) return;
    setTestResult('Testing connectivity...');
    try {
      const response = await testMutation.mutateAsync({
        name: selectedInstance.name,
        username: values.username,
        password: values.password,
        target_url: values.target_url || undefined
      });
      setTestResult(response.message ?? response.status);
    } catch (error) {
      const message =
        typeof error === 'object' && error && 'message' in error
          ? String((error as { message: string }).message)
          : 'Connectivity test failed.';
      setTestResult(message);
    }
  });

  const handleRegenerateCerts = async () => {
    if (!selectedInstance) return;
    await regenerateMutation.mutateAsync(selectedInstance.name);
  };

  const createErrors = createForm.formState.errors;
  const settingsErrors = settingsForm.formState.errors;

  return (
    <div className="min-h-screen bg-app-bg px-6 py-6 text-text-primary">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-5">
        <header className="flex h-[81px] items-center justify-between border-b border-white/10 bg-[#1c1c1c] px-6">
          <div className="flex items-center gap-3">
            <span className="text-[36px] leading-10 text-[#e1e1e1]">🦑</span>
            <div>
              <h1 className="text-2xl font-normal leading-8 text-[#e1e1e1]">Squid Proxy Manager</h1>
              <p className="flex items-center gap-2 text-xs leading-4 text-text-secondary">
                <span>Instances: {instances.length}</span>
                <span>•</span>
                <span className="h-1.5 w-1.5 rounded-full bg-success" />
                <span>Running: {runningCount}</span>
              </p>
            </div>
          </div>
          <Button
            className="h-11 w-[158px] rounded-[12px] bg-[#03a9f4] px-6 text-sm font-medium text-white shadow-none hover:bg-[#039be5]"
            onClick={() => setAddOpen(true)}
          >
            <PlusIcon className="mr-2 h-4 w-4" />
            Add Instance
          </Button>
        </header>

        <section className="space-y-4">
          {instancesQuery.isLoading && (
            <Card>
              <p className="text-sm text-text-secondary">Loading instances…</p>
            </Card>
          )}

          {instancesQuery.isError && (
            <Card>
              <p className="text-sm text-danger">Failed to load instances.</p>
            </Card>
          )}

          {!instancesQuery.isLoading && instances.length === 0 && (
            <Card>
              <p className="text-sm text-text-secondary">No instances configured yet.</p>
            </Card>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            {instances.map((instance) => (
              <div
                key={instance.name}
                className="instance-card h-[168px] rounded-[16px] bg-[#1c1c1c] px-6 pb-5 pt-5 shadow-[0_2px_8px_rgba(0,0,0,0.4)]"
                data-instance={instance.name}
                data-status={instance.running ? 'running' : 'stopped'}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-7">
                    <ServerIcon
                      className={cn('mt-0.5 h-6 w-6', instance.https_enabled ? 'text-danger' : 'text-success')}
                    />
                    <div>
                      <h3 className="text-sm font-medium leading-[21px] text-[#e1e1e1]">
                        {instance.name || 'Proxy'}
                      </h3>
                      <p className="text-xs leading-4 text-text-secondary">Port: {instance.port}</p>
                      <p className="text-xs leading-4 text-text-secondary">
                        HTTPS: {instance.https_enabled ? 'Enabled' : 'Disabled'}
                        {typeof instance.user_count === 'number' ? ` · Users: ${instance.user_count}` : ''}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-base leading-6 text-[#e1e1e1]">
                    <span className={cn('h-2 w-2 rounded-full', instance.running ? 'bg-success' : 'bg-danger')} />
                    <span>{instance.running ? 'Running' : 'Stopped'}</span>
                  </div>
                </div>
                <div className="mt-4 border-t border-border-subtle/70 pt-4">
                  <div className="flex items-center gap-2 -ml-3">
                    <Button
                      className="start-btn h-9 w-[238px] rounded-[12px] border border-white/10 bg-transparent px-3 text-sm font-medium text-[#e1e1e1] hover:bg-white/5 disabled:text-text-muted disabled:opacity-50"
                      variant="ghost"
                      size="sm"
                      disabled={instance.running}
                      onClick={() => startMutation.mutate(instance.name)}
                    >
                      <PlayIcon className="mr-2 h-4 w-4" />
                      Start
                    </Button>
                    <Button
                      className="stop-btn h-9 w-[238px] rounded-[12px] border border-white/10 bg-transparent px-3 text-sm font-medium text-[#e1e1e1] hover:bg-white/5 disabled:text-text-muted disabled:opacity-50"
                      variant="ghost"
                      size="sm"
                      disabled={!instance.running}
                      onClick={() => stopMutation.mutate(instance.name)}
                    >
                      <StopIcon className="mr-2 h-4 w-4" />
                      Stop
                    </Button>
                    <div className="ml-auto flex items-center">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-9 w-9 rounded-[12px] border border-white/10 p-0 text-[#e1e1e1]"
                        onClick={() => handleOpenSettings(instance, 'main')}
                        aria-label="Settings"
                        data-action="settings"
                      >
                        <SettingsIcon className="h-5 w-5" />
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <Modal id="addInstanceModal" title="Add Instance" isOpen={isAddOpen} onClose={() => setAddOpen(false)} className="max-w-[520px]">
        <form className="grid gap-5" onSubmit={handleCreate}>
          <Input
            id="newName"
            label="Instance Name"
            autoComplete="off"
            {...createForm.register('name')}
            helperText={createErrors.name?.message}
          />
          <Input
            id="newPort"
            label="Port"
            type="number"
            autoComplete="off"
            {...createForm.register('port', { valueAsNumber: true })}
            helperText={createErrors.port?.message}
          />
          <Checkbox id="newHttps" label="Enable HTTPS (SSL)" {...createForm.register('https_enabled')} />
          {createHttpsEnabled ? (
            <p className="text-xs text-text-secondary">Certificate will be auto-generated</p>
          ) : null}
          <div id="newCertProgress" className={createMutation.isPending ? 'text-sm text-text-secondary' : 'hidden'}>
            Creating instance...
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" className="rounded-full px-6" type="button" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button id="createInstanceBtn" className="rounded-full px-6" type="submit" loading={createMutation.isPending}>
              Create Instance
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        id="settingsModal"
        title={selectedInstance ? selectedInstance.name : 'Settings'}
        isOpen={isSettingsOpen}
        onClose={() => setSettingsOpen(false)}
        className="max-w-[760px]"
      >
        <div className="flex flex-wrap items-center gap-4 border-b border-border-subtle pb-3">
          {[
            { id: 'main', label: 'Main' },
            { id: 'users', label: 'Users' },
            { id: 'certificate', label: 'Certificate' },
            { id: 'logs', label: 'Logs' },
            { id: 'test', label: 'Test' },
            { id: 'status', label: 'Status' },
            { id: 'delete', label: 'Delete Instance' }
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={cn(
                'border-b-2 pb-3 text-sm font-medium transition-colors',
                settingsTab === tab.id
                  ? 'border-info text-info'
                  : 'border-transparent text-text-secondary hover:text-text-primary'
              )}
              onClick={() =>
                handleChangeSettingsTab(
                  tab.id as 'main' | 'users' | 'certificate' | 'logs' | 'test' | 'status' | 'delete'
                )
              }
              data-tab={tab.id}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {settingsTab === 'main' ? (
          <form className="grid gap-6" onSubmit={handleUpdate} id="settingsMainTab">
            <Input
              id="editPort"
              label="Port"
              type="number"
              autoComplete="off"
              {...settingsForm.register('port', { valueAsNumber: true })}
              helperText={settingsErrors.port?.message}
            />
            <Checkbox id="editHttps" label="Enable HTTPS (SSL)" {...settingsForm.register('https_enabled')} />
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-[0.18em] text-text-secondary">Status</p>
              <div className="flex items-center gap-2 text-sm">
                <span className={cn('h-2 w-2 rounded-full', selectedInstance?.running ? 'bg-success' : 'bg-danger')} />
                <span className={selectedInstance?.running ? 'text-success' : 'text-danger'}>
                  {selectedInstance?.running ? 'Running' : 'Stopped'}
                </span>
              </div>
            </div>
            {editHttpsEnabled ? (
              <p className="text-xs text-text-secondary">Certificate will be auto-generated</p>
            ) : null}
            <div className="flex items-center justify-between pt-2">
              <Button variant="danger" className="rounded-full px-6" type="button" onClick={handleDelete}>
                Delete Instance
              </Button>
              <Button className="rounded-full px-6" type="submit" loading={updateMutation.isPending}>
                Save Changes
              </Button>
            </div>
          </form>
        ) : null}

        {settingsTab === 'users' ? (
          <div className="grid gap-5" id="settingsUsersTab">
            <div className="text-sm font-semibold text-text-primary">Add User</div>
            <div id="addUserProgress" className={addUserMutation.isPending ? 'text-sm text-text-secondary' : 'hidden'}>
              Updating users...
            </div>
            {userError && (
              <div
                id="userError"
                className="rounded-[12px] border border-danger/40 bg-danger/10 p-3 text-sm text-danger"
              >
                {userError}
              </div>
            )}
            <Input
              id="newUsername"
              label="Username"
              autoComplete="username"
              {...userForm.register('username')}
              helperText={userForm.formState.errors.username?.message}
            />
            <Input
              id="newPassword"
              label="Password"
              type="password"
              autoComplete="new-password"
              {...userForm.register('password')}
              helperText={userForm.formState.errors.password?.message}
            />
            <Button className="w-full rounded-full" onClick={() => void handleAddUser()} loading={addUserMutation.isPending}>
              Add User
            </Button>

            <div className="text-sm font-semibold text-text-primary">Existing Users</div>
            <div id="userList" className="space-y-2">
              {usersQuery.data?.users.map((user) => (
                <div
                  key={user.username}
                  className="user-item flex items-center justify-between rounded-[12px] border border-border-subtle px-4 py-2"
                >
                  <span className="text-sm text-text-primary">{user.username}</span>
                  <button
                    type="button"
                    className="text-xs font-medium text-danger hover:text-danger/80"
                    onClick={() => handleRemoveUser(user.username)}
                  >
                    Remove
                  </button>
                </div>
              ))}
              {usersQuery.data?.users.length === 0 && <p className="text-sm text-text-secondary">No users yet.</p>}
            </div>
          </div>
        ) : null}

        {settingsTab === 'certificate' ? (
          <div className="grid gap-5" id="settingsCertificateTab">
            {!editHttpsEnabled ? (
              <p className="text-sm text-text-secondary">Enable HTTPS to generate certificates.</p>
            ) : null}
            <div className="text-sm font-semibold text-text-primary">Certificate Information</div>
            {certificateQuery.isLoading ? (
              <p className="text-sm text-text-secondary">Loading certificate...</p>
            ) : null}
            {certificateQuery.isError ? (
              <p className="text-sm text-danger">Unable to load certificate details.</p>
            ) : null}
            {certificateQuery.data ? (
              <div className="grid gap-3 rounded-[14px] border border-border-subtle bg-input-bg p-4 text-sm">
                <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                  <span className="text-text-secondary">Expiry Date</span>
                  <span className="text-text-primary">{certificateQuery.data.not_valid_after ?? '—'}</span>
                </div>
                <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                  <span className="text-text-secondary">Common Name</span>
                  <span className="text-text-primary">{certificateQuery.data.common_name ?? '—'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Status</span>
                  <span className={certificateQuery.data.status === 'valid' ? 'text-success' : 'text-text-secondary'}>
                    {certificateQuery.data.status === 'valid' ? 'Valid ✓' : certificateQuery.data.status}
                  </span>
                </div>
              </div>
            ) : null}
            <div>
              <Button
                type="button"
                className="w-full rounded-full"
                onClick={() => void handleRegenerateCerts()}
                loading={regenerateMutation.isPending}
                disabled={!editHttpsEnabled}
              >
                Regenerate Certificate
              </Button>
            </div>
            {certificateQuery.data?.pem ? (
              <div className="space-y-2">
                <div className="text-sm font-semibold text-text-primary">Certificate Preview</div>
                <pre className="max-h-60 overflow-auto rounded-[14px] border border-border-subtle bg-app-bg/70 p-4 text-xs text-text-secondary">
                  {certificateQuery.data.pem}
                </pre>
              </div>
            ) : null}
          </div>
        ) : null}

        {settingsTab === 'logs' ? (
          <div className="grid gap-4" id="settingsLogsTab">
            <pre
              id="logContent"
              className="max-h-64 overflow-auto rounded-[14px] border border-border-subtle bg-app-bg p-4 text-xs text-text-secondary"
            >
              {logContent}
            </pre>
            <div className="flex justify-end">
              <button
                type="button"
                className="text-xs font-medium text-text-secondary hover:text-text-primary"
                onClick={() =>
                  selectedInstance && clearLogsMutation.mutate({ name: selectedInstance.name, type: logType })
                }
              >
                Clear Logs
              </button>
            </div>
          </div>
        ) : null}

        {settingsTab === 'test' ? (
          <div className="grid gap-5" id="settingsTestTab">
            <Input
              id="testUsername"
              label="Username"
              autoComplete="username"
              {...testForm.register('username')}
              helperText={testForm.formState.errors.username?.message}
            />
            <Input
              id="testPassword"
              label="Password"
              type="password"
              autoComplete="current-password"
              {...testForm.register('password')}
              helperText={testForm.formState.errors.password?.message}
            />
            <Input
              id="testTargetUrl"
              label="Target URL (optional)"
              autoComplete="off"
              {...testForm.register('target_url')}
              helperText={
                testForm.formState.errors.target_url?.message ?? 'URL to test proxy connection against'
              }
            />
            <div
              id="testResult"
              className="rounded-[14px] border border-border-subtle bg-input-bg p-4 text-sm text-text-secondary"
            >
              {testResult || 'Ready to test connectivity.'}
            </div>
            <div className="flex justify-end">
              <Button
                variant="success"
                className="w-full rounded-full"
                onClick={() => void handleTest()}
                loading={testMutation.isPending}
              >
                Run Test
              </Button>
            </div>
          </div>
        ) : null}

        {settingsTab === 'status' ? (
          <div className="grid gap-4" id="settingsStatusTab">
            <div className="rounded-[14px] border border-border-subtle bg-input-bg p-4 text-sm">
              <div className="flex justify-between">
                <span className="text-text-secondary">Status</span>
                <span>{selectedInstance?.running ? 'Running' : 'Stopped'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Port</span>
                <span>{selectedInstance?.port ?? '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">HTTPS</span>
                <span>{selectedInstance?.https_enabled ? 'Enabled' : 'Disabled'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Users</span>
                <span>{selectedInstance?.user_count ?? '—'}</span>
              </div>
            </div>
          </div>
        ) : null}

        {settingsTab === 'delete' ? (
          <div className="grid gap-4" id="settingsDeleteTab">
            <p id="deleteMessage" className="text-sm text-text-secondary">
              {selectedInstance
                ? `This action permanently removes ${selectedInstance.name} and its data.`
                : 'This action permanently removes the instance and its data.'}
            </p>
            {deleteError ? (
              <div className="rounded-[12px] border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
                {deleteError}
              </div>
            ) : null}
            <div id="deleteProgress" className={deleteMutation.isPending ? 'text-sm text-text-secondary' : 'hidden'}>
              Removing instance...
            </div>
            <div className="flex justify-end gap-3">
              <Button variant="secondary" className="rounded-full px-6" onClick={() => setSettingsOpen(false)}>
                Cancel
              </Button>
              <Button
                id="confirmDeleteBtn"
                variant="danger"
                className="rounded-full px-6"
                onClick={handleDelete}
                loading={deleteMutation.isPending}
              >
                Delete
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
