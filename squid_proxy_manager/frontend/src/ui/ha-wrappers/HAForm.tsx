import { useEffect, useMemo, useRef } from 'react';

import { HASwitch } from './HASwitch';
import { HATextField } from './HATextField';

type HAFormFieldType = 'string' | 'integer' | 'boolean';

export interface HAFormFieldSchema {
  name: string;
  label: string;
  type: HAFormFieldType;
  testId?: string;
  required?: boolean;
  disabled?: boolean;
  min?: number;
  max?: number;
  placeholder?: string;
  helperText?: string;
}

interface HAFormProps {
  schema: readonly HAFormFieldSchema[];
  data: Record<string, string | number | boolean | undefined>;
  onChange: (next: Record<string, string | number | boolean | undefined>) => void;
  disabled?: boolean;
  className?: string;
  'data-testid'?: string;
  hass?: unknown;
}

export function HAForm({
  schema,
  data,
  onChange,
  disabled,
  className,
  'data-testid': testId,
  hass
}: HAFormProps) {
  const hasHaForm = useMemo(
    () => typeof customElements !== 'undefined' && Boolean(customElements.get('ha-form')),
    []
  );
  const hostRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<(HTMLElement & {
    schema?: unknown;
    data?: unknown;
    disabled?: boolean;
    computeLabel?: (item: { name: string }) => string;
    computeHelper?: (item: { name: string }) => string | undefined;
    hass?: unknown;
  }) | null>(null);
  const resolvedHass = hass ?? window.__HASS__;

  useEffect(() => {
    if (!hasHaForm) return;
    const host = hostRef.current;
    if (!host || formRef.current) return;

    const el = document.createElement('ha-form') as HTMLElement & {
      schema?: unknown;
      data?: unknown;
      disabled?: boolean;
      computeLabel?: (item: { name: string }) => string;
      computeHelper?: (item: { name: string }) => string | undefined;
    };

    formRef.current = el;
    host.appendChild(el);

    return () => {
      el.remove();
      formRef.current = null;
    };
  }, [hasHaForm]);

  useEffect(() => {
    if (!hasHaForm || !formRef.current) return;

    const el = formRef.current;
    el.schema = schema.map((item) => ({
      name: item.name,
      selector:
        item.type === 'boolean'
          ? { boolean: {} }
          : item.type === 'integer'
            ? { number: { mode: 'box', min: item.min, max: item.max } }
            : { text: { type: 'text' } },
      required: item.required,
      disabled: item.disabled
    }));
    el.data = data;
    el.disabled = Boolean(disabled);
    el.computeLabel = (item) => schema.find((field) => field.name === item.name)?.label ?? item.name;
    el.computeHelper = (item) => schema.find((field) => field.name === item.name)?.helperText;
    if (resolvedHass) {
      el.hass = resolvedHass;
    }
  }, [data, disabled, hasHaForm, resolvedHass, schema]);

  useEffect(() => {
    if (!hasHaForm || !formRef.current) return;
    const el = formRef.current;
    const handleValueChanged = (event: Event) => {
      const detail = (event as CustomEvent<{ value?: Record<string, unknown> }>).detail;
      if (detail?.value) {
        onChange(detail.value as Record<string, string | number | boolean | undefined>);
      }
    };

    el.addEventListener('value-changed', handleValueChanged);
    return () => el.removeEventListener('value-changed', handleValueChanged);
  }, [hasHaForm, onChange]);

  if (hasHaForm) {
    return <div ref={hostRef} data-testid={testId} className={className} />;
  }

  return (
    <div data-testid={testId} className={className}>
      <div className="grid gap-4">
        {schema.map((field) => {
          const fieldValue = data[field.name];
          if (field.type === 'boolean') {
            return (
              <HASwitch
                key={field.name}
                label={field.label}
                disabled={disabled || field.disabled}
                checked={Boolean(fieldValue)}
                data-testid={field.testId ?? `${field.name}-switch`}
                onChange={(event) =>
                  onChange({
                    ...data,
                    [field.name]: Boolean(event.target.checked)
                  })
                }
              />
            );
          }

          return (
            <HATextField
              key={field.name}
              label={field.label}
              type={field.type === 'integer' ? 'number' : 'text'}
              value={String(fieldValue ?? '')}
              disabled={disabled || field.disabled}
              required={field.required}
              min={field.min}
              max={field.max}
              placeholder={field.placeholder}
              helperText={field.helperText}
              data-testid={
                field.testId ?? `${field.name}-input`
              }
              onChange={(event) =>
                onChange({
                  ...data,
                  [field.name]:
                    field.type === 'integer'
                      ? Number.parseInt(event.target.value || '0', 10) || 0
                      : event.target.value
                })
              }
            />
          );
        })}
      </div>
    </div>
  );
}
