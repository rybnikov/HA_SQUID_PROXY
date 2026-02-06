import { forwardRef, useEffect, useRef, useState } from 'react';
import type { InputHTMLAttributes, MutableRefObject, Ref } from 'react';

interface HASwitchProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange'> {
  label: string;
  'data-testid'?: string;
  onChange?: (event: {
    target: { name?: string; checked: boolean; value: string; type: 'checkbox' };
    currentTarget: { name?: string; checked: boolean; value: string; type: 'checkbox' };
  }) => void;
}

function setRef<T>(ref: Ref<T> | undefined, value: T) {
  if (typeof ref === 'function') {
    ref(value);
  } else if (ref && 'current' in ref) {
    (ref as MutableRefObject<T>).current = value;
  }
}

export const HASwitch = forwardRef<HTMLElement, HASwitchProps>(function HASwitch(
  { label, className, checked, defaultChecked, name, onBlur, onChange, disabled, 'data-testid': testId },
  forwardedRef
) {
  const ref = useRef<HTMLElement>(null);
  const fallbackRef = useRef<HTMLInputElement>(null);
  const [internalChecked, setInternalChecked] = useState(Boolean(defaultChecked));
  const hasHaSwitch = typeof customElements !== 'undefined' && Boolean(customElements.get('ha-switch'));

  const isControlled = typeof checked === 'boolean';
  const resolvedChecked = isControlled ? Boolean(checked) : internalChecked;

  useEffect(() => {
    if (hasHaSwitch && ref.current) {
      setRef(forwardedRef, ref.current);
      return;
    }
    if (!hasHaSwitch && fallbackRef.current) {
      setRef(forwardedRef, fallbackRef.current as unknown as HTMLElement);
    }
  }, [forwardedRef, hasHaSwitch]);

  useEffect(() => {
    const el = ref.current;
    if (!el || !hasHaSwitch) return;
    (el as { checked?: boolean }).checked = resolvedChecked;
    (el as { disabled?: boolean }).disabled = Boolean(disabled);
  }, [disabled, hasHaSwitch, resolvedChecked]);

  const handleNativeChange = (nextChecked: boolean) => {
    if (!isControlled) {
      setInternalChecked(nextChecked);
    }
    const eventLike = {
      target: {
        name,
        checked: nextChecked,
        value: nextChecked ? 'on' : 'off',
        type: 'checkbox' as const
      },
      currentTarget: {
        name,
        checked: nextChecked,
        value: nextChecked ? 'on' : 'off',
        type: 'checkbox' as const
      }
    };
    onChange?.(eventLike);
  };

  return (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}>
      <span style={{ fontSize: '14px' }}>{label}</span>
      <span
        data-testid={testId}
        data-checked={resolvedChecked ? 'true' : 'false'}
      >
        {hasHaSwitch ? (
          <ha-switch
            ref={ref}
            checked={resolvedChecked}
            disabled={disabled}
            onChange={(event) =>
              handleNativeChange(
                Boolean(
                  (event.target as { checked?: boolean } | null)?.checked ??
                    (ref.current as { checked?: boolean } | null)?.checked
                )
              )
            }
            onBlur={onBlur as never}
          />
        ) : (
          <input
            ref={fallbackRef}
            type="checkbox"
            name={name}
            checked={resolvedChecked}
            disabled={disabled}
            onChange={(event) => handleNativeChange(event.target.checked)}
            onBlur={onBlur}
            className={className}
          />
        )}
      </span>
    </label>
  );
});
