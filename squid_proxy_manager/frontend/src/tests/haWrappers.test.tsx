import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { HAButton, HADialog, HASwitch, HATextField } from '@/ui/ha-wrappers';

describe('HA wrappers', () => {
  it('HAButton triggers onClick', () => {
    const onClick = vi.fn();
    render(<HAButton onClick={onClick}>Save</HAButton>);

    fireEvent.click(screen.getByText('Save'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('HASwitch emits checked state', async () => {
    const onChange = vi.fn();
    const originalGet = customElements.get.bind(customElements);
    const getSpy = vi
      .spyOn(customElements, 'get')
      .mockImplementation((name: string) => (name === 'ha-switch' ? undefined : originalGet(name)));
    render(<HASwitch label="Enable HTTPS" onChange={onChange} data-testid="https-switch" />);

    const container = screen.getByTestId('https-switch');
    const switchEl = container.querySelector('input[type="checkbox"]') as (HTMLElement & {
      checked?: boolean;
    }) | null;
    expect(switchEl).not.toBeNull();
    await new Promise((resolve) => setTimeout(resolve, 0));
    fireEvent.click(switchEl!);
    getSpy.mockRestore();

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        target: expect.objectContaining({ name: undefined, checked: true, type: 'checkbox' })
      })
    );
  });

  it('HATextField emits input value', () => {
    const onChange = vi.fn();
    render(<HATextField label="Name" data-testid="name-field" onChange={onChange} />);

    const field =
      (screen.getByTestId('name-field').querySelector('input') as (HTMLElement & { value?: string }) | null) ??
      (screen.getByTestId('name-field') as HTMLElement & { value?: string });
    expect(field).not.toBeNull();
    fireEvent.input(field!, { target: { value: 'proxy-1' } });

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        target: expect.objectContaining({ value: 'proxy-1', type: 'text' })
      })
    );
  });

  it('HADialog closes on backdrop click', () => {
    const onClose = vi.fn();
    render(
      <HADialog id="settingsModal" title="Settings" isOpen onClose={onClose}>
        <div>Content</div>
      </HADialog>
    );

    const dialog = document.getElementById('settingsModal') as HTMLElement | null;
    expect(dialog).not.toBeNull();
    fireEvent.click(dialog!);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
