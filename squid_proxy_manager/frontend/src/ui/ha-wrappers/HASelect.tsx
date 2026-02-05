import { forwardRef, useEffect, useRef, useState } from 'react';
import type { MutableRefObject, Ref, SelectHTMLAttributes } from 'react';

interface HASelectOption {
  value: string;
  label: string;
}

interface HASelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  label: string;
  value: string;
  options: HASelectOption[];
  onChange: (value: string) => void;
  'data-testid'?: string;
}

function setRef<T>(ref: Ref<T> | undefined, value: T) {
  if (typeof ref === 'function') {
    ref(value);
  } else if (ref && 'current' in ref) {
    (ref as MutableRefObject<T>).current = value;
  }
}

export const HASelect = forwardRef<HTMLElement, HASelectProps>(function HASelect(
  {
    label,
    value,
    options,
    onChange,
    disabled,
    className,
    'data-testid': testId,
    ...props
  },
  forwardedRef
) {
  const ref = useRef<HTMLElement>(null);
  const fallbackRef = useRef<HTMLSelectElement>(null);
  const [internalValue, setInternalValue] = useState(value);
  const hasHaSelect = typeof customElements !== 'undefined' && Boolean(customElements.get('ha-select'));

  const resolvedValue = value ?? internalValue;

  useEffect(() => {
    if (hasHaSelect && ref.current) {
      setRef(forwardedRef, ref.current);
      return;
    }
    if (!hasHaSelect && fallbackRef.current) {
      setRef(forwardedRef, fallbackRef.current as unknown as HTMLElement);
    }
  }, [forwardedRef, hasHaSelect]);

  useEffect(() => {
    const el = ref.current;
    if (!el || !hasHaSelect) return;

    const target = el as {
      value?: string;
      label?: string;
      disabled?: boolean;
    };

    target.value = resolvedValue;
    target.label = label;
    target.disabled = Boolean(disabled);

    const handleChange = (event: Event) => {
      const nextValue = String((event.target as { value?: string }).value ?? '');
      setInternalValue(nextValue);
      onChange(nextValue);
    };

    el.addEventListener('selected', handleChange);
    el.addEventListener('change', handleChange);
    el.addEventListener('closed', handleChange);
    return () => {
      el.removeEventListener('selected', handleChange);
      el.removeEventListener('change', handleChange);
      el.removeEventListener('closed', handleChange);
    };
  }, [disabled, hasHaSelect, label, onChange, resolvedValue]);

  if (hasHaSelect) {
    return (
      <ha-select
        ref={ref}
        label={label}
        value={resolvedValue}
        disabled={disabled}
        className={className}
        data-testid={testId}
        {...props}
      >
        {options.map((option) => (
          <mwc-list-item key={option.value} value={option.value}>
            {option.label}
          </mwc-list-item>
        ))}
      </ha-select>
    );
  }

  // Fallback: native select
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {label && <span style={{ fontSize: '14px', fontWeight: 500 }}>{label}</span>}
      <select
        ref={fallbackRef}
        value={resolvedValue}
        disabled={disabled}
        onChange={(event) => {
          const nextValue = event.target.value;
          setInternalValue(nextValue);
          onChange(nextValue);
        }}
        style={{
          padding: '8px 12px',
          border: '1px solid var(--divider-color, rgba(225,225,225,0.12))',
          borderRadius: '4px',
          backgroundColor: 'var(--secondary-background-color, #282828)',
          color: 'var(--primary-text-color, #e1e1e1)',
          fontSize: '14px',
          outline: 'none',
        }}
        data-testid={testId}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
});
