import { forwardRef, useEffect, useRef, useState } from 'react';
import type { InputHTMLAttributes, MutableRefObject, Ref } from 'react';

interface HATextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  label: string;
  helperText?: string;
  suffix?: string;
  type?: 'text' | 'number' | 'password' | 'email' | 'url';
  min?: string | number;
  max?: string | number;
  'data-testid'?: string;
  onChange?: (event: { target: { name?: string; value: string; type?: string } }) => void;
}

function setRef<T>(ref: Ref<T> | undefined, value: T) {
  if (typeof ref === 'function') {
    ref(value);
  } else if (ref && 'current' in ref) {
    (ref as MutableRefObject<T>).current = value;
  }
}

export const HATextField = forwardRef<HTMLElement, HATextFieldProps>(function HATextField(
  {
    id,
    name,
    label,
    helperText,
    className,
    type = 'text',
    disabled,
    required,
    min,
    max,
    placeholder,
    suffix,
    value,
    defaultValue,
    onChange,
    onBlur,
    'data-testid': testId
  },
  forwardedRef
) {
  const ref = useRef<HTMLElement>(null);
  const fallbackRef = useRef<HTMLInputElement>(null);
  const [internalValue, setInternalValue] = useState(String(defaultValue ?? ''));
  const isControlled = value !== undefined;
  const resolvedValue = isControlled ? String(value ?? '') : internalValue;
  const hasHaTextField = typeof customElements !== 'undefined' && Boolean(customElements.get('ha-textfield'));

  useEffect(() => {
    if (hasHaTextField && ref.current) {
      setRef(forwardedRef, ref.current);
      return;
    }
    if (!hasHaTextField && fallbackRef.current) {
      setRef(forwardedRef, fallbackRef.current as unknown as HTMLElement);
    }
  }, [forwardedRef, hasHaTextField]);

  useEffect(() => {
    const el = ref.current;
    if (!el || !hasHaTextField) return;

    const target = el as {
      value?: string;
      label?: string;
      type?: string;
      disabled?: boolean;
      required?: boolean;
      min?: number;
      max?: number;
      placeholder?: string;
      suffix?: string;
      name?: string;
      id?: string;
    };

    target.value = resolvedValue;
    target.label = label;
    target.type = String(type);
    target.disabled = Boolean(disabled);
    target.required = Boolean(required);
    target.name = name;
    target.id = id;
    target.placeholder = placeholder;
    if (min !== undefined) target.min = Number(min);
    if (max !== undefined) target.max = Number(max);
    if (suffix !== undefined) target.suffix = suffix;

    const handleInput = (event: Event) => {
      const nextValue = String((event.target as { value?: string }).value ?? '');
      if (!isControlled) {
        setInternalValue(nextValue);
      }
      onChange?.({ target: { name, value: nextValue, type: String(type) } });
    };

    const handleBlur = () => {
      onBlur?.({} as never);
    };

    el.addEventListener('input', handleInput);
    el.addEventListener('change', handleInput);
    el.addEventListener('blur', handleBlur);
    return () => {
      el.removeEventListener('input', handleInput);
      el.removeEventListener('change', handleInput);
      el.removeEventListener('blur', handleBlur);
    };
  }, [
    disabled,
    hasHaTextField,
    id,
    isControlled,
    label,
    max,
    min,
    name,
    onBlur,
    onChange,
    placeholder,
    required,
    resolvedValue,
    suffix,
    type
  ]);

  const fieldName = name ?? id;
  const handleNativeChange = (nextValue: string) => {
    if (!isControlled) {
      setInternalValue(nextValue);
    }
    onChange?.({ target: { name, value: nextValue, type: String(type) } });
  };

  return (
    hasHaTextField ? (
      <ha-textfield
        ref={ref}
        id={id}
        name={fieldName}
        label={label}
        data-testid={testId}
        className={className}
        type={type}
        value={resolvedValue}
        disabled={disabled}
        required={required}
        min={min}
        max={max}
        placeholder={placeholder}
        suffix={suffix}
      />
    ) : (
      <label style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <span style={{ fontSize: '14px', fontWeight: 500 }}>{label}</span>
        <span data-testid={testId}>
          <input
            ref={fallbackRef}
            id={id}
            name={fieldName}
            type={type}
            value={resolvedValue}
            disabled={disabled}
            required={required}
            min={min}
            max={max}
            placeholder={placeholder}
            onChange={(event) => handleNativeChange(event.target.value)}
            onBlur={onBlur}
            style={{
              width: '100%',
              padding: '8px 12px',
              border: '1px solid var(--divider-color, rgba(225,225,225,0.12))',
              borderRadius: '4px',
              backgroundColor: 'var(--card-background-color, #1c1c1c)',
              color: 'var(--primary-text-color, #e1e1e1)',
              fontSize: '14px',
              boxSizing: 'border-box',
            }}
          />
        </span>
        {helperText ? <span style={{ fontSize: '13px', color: 'var(--secondary-text-color, #9b9b9b)' }}>{helperText}</span> : null}
      </label>
    )
  );
});
