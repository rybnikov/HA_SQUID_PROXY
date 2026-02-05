/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'app-bg': 'var(--color-app-bg)',
        'card-bg': 'var(--color-card-bg)',
        'modal-bg': 'var(--color-modal-bg)',
        'input-bg': 'var(--color-input-bg)',
        'border-subtle': 'var(--color-border-subtle)',
        'border-default': 'var(--color-border-default)',
        info: 'var(--color-info)',
        'text-primary': 'var(--color-foreground)',
        'text-secondary': 'var(--color-muted-foreground)',
        'text-muted': 'var(--color-text-muted)',
        primary: 'var(--color-primary)',
        surface: 'var(--color-surface)',
        muted: 'var(--color-muted)',
        foreground: 'var(--color-foreground)',
        'muted-foreground': 'var(--color-muted-foreground)',
        accent: 'var(--color-accent)',
        danger: 'var(--color-danger)',
        success: 'var(--color-success)',
        warning: 'var(--color-warning)'
      },
      borderRadius: {
        card: '12px',
        pill: '999px'
      },
      boxShadow: {
        card: '0 2px 6px rgba(0, 0, 0, 0.15)',
        modal: '0 8px 28px rgba(0, 0, 0, 0.28)'
      }
    }
  },
  plugins: []
};
