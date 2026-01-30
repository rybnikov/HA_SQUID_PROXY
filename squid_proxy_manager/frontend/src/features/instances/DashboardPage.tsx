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
    <div className="min-h-screen bg-app-bg px-6 py-8 text-text-primary">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
        <header className="flex flex-col gap-4 border-b border-border-subtle bg-app-bg px-8 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-red-500 to-orange-500 text-2xl">
              🦑
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-text-primary">Squid Proxy Manager</h1>
              <p className="text-sm text-text-secondary">
                Instances: {instances.length} · Running: {runningCount}
              </p>
            </div>
          </div>
          <Button
            className="rounded-lg px-6 py-2 text-sm font-semibold"
            onClick={() => setAddOpen(true)}
          >
            + Add Instance
          </Button>
        </header>

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Instances</h2>
            <span className="text-sm text-text-secondary">{instances.length} total</span>
          </div>

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

          <div className="grid gap-6 md:grid-cols-2">
            {instances.map((instance) => (
              <div
                key={instance.name}
                className="instance-card rounded-[20px] border border-border-subtle bg-card-bg p-6 shadow-card"
                data-instance={instance.name}
                data-status={instance.running ? 'running' : 'stopped'}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={cn(
                      'flex h-14 w-14 items-center justify-center rounded-lg border text-2xl',
                      instance.https_enabled
                        ? 'border-danger bg-danger/20 text-danger'
                        : 'border-success bg-success/20 text-success'
                    )}
                  >
                    {instance.https_enabled ? '🔒' : '🧩'}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="text-lg font-semibold text-text-primary">
                          {instance.name || 'Proxy'}
                        </h3>
                        <p className="text-sm text-text-secondary">Port: {instance.port}</p>
                        <p className="text-sm text-text-secondary">
                          HTTPS: {instance.https_enabled ? 'Enabled' : 'Disabled'}
                          {typeof instance.user_count === 'number' ? ` · Users: ${instance.user_count}` : ''}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <span
                          className={cn(
                            'h-2.5 w-2.5 rounded-full',
                            instance.running ? 'bg-success' : 'bg-danger'
                          )}
                        />
                        <span className={instance.running ? 'text-success' : 'text-danger'}>
                          {instance.running ? 'Running' : 'Stopped'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-border-subtle pt-4">
                  <Button
                    className="start-btn rounded-lg px-5"
                    variant="secondary"
                    size="sm"
                    disabled={instance.running}
                    onClick={() => startMutation.mutate(instance.name)}
                  >
                    ▶ Start
                  </Button>
                  <Button
                    className="stop-btn rounded-lg px-5"
                    variant="secondary"
                    size="sm"
                    disabled={!instance.running}
                    onClick={() => stopMutation.mutate(instance.name)}
                  >
                    ■ Stop
                  </Button>
                  <div className="ml-auto flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-9 w-9 rounded-full border border-border-subtle p-0 text-lg"
                      onClick={() => handleOpenSettings(instance, 'main')}
                      aria-label="Settings"
                      data-action="settings"
                    >
                      ⚙
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <Modal id="addInstanceModal" title="Create instance" isOpen={isAddOpen} onClose={() => setAddOpen(false)}>
        <form className="grid gap-4" onSubmit={handleCreate}>
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
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" type="button" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button id="createInstanceBtn" type="submit" loading={createMutation.isPending}>
              Create Instance
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        id="settingsModal"
        title={selectedInstance ? `Settings: ${selectedInstance.name}` : 'Settings'}
        isOpen={isSettingsOpen}
        onClose={() => setSettingsOpen(false)}
        className="max-w-3xl"
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
                'border-b-2 pb-2 text-sm font-medium transition-colors',
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
          <form className="grid gap-4" onSubmit={handleUpdate} id="settingsMainTab">
            <Input
              id="editPort"
              label="Port"
              type="number"
              autoComplete="off"
              {...settingsForm.register('port', { valueAsNumber: true })}
              helperText={settingsErrors.port?.message}
            />
            <Checkbox id="editHttps" label="Enable HTTPS (SSL)" {...settingsForm.register('https_enabled')} />
            {editHttpsEnabled ? (
              <p className="text-xs text-text-secondary">Certificate will be auto-generated</p>
            ) : null}
            <div className="flex justify-end gap-2">
              <Button variant="secondary" type="button" onClick={() => setSettingsOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={updateMutation.isPending}>
                Save Changes
              </Button>
            </div>
          </form>
        ) : null}

        {settingsTab === 'users' ? (
          <div className="grid gap-4" id="settingsUsersTab">
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
            <Button className="w-full" onClick={() => void handleAddUser()} loading={addUserMutation.isPending}>
              Add User
            </Button>

            <div className="text-sm font-semibold text-text-primary">Existing Users</div>
            <div id="userList" className="space-y-2">
              {usersQuery.data?.users.map((user) => (
                <div
                  key={user.username}
                  className="user-item flex items-center justify-between rounded-[12px] border border-border-subtle px-3 py-2"
                >
                  <span>{user.username}</span>
                  <Button variant="ghost" size="sm" onClick={() => handleRemoveUser(user.username)}>
                    Remove
                  </Button>
                </div>
              ))}
              {usersQuery.data?.users.length === 0 && <p className="text-sm text-text-secondary">No users yet.</p>}
            </div>
          </div>
        ) : null}

        {settingsTab === 'certificate' ? (
          <div className="grid gap-4" id="settingsCertificateTab">
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
              <div className="grid gap-2 rounded-[12px] border border-border-subtle bg-input-bg p-4 text-sm">
                <div className="flex justify-between">
                  <span className="text-text-secondary">Expiry Date</span>
                  <span>{certificateQuery.data.not_valid_after ?? '—'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Common Name</span>
                  <span>{certificateQuery.data.common_name ?? '—'}</span>
                </div>
                <div className="flex justify-between">
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
                className="w-full"
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
                <pre className="max-h-60 overflow-auto rounded-[12px] border border-border-subtle bg-input-bg p-3 text-xs text-text-secondary">
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
              className="max-h-64 overflow-auto rounded-[12px] border border-border-subtle bg-app-bg p-3 text-xs text-text-secondary"
            >
              {logContent}
            </pre>
            <div className="flex justify-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() =>
                  selectedInstance && clearLogsMutation.mutate({ name: selectedInstance.name, type: logType })
                }
                loading={clearLogsMutation.isPending}
              >
                Clear Logs
              </Button>
            </div>
          </div>
        ) : null}

        {settingsTab === 'test' ? (
          <div className="grid gap-4" id="settingsTestTab">
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
              className="rounded-[12px] border border-border-subtle bg-input-bg p-3 text-sm text-text-secondary"
            >
              {testResult || 'Ready to test connectivity.'}
            </div>
            <div className="flex justify-end">
              <Button variant="success" className="w-full" onClick={() => void handleTest()} loading={testMutation.isPending}>
                Run Test
              </Button>
            </div>
          </div>
        ) : null}

        {settingsTab === 'status' ? (
          <div className="grid gap-4" id="settingsStatusTab">
            <div className="rounded-[12px] border border-border-subtle bg-input-bg p-4 text-sm">
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
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setSettingsOpen(false)}>
                Cancel
              </Button>
              <Button
                id="confirmDeleteBtn"
                variant="danger"
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
