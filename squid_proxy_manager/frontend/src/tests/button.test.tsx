import { render, screen } from '@testing-library/react';

import { Button } from '@/ui/Button';

describe('Button', () => {
  it('renders label', () => {
    render(<Button>Launch</Button>);
    expect(screen.getByRole('button', { name: 'Launch' })).toBeInTheDocument();
  });

  it('shows loading spinner and disables when loading', () => {
    render(<Button loading>Saving</Button>);
    const button = screen.getByRole('button', { name: 'Saving' }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.querySelector('span')).not.toBeNull();
  });
});
