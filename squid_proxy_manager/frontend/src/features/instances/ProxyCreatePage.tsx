import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, useWatch } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';

import { createInstanceSchema, type CreateInstanceFormInput } from './validation';

import { createInstance } from '@/api/instances';
import { Button } from '@/ui/Button';
import { Card } from '@/ui/Card';
import { Checkbox } from '@/ui/Checkbox';
import { Input } from '@/ui/Input';

const defaults: CreateInstanceFormInput = {
  name: '',
  port: 3128,
  https_enabled: false
};

export function ProxyCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const form = useForm<CreateInstanceFormInput>({
    resolver: zodResolver(createInstanceSchema),
    defaultValues: defaults,
    mode: 'onTouched'
  });
  const httpsEnabled = useWatch({ control: form.control, name: 'https_enabled' });
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
      users: []
    });
  });

  const errors = form.formState.errors;

  return (
    <div className="min-h-screen bg-app-bg px-4 sm:px-6 py-6 sm:py-10 text-text-primary">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <header className="space-y-2">
          <p className="text-xs uppercase tracking-[0.5em] text-text-secondary">Create proxy</p>
          <h1 className="text-2xl sm:text-3xl font-semibold">New proxy instance</h1>
          <p className="text-sm text-text-secondary">
            Provision a new Squid proxy with optional HTTPS support.
          </p>
        </header>
        <Card title="Instance details" subtitle="Fill in the required fields">
          <form className="grid gap-4" onSubmit={handleCreate}>
            <Input
              id="createName"
              label="Instance Name"
              autoComplete="off"
              {...form.register('name')}
              helperText={errors.name?.message}
            />
            <Input
              id="createPort"
              label="Port"
              type="number"
              autoComplete="off"
              {...form.register('port', { valueAsNumber: true })}
              helperText={errors.port?.message}
            />
            <Checkbox id="createHttps" label="Enable HTTPS (SSL)" {...form.register('https_enabled')} />
            {httpsEnabled ? (
              <p className="text-xs text-text-secondary">Certificate will be auto-generated</p>
            ) : null}
            <div className="flex flex-col sm:flex-row justify-end gap-2">
              <Button type="button" variant="secondary" className="w-full sm:w-auto rounded-full px-6" onClick={() => navigate('/')}>
                Cancel
              </Button>
              <Button type="submit" className="w-full sm:w-auto rounded-full px-6" loading={createMutation.isPending}>
                Create Instance
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
