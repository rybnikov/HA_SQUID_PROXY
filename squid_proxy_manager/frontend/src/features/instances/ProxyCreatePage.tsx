import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';

import { createInstanceSchema, type CreateInstanceFormInput } from './validation';

import { createInstance } from '@/api/instances';
import { Button } from '@/ui/Button';
import { Card } from '@/ui/Card';
import { Checkbox } from '@/ui/Checkbox';
import { Input } from '@/ui/Input';
import { Select } from '@/ui/Select';

const defaults: CreateInstanceFormInput = {
  name: '',
  port: 3128,
  https_enabled: false,
  cert_params: {
    common_name: '',
    validity_days: 365,
    key_size: 2048
  }
};

export function ProxyCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const form = useForm<CreateInstanceFormInput>({
    resolver: zodResolver(createInstanceSchema),
    defaultValues: defaults,
    mode: 'onTouched'
  });
  const httpsEnabled = form.watch('https_enabled');

  const createMutation = useMutation({
    mutationFn: createInstance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      navigate('/');
    }
  });

  const handleCreate = form.handleSubmit(async (values) => {
    const parsed = createInstanceSchema.parse(values);
    await createMutation.mutateAsync({
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
    });
  });

  const errors = form.formState.errors;

  return (
    <div className="min-h-screen bg-surface px-6 py-10 text-foreground">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <header className="space-y-2">
          <p className="text-xs uppercase tracking-[0.5em] text-muted-foreground">Create proxy</p>
          <h1 className="text-3xl font-semibold">New proxy instance</h1>
          <p className="text-sm text-muted-foreground">
            Provision a new Squid proxy with optional HTTPS support.
          </p>
        </header>
        <Card title="Instance details" subtitle="Fill in the required fields">
          <form className="grid gap-4" onSubmit={handleCreate}>
            <Input
              label="Instance name"
              {...form.register('name')}
              helperText={errors.name?.message}
            />
            <Input
              label="Port"
              type="number"
              {...form.register('port', { valueAsNumber: true })}
              helperText={errors.port?.message}
            />
            <Checkbox label="Enable HTTPS" {...form.register('https_enabled')} />
            <div className={httpsEnabled ? 'grid gap-3' : 'hidden'}>
              <Input
                label="Certificate CN"
                {...form.register('cert_params.common_name')}
                helperText={errors.cert_params?.common_name?.message}
              />
              <Input
                label="Validity (days)"
                type="number"
                {...form.register('cert_params.validity_days', { valueAsNumber: true })}
                helperText={errors.cert_params?.validity_days?.message}
              />
              <Select
                label="Key size"
                {...form.register('cert_params.key_size', { valueAsNumber: true })}
              >
                <option value={2048}>2048</option>
                <option value={4096}>4096</option>
              </Select>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => navigate('/')}>Cancel</Button>
              <Button type="submit" loading={createMutation.isPending}>
                Create Instance
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
