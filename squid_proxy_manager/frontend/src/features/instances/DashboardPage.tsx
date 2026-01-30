import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';

import {
  createInstanceSchema,
  testCredentialsSchema,
  updateInstanceSchema,
  userSchema,
  type CreateInstanceFormInput,
  type TestCredentialsValues,
  type UpdateInstanceFormInput,
  type UpdateInstanceFormValues,
  type UserFormValues
} from './validation';

import {
  addUser,
  createInstance,
  deleteInstance,
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
import { getStatus } from '@/api/status';
import { Badge } from '@/ui/Badge';
import { Button } from '@/ui/Button';
import { Card } from '@/ui/Card';
import { Checkbox } from '@/ui/Checkbox';
import { Input } from '@/ui/Input';
import { Modal } from '@/ui/Modal';
import { Select } from '@/ui/Select';

const statusTone: Record<ProxyInstance['status'], 'success' | 'warning' | 'danger' | 'info'> = {
  running: 'success',
  initializing: 'warning',
  stopped: 'danger',
  error: 'danger'
};

const createDefaults: CreateInstanceFormInput = {
  name: '',
  port: 3128,
  https_enabled: false,
  cert_params: {
    common_name: '',
    validity_days: 365,
    key_size: 2048
  }
};

export function DashboardPage() {
  const queryClient = useQueryClient();
  const statusQuery = useQuery({ queryKey: ['status'], queryFn: getStatus });
  const instancesQuery = useQuery({
    queryKey: ['instances'],
    queryFn: getInstances,
    refetchInterval: 10_000
  });

  const instances = useMemo(() => instancesQuery.data?.instances ?? [], [instancesQuery.data]);

  const [isAddOpen, setAddOpen] = useState(false);
  const [isUsersOpen, setUsersOpen] = useState(false);
  const [isLogsOpen, setLogsOpen] = useState(false);
  const [isSettingsOpen, setSettingsOpen] = useState(false);
  const [isTestOpen, setTestOpen] = useState(false);
  const [isDeleteOpen, setDeleteOpen] = useState(false);
  const [selectedInstance, setSelectedInstance] = useState<ProxyInstance | null>(null);

  const [logType, setLogType] = useState<'cache' | 'access'>('cache');
  const [logContent, setLogContent] = useState('Loading logs...');
  const [userError, setUserError] = useState('');
  const [testResult, setTestResult] = useState('');

  const createForm = useForm<CreateInstanceFormInput>({
    resolver: zodResolver(createInstanceSchema),
    defaultValues: createDefaults,
    mode: 'onTouched'
  });

  const settingsForm = useForm<UpdateInstanceFormInput>({
    resolver: zodResolver(updateInstanceSchema),
    defaultValues: {
      port: createDefaults.port,
      https_enabled: createDefaults.https_enabled,
      cert_params: createDefaults.cert_params
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
    defaultValues: { username: '', password: '' },
    mode: 'onTouched'
  });

  const createHttpsEnabled = createForm.watch('https_enabled');
  const editHttpsEnabled = settingsForm.watch('https_enabled');

  const usersQuery = useQuery({
    queryKey: ['users', selectedInstance?.name],
    queryFn: () => (selectedInstance ? getUsers(selectedInstance.name) : Promise.resolve({ users: [] })),
    enabled: isUsersOpen && Boolean(selectedInstance)
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
      payload: { port: number; https_enabled: boolean; cert_params?: UpdateInstanceFormValues['cert_params'] };
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
      setDeleteOpen(false);
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
    mutationFn: ({ name, username, password }: { name: string; username: string; password: string }) =>
      testConnectivity(name, username, password)
  });

  const regenerateMutation = useMutation({
    mutationFn: regenerateCertificates,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['instances'] })
  });

  const handleOpenUsers = (instance: ProxyInstance) => {
    setSelectedInstance(instance);
    setUsersOpen(true);
    setUserError('');
  };

  const handleOpenLogs = async (instance: ProxyInstance) => {
    setSelectedInstance(instance);
    setLogsOpen(true);
    setLogType('cache');
    setLogContent('Loading logs...');
    const response = await getLogs(instance.name, 'cache');
    setLogContent(response);
  };

  const handleSelectLog = async (type: 'cache' | 'access') => {
    if (!selectedInstance) return;
    setLogType(type);
    setLogContent('Loading logs...');
    const response = await getLogs(selectedInstance.name, type);
    setLogContent(response);
  };

  const handleOpenSettings = (instance: ProxyInstance) => {
    setSelectedInstance(instance);
    settingsForm.reset({
      port: instance.port,
      https_enabled: instance.https_enabled,
      cert_params: {
        common_name: '',
        validity_days: 365,
        key_size: 2048
      }
    });
    setSettingsOpen(true);
  };

  const handleOpenTest = (instance: ProxyInstance) => {
    setSelectedInstance(instance);
    testForm.reset({ username: '', password: '' });
    setTestResult('');
    setTestOpen(true);
  };

  const handleOpenDelete = (instance: ProxyInstance) => {
    setSelectedInstance(instance);
    setDeleteOpen(true);
  };

  const handleCreate = createForm.handleSubmit(async (values) => {
    const parsed = createInstanceSchema.parse(values);
    const payload = {
      name: parsed.name,
      port: parsed.port,
      https_enabled: parsed.https_enabled,
      users: [],
      cert_params: parsed.https_enabled
        ? {
            common_name: parsed.cert_params?.common_name ?? null,
            validity_days: parsed.cert_params?.validity_days,
            key_size: parsed.cert_params?.key_size
          }
        : undefined
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
        https_enabled: parsed.https_enabled,
        cert_params: parsed.https_enabled ? parsed.cert_params : undefined
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
    await deleteMutation.mutateAsync(selectedInstance.name);
  };

  const handleTest = testForm.handleSubmit(async (values) => {
    if (!selectedInstance) return;
    setTestResult('Testing connectivity...');
    const response = await testMutation.mutateAsync({
      name: selectedInstance.name,
      username: values.username,
      password: values.password
    });
    setTestResult(response.message ?? response.status);
  });

  const handleRegenerateCerts = async () => {
    if (!selectedInstance) return;
    await regenerateMutation.mutateAsync(selectedInstance.name);
  };

  const createErrors = createForm.formState.errors;
  const settingsErrors = settingsForm.formState.errors;

  return (
    <div className="min-h-screen bg-surface px-6 py-10 text-foreground">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.5em] text-muted-foreground">Squid Proxy Manager 🐙</p>
            <h1 className="text-3xl font-semibold">Proxy dashboard</h1>
            <p className="text-sm text-muted-foreground">Monitor and manage every proxy instance in one place.</p>
          </div>
          <Button onClick={() => setAddOpen(true)}>+ Add Instance</Button>
        </header>

        <Card
          title="Service status"
          subtitle={`Version ${statusQuery.data?.version ?? '—'}`}
          action={<Badge label={statusQuery.data?.status ?? 'unknown'} tone="info" />}
        >
          <p className="text-sm text-muted-foreground">
            {statusQuery.data?.manager_initialized ? 'Manager initialized' : 'Manager not initialized'}
          </p>
        </Card>

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Instances</h2>
            <span className="text-sm text-muted-foreground">{instances.length} total</span>
          </div>

          {instancesQuery.isLoading && (
            <Card>
              <p className="text-sm text-muted-foreground">Loading instances…</p>
            </Card>
          )}

          {instancesQuery.isError && (
            <Card>
              <p className="text-sm text-danger">Failed to load instances.</p>
            </Card>
          )}

          {!instancesQuery.isLoading && instances.length === 0 && (
            <Card>
              <p className="text-sm text-muted-foreground">No instances configured yet.</p>
            </Card>
          )}

          <div className="grid gap-6 md:grid-cols-2">
            {instances.map((instance) => (
              <div
                key={instance.name}
                className="instance-card rounded-card border border-muted bg-surface p-6 shadow-card"
                data-instance={instance.name}
                data-status={instance.running ? 'running' : 'stopped'}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.4em] text-muted-foreground">Instance</p>
                    <h3 className="text-xl font-semibold">{instance.name}</h3>
                    <p className="text-sm text-muted-foreground">Port {instance.port}</p>
                  </div>
                  <Badge
                    label={instance.running ? 'running' : 'stopped'}
                    tone={statusTone[instance.running ? 'running' : 'stopped']}
                  />
                </div>
                <div className="mt-4 text-sm text-muted-foreground">
                  HTTPS: <span className="text-foreground">{instance.https_enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
                <div className="mt-6 flex flex-wrap gap-2">
                  <Button
                    className="start-btn"
                    variant="secondary"
                    size="sm"
                    disabled={instance.running}
                    onClick={() => startMutation.mutate(instance.name)}
                  >
                    Start
                  </Button>
                  <Button
                    className="stop-btn"
                    variant="secondary"
                    size="sm"
                    disabled={!instance.running}
                    onClick={() => stopMutation.mutate(instance.name)}
                  >
                    Stop
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleOpenUsers(instance)}>
                    Users
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleOpenLogs(instance)}>
                    Logs
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleOpenSettings(instance)}>
                    Settings
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleOpenTest(instance)}>
                    Test
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => handleOpenDelete(instance)}>
                    Delete
                  </Button>
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
            label="Instance name"
            {...createForm.register('name')}
            helperText={createErrors.name?.message}
          />
          <Input
            id="newPort"
            label="Port"
            type="number"
            {...createForm.register('port', { valueAsNumber: true })}
            helperText={createErrors.port?.message}
          />
          <Checkbox id="newHttps" label="Enable HTTPS" {...createForm.register('https_enabled')} />
          <div id="newCertSettings" className={createHttpsEnabled ? 'grid gap-3' : 'hidden'}>
            <Input
              id="newCertCN"
              label="Certificate CN"
              {...createForm.register('cert_params.common_name')}
              helperText={createErrors.cert_params?.common_name?.message}
            />
            <Input
              id="newCertValidity"
              label="Validity (days)"
              type="number"
              {...createForm.register('cert_params.validity_days', { valueAsNumber: true })}
              helperText={createErrors.cert_params?.validity_days?.message}
            />
            <Select
              id="newCertKeySize"
              label="Key size"
              {...createForm.register('cert_params.key_size', { valueAsNumber: true })}
            >
              <option value={2048}>2048</option>
              <option value={4096}>4096</option>
            </Select>
          </div>
          <div id="newCertProgress" className={createMutation.isPending ? 'text-sm text-muted-foreground' : 'hidden'}>
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
        id="userModal"
        title={selectedInstance ? `Users: ${selectedInstance.name}` : 'Users'}
        isOpen={isUsersOpen}
        onClose={() => setUsersOpen(false)}
      >
        <div className="grid gap-4">
          <div id="addUserProgress" className={addUserMutation.isPending ? 'text-sm text-muted-foreground' : 'hidden'}>
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
          <div id="userList" className="space-y-2">
            {usersQuery.data?.users.map((user) => (
              <div
                key={user.username}
                className="user-item flex items-center justify-between rounded-[12px] border border-muted px-3 py-2"
              >
                <span>{user.username}</span>
                <Button variant="ghost" size="sm" onClick={() => handleRemoveUser(user.username)}>
                  Remove
                </Button>
              </div>
            ))}
            {usersQuery.data?.users.length === 0 && <p className="text-sm text-muted-foreground">No users yet.</p>}
          </div>
          <Input
            id="newUsername"
            label="Username"
            {...userForm.register('username')}
            helperText={userForm.formState.errors.username?.message}
          />
          <Input
            id="newPassword"
            label="Password"
            type="password"
            {...userForm.register('password')}
            helperText={userForm.formState.errors.password?.message}
          />
          <Button onClick={() => void handleAddUser()} loading={addUserMutation.isPending}>
            Add
          </Button>
        </div>
      </Modal>

      <Modal
        id="logModal"
        title={selectedInstance ? `Logs: ${selectedInstance.name}` : 'Logs'}
        isOpen={isLogsOpen}
        onClose={() => setLogsOpen(false)}
      >
        <div className="flex gap-2">
          <Button
            variant={logType === 'cache' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => handleSelectLog('cache')}
          >
            Cache Log
          </Button>
          <Button
            variant={logType === 'access' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => handleSelectLog('access')}
          >
            Access Log
          </Button>
        </div>
        <pre
          id="logContent"
          className="max-h-64 overflow-auto rounded-[12px] border border-muted bg-muted/30 p-3 text-xs text-muted-foreground"
        >
          {logContent}
        </pre>
      </Modal>

      <Modal
        id="settingsModal"
        title={selectedInstance ? `Settings: ${selectedInstance.name}` : 'Settings'}
        isOpen={isSettingsOpen}
        onClose={() => setSettingsOpen(false)}
      >
        <form className="grid gap-4" onSubmit={handleUpdate}>
          <Input
            id="editPort"
            label="Port"
            type="number"
            {...settingsForm.register('port', { valueAsNumber: true })}
            helperText={settingsErrors.port?.message}
          />
          <Checkbox id="editHttps" label="HTTPS enabled" {...settingsForm.register('https_enabled')} />
          <div id="editCertSettings" className={editHttpsEnabled ? 'grid gap-3' : 'hidden'}>
            <Input
              id="editCertCN"
              label="Certificate CN"
              {...settingsForm.register('cert_params.common_name')}
              helperText={settingsErrors.cert_params?.common_name?.message}
            />
            <Input
              id="editCertValidity"
              label="Validity (days)"
              type="number"
              {...settingsForm.register('cert_params.validity_days', { valueAsNumber: true })}
              helperText={settingsErrors.cert_params?.validity_days?.message}
            />
            <Select
              id="editCertKeySize"
              label="Key size"
              {...settingsForm.register('cert_params.key_size', { valueAsNumber: true })}
            >
              <option value={2048}>2048</option>
              <option value={4096}>4096</option>
            </Select>
            <div id="certActions" className="flex gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => void handleRegenerateCerts()}
                loading={regenerateMutation.isPending}
              >
                Regenerate Certificates
              </Button>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" type="button" onClick={() => setSettingsOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={updateMutation.isPending}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        id="testModal"
        title={selectedInstance ? `Test Connectivity: ${selectedInstance.name}` : 'Test Connectivity'}
        isOpen={isTestOpen}
        onClose={() => setTestOpen(false)}
      >
        <div className="grid gap-4">
          <Input
            id="testUsername"
            label="Username"
            {...testForm.register('username')}
            helperText={testForm.formState.errors.username?.message}
          />
          <Input
            id="testPassword"
            label="Password"
            type="password"
            {...testForm.register('password')}
            helperText={testForm.formState.errors.password?.message}
          />
          <div id="testResult" className="rounded-[12px] border border-muted bg-muted/40 p-3 text-sm text-muted-foreground">
            {testResult || 'Ready to test connectivity.'}
          </div>
          <div className="flex justify-end">
            <Button onClick={() => void handleTest()} loading={testMutation.isPending}>
              Run Test
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        id="deleteModal"
        title={selectedInstance ? `Delete ${selectedInstance.name}?` : 'Delete instance'}
        isOpen={isDeleteOpen}
        onClose={() => setDeleteOpen(false)}
      >
        <p id="deleteMessage" className="text-sm text-muted-foreground">
          {selectedInstance
            ? `This action permanently removes ${selectedInstance.name} and its data.`
            : 'This action permanently removes the instance and its data.'}
        </p>
        <div id="deleteProgress" className={deleteMutation.isPending ? 'text-sm text-muted-foreground' : 'hidden'}>
          Removing instance...
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteOpen(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDelete} loading={deleteMutation.isPending}>
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}
