# Design Guidelines - Squid Proxy Manager UI

**Version**: 1.5.0 | **Framework**: React 19 + Vite + Tailwind CSS 4 + HA Web Components | **Design System**: Figma-based tokens

## Table of Contents

1. [Design System Overview](#design-system-overview)
2. [Color Palette](#color-palette)
3. [Typography](#typography)
4. [Components & Patterns](#components--patterns)
5. [Modal & Dialog Design](#modal--dialog-design)
6. [Forms & Validation](#forms--validation)
7. [Responsive Design](#responsive-design)
8. [Accessibility](#accessibility)
9. [Async States & Loading](#async-states--loading)
10. [Error Handling & Messages](#error-handling--messages)
11. [Figma & Design Tokens](#figma--design-tokens)
12. [Testing Design with Playwright](#testing-design-with-playwright)

---

## Design System Overview

### Core Principles

1. **Modal-First UI**: All configuration and management in modals (no page navigation for settings)
2. **Dashboard-Centric**: Home page shows all instances as cards with quick actions
3. **Accessibility First**: WCAG 2.1 Level AA compliance required
4. **Responsive**: Mobile-first, works on phone/tablet/desktop
5. **Dark Mode Ready**: Support for both light and dark themes
6. **Consistent**: All modals follow same tab + form + button pattern
7. **Feedback**: Every async action shows loading state + success/error feedback

### Project Structure

```
squid_proxy_manager/frontend/src/
├── features/                    # Feature-based pages
│   └── instances/               # Instance management
│       ├── DashboardPage.tsx    # Dashboard with instance cards
│       ├── ProxyCreatePage.tsx  # Create new instance
│       ├── InstanceSettingsPage.tsx # Instance settings
│       └── tabs/               # Settings tab panels
├── ui/                          # Reusable components
│   └── ha-wrappers/            # HA web component wrappers
│       ├── HAButton.tsx
│       ├── HASwitch.tsx
│       ├── HATextField.tsx
│       ├── HACard.tsx
│       ├── HADialog.tsx
│       └── HATabGroup.tsx
├── api/                        # API client + mock data
│   └── client.ts
├── app/                        # App setup (router, ingress)
├── types/                      # TypeScript types
│   └── ha-components.d.ts
└── ha-panel.tsx                # HA panel entry point
```

### Tech Stack

| Layer | Technology | Version | Config |
|-------|-----------|---------|--------|
| **Build** | Vite | 7.x | `vite.config.ts` |
| **Framework** | React | 19.x | Strict mode, concurrent features |
| **Styling** | Tailwind CSS | 4.x | `tailwind.config.js` (custom tokens) |
| **Type Safety** | TypeScript | 5.x | `strict: true` in `tsconfig.json` |
| **State** | TanStack Query | v5 | Server state management |
| **Testing** | Vitest + React Testing Library | Latest | `squid_proxy_manager/frontend/vitest.config.ts` |
| **Linting** | ESLint + Prettier | Latest | `.eslintrc`, `.prettierrc` |

---

## Color Palette

### Tailwind CSS Custom Config

**File**: `squid_proxy_manager/frontend/tailwind.config.js`

```javascript
module.exports = {
  theme: {
    colors: {
      // Grays (neutral)
      gray: { 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950 },

      // Status colors
      success: { 50, 100, 200, ..., 900 },   // Green (#10B981)
      warning: { 50, 100, 200, ..., 900 },   // Amber (#F59E0B)
      error: { 50, 100, 200, ..., 900 },     // Red (#EF4444)
      info: { 50, 100, 200, ..., 900 },      // Blue (#3B82F6)

      // Brand colors
      primary: { 50, 100, 200, ..., 900 },   // Use brand color if defined

      // Semantic
      border: 'var(--color-border)',          // From design tokens
      background: 'var(--color-background)',
      text: 'var(--color-text)',
    },
  },
};
```

### Usage Examples

```tsx
// Status indicators
<div className="bg-success-100 text-success-900">✅ Running</div>
<div className="bg-error-100 text-error-900">❌ Failed</div>
<div className="bg-warning-100 text-warning-900">⚠️ Warning</div>

// Buttons
<button className="bg-primary-600 hover:bg-primary-700 text-white">Primary</button>
<button className="bg-gray-200 hover:bg-gray-300 text-gray-900">Secondary</button>

// Borders & dividers
<div className="border border-gray-300"></div>
<hr className="my-4 border-gray-200" />
```

---

## Typography

### Font Stack

```css
/* tailwind.config.js */
fontFamily: {
  sans: ['Inter', 'system-ui', 'sans-serif'],      /* Default */
  mono: ['Fira Code', 'JetBrains Mono', 'monospace'], /* Code */
}
```

### Scale & Usage

| Type | Size | Weight | Example | Tailwind Class |
|------|------|--------|---------|---|
| **Heading 1** | 32px | 700 | Page title | `text-4xl font-bold` |
| **Heading 2** | 24px | 700 | Section title | `text-2xl font-bold` |
| **Heading 3** | 20px | 600 | Subsection | `text-xl font-semibold` |
| **Body** | 16px | 400 | Regular text | `text-base font-normal` |
| **Small** | 14px | 400 | Helper text | `text-sm font-normal` |
| **Label** | 12px | 600 | Form labels | `text-xs font-semibold` |
| **Code** | 14px | 400 | `<code>` blocks | `text-sm font-mono` |

### Examples

```tsx
// Headings
<h1 className="text-4xl font-bold">Squid Proxy Manager</h1>
<h2 className="text-2xl font-bold text-gray-800">Instances</h2>

// Body text
<p className="text-base text-gray-700">
  Manage multiple proxy instances with custom auth and HTTPS.
</p>

// Labels & hints
<label className="text-xs font-semibold text-gray-600">Instance Name</label>
<span className="text-sm text-gray-500">Required field</span>

// Code/terminal
<code className="text-sm font-mono bg-gray-100 p-2 rounded">
  curl -x localhost:3128 http://example.com
</code>
```

---

## Components & Patterns

### Feature-Based Architecture

Each feature has its own folder with component, logic, and tests:

```
features/instances/
├── InstanceList.tsx              # List view
├── InstanceCard.tsx              # Card component
├── AddInstanceModal.tsx           # Add instance modal (5 tabs)
├── InstanceSettingsModal.tsx      # Settings modal (5 tabs)
├── InstanceActions.tsx            # Action buttons (Start/Stop/Delete)
└── tests/
    ├── InstanceList.test.tsx
    ├── AddInstanceModal.test.tsx
    └── InstanceSettingsModal.test.tsx
```

### Reusable UI Components

**File**: `squid_proxy_manager/frontend/src/ui/`

```
ui/
├── Button.tsx                   # Primary, secondary, danger, disabled states
├── Modal.tsx                    # Base modal wrapper
├── TabbedModal.tsx              # Modal with tabs
├── Form.tsx                     # Form wrapper with validation
├── FormField.tsx                # Input wrapper with label + error
├── TextInput.tsx                # Text input
├── TextArea.tsx                 # Textarea
├── Select.tsx                   # Dropdown
├── Checkbox.tsx                 # Checkbox
├── Radio.tsx                    # Radio button
├── Badge.tsx                    # Status badge (running, stopped, etc.)
├── Toast.tsx                    # Toast notifications (success, error, warning)
├── Spinner.tsx                  # Loading spinner
├── ConfirmModal.tsx             # Delete/confirm dialogs
└── ErrorBoundary.tsx            # Error boundary wrapper
```

### Button Patterns

```tsx
// Primary (call-to-action)
<Button variant="primary" onClick={handleCreate}>
  Create Instance
</Button>

// Secondary (alternative action, outlined style)
<Button variant="secondary" onClick={handleCancel}>
  Cancel
</Button>

// Instance control buttons (Start, Stop, Settings) - outlined style
<Button variant="secondary" size="sm" onClick={handleStart}>
  <PlayIcon className="mr-2 h-4 w-4" />
  Start
</Button>
<Button variant="secondary" size="sm" onClick={handleStop}>
  <StopIcon className="mr-2 h-4 w-4" />
  Stop
</Button>
<Button variant="secondary" size="sm" onClick={handleSettings}>
  <SettingsIcon className="h-5 w-5" />
</Button>

// Danger (destructive)
<Button variant="danger" onClick={handleDelete}>
  Delete
</Button>

// Disabled (loading or unavailable)
<Button disabled>
  <Spinner size="sm" className="mr-2" />
  Creating...
</Button>

// Icon button (compact)
<Button icon={<TrashIcon />} variant="ghost" onClick={handleDelete} />
```

### Modal Patterns

**Rule**: Use custom HTML modals, NOT `window.confirm()` (blocked in HA ingress iframes)

```tsx
// Delete confirmation modal
<ConfirmModal
  isOpen={showDeleteConfirm}
  title="Delete Instance"
  message={`Are you sure you want to delete "${instanceName}"? This cannot be undone.`}
  confirmText="Delete"
  cancelText="Cancel"
  onConfirm={handleConfirmDelete}
  onCancel={() => setShowDeleteConfirm(false)}
  isDangerous={true}  // Red confirmation button
/>

// Error modal
<Modal isOpen={showError} onClose={handleCloseError} title="Error">
  <div className="text-error-700 mb-4">{errorMessage}</div>
  <Button onClick={handleCloseError}>Close</Button>
</Modal>

// Success toast (auto-hide)
<Toast
  type="success"
  message="Instance created successfully!"
  autoClose={3000}
  onClose={handleToastClose}
/>
```

---

## Modal & Dialog Design

### Modal Structure (All Modals Follow This Pattern)

```tsx
<Modal
  isOpen={isOpen}
  onClose={handleClose}
  title="Modal Title"
  size="lg"  // sm, md (default), lg, xl
  closeButton={true}
>
  {/* Tabs (if multi-step) */}
  <TabbedModal tabs={['Tab 1', 'Tab 2', 'Tab 3']}>
    {/* Tab 1 content */}
    {/* Tab 2 content */}
    {/* Tab 3 content */}
  </TabbedModal>

  {/* Or single content */}
  <div className="space-y-4">
    <FormField label="Field Name">
      <TextInput placeholder="..." />
    </FormField>
  </div>

  {/* Buttons (sticky bottom) */}
  <div className="flex gap-3 justify-end mt-6 pt-4 border-t">
    <Button variant="secondary" onClick={handleCancel}>Cancel</Button>
    <Button variant="primary" onClick={handleSubmit} disabled={isLoading}>
      {isLoading ? <Spinner /> : 'Save'}
    </Button>
  </div>
</Modal>
```

### Responsive Tab Layout (v1.4.5+)

**New Design Pattern**: Tabs are responsive - vertical on tablet/desktop, horizontal on mobile.

```tsx
{/* Mobile: Horizontal scrollable tabs, Tablet/Desktop: Vertical tabs */}
<div className="flex flex-col md:flex-row gap-4 md:gap-6">
  {/* Tabs Navigation */}
  <div className="flex md:flex-col overflow-x-auto md:overflow-x-visible md:min-w-[180px] gap-2 md:gap-1 border-b md:border-b-0 md:border-r border-border-subtle pb-3 md:pb-0 md:pr-4">
    {tabs.map((tab) => (
      <button
        key={tab.id}
        type="button"
        className={cn(
          'flex-shrink-0 md:w-full text-left px-3 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap',
          activeTab === tab.id
            ? 'bg-info/10 text-info border-l-2 md:border-l-4 border-info'
            : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
        )}
        onClick={() => setActiveTab(tab.id)}
        data-tab={tab.id}
      >
        {tab.label}
      </button>
    ))}
  </div>

  {/* Tab Content - Scrollable */}
  <div className="flex-1 overflow-y-auto max-h-[60vh] md:max-h-[500px] pr-2">
    <div className="space-y-6">
      {activeTab === 'tab1' ? <Tab1Content /> : null}
      {activeTab === 'tab2' ? <Tab2Content /> : null}
      {/* ... */}
    </div>
  </div>
</div>
```

**Key Features**:
- **Mobile (<768px)**: Horizontal tabs with overflow scroll, vertical content
- **Tablet/Desktop (≥768px)**: Vertical tabs on left (180px wide), content on right
- **Scrollable Content**: max-h-[60vh] on mobile, max-h-[500px] on desktop prevents modal overflow
- **Active Indicator**: Left border (2px mobile, 4px desktop) + background color
- **No Horizontal Jumps**: overflow-y-auto ensures consistent width

### Modal Tab Patterns

**Add Instance Modal** (5 tabs):
1. **Basic**: Name, Port, HTTPS toggle
2. **HTTPS Settings**: CN, Org, Country, Validity, Key Size, Generate Button
3. **Users**: Add/remove users inline
4. **Test**: Test connectivity button + status display
5. (Optional) **Review**: Summary before creation

**Settings Modal** (7 tabs - v1.4.5+)**:
1. **Main**: Port, HTTPS toggle, Status, Delete Instance button
2. **Users**: List users, Add/Remove buttons
3. **Certificate**: Show cert info, Regenerate button
4. **Logs**: Log viewer with dropdown + search
5. **Test**: Connectivity test
6. **Status**: Instance status details
7. **Delete Instance**: Confirmation UI with warning
3. **Users**: List users, Add/Remove buttons
4. **Test**: Connectivity test
5. **Logs**: Log viewer with dropdown + search

---

## Forms & Validation

### Form Field Component

```tsx
// Standard field with label + error
<FormField
  label="Instance Name"
  error={errors.name}
  required={true}
>
  <TextInput
    placeholder="e.g., office-proxy"
    value={name}
    onChange={(e) => setName(e.target.value)}
  />
</FormField>

// With hint text
<FormField
  label="Port"
  hint="Range: 3128-3140"
  error={errors.port}
>
  <TextInput
    type="number"
    min="3128"
    max="3140"
    value={port}
    onChange={(e) => setPort(e.target.value)}
  />
</FormField>

// Select dropdown
<FormField label="Log File" required>
  <Select value={logFile} onChange={(e) => setLogFile(e.target.value)}>
    <option value="">-- Select --</option>
    <option value="access.log">Access Log</option>
    <option value="cache.log">Cache Log</option>
  </Select>
</FormField>

// Checkbox
<FormField>
  <Checkbox
    label="Enable HTTPS"
    checked={httpsEnabled}
    onChange={(e) => setHttpsEnabled(e.target.checked)}
  />
</FormField>
```

### Validation Patterns

```tsx
// React Hook Form + Zod schema
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const createInstanceSchema = z.object({
  name: z.string().min(1, 'Name required').max(255),
  port: z.number().min(3128).max(3140),
  httpsEnabled: z.boolean(),
  cn: z.string().optional(),
});

export function AddInstanceForm() {
  const { register, formState: { errors }, watch, handleSubmit } = useForm({
    resolver: zodResolver(createInstanceSchema),
  });

  const httpsEnabled = watch('httpsEnabled');

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <FormField label="Name" error={errors.name?.message}>
        <TextInput {...register('name')} />
      </FormField>

      <FormField label="Port" error={errors.port?.message}>
        <TextInput type="number" {...register('port', { valueAsNumber: true })} />
      </FormField>

      <FormField>
        <Checkbox label="Enable HTTPS" {...register('httpsEnabled')} />
      </FormField>

      {httpsEnabled && (
        <FormField label="Certificate CN" error={errors.cn?.message}>
          <TextInput {...register('cn')} />
        </FormField>
      )}

      <Button type="submit">Create</Button>
    </form>
  );
}
```

---

## Responsive Design

### Breakpoints (Tailwind CSS)

| Breakpoint | Width | Device | Usage |
|-----------|-------|--------|-------|
| **sm** | 640px | Tablet | Small screens |
| **md** | 768px | Tablet | Medium screens |
| **lg** | 1024px | Desktop | Large screens |
| **xl** | 1280px | Desktop | Extra large |
| **2xl** | 1536px | Desktop | Ultra-wide |

### Mobile-First Approach

```tsx
// Mobile first, then tablet/desktop overrides
<div className="
  grid grid-cols-1          /* Mobile: 1 column */
  sm:grid-cols-2            /* Tablet: 2 columns */
  lg:grid-cols-3            /* Desktop: 3 columns */
  gap-4
">
  {/* Cards */}
</div>

// Responsive padding
<div className="p-4 md:p-6 lg:p-8">
  Content with mobile-optimized padding
</div>

// Responsive text
<h1 className="text-2xl md:text-3xl lg:text-4xl font-bold">
  Title scales with screen
</h1>

// Hide/show by breakpoint
<div className="hidden md:block">Desktop only</div>
<div className="md:hidden">Mobile only</div>
```

### Layout Patterns

```tsx
// Sidebar layout (desktop) → stacked (mobile)
<div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
  <aside className="lg:col-span-1">Sidebar</aside>
  <main className="lg:col-span-3">Content</main>
</div>

// Modal responsive
<Modal size={isMobile ? "full" : "lg"} className="w-full md:max-w-lg">
  {/* Fills screen on mobile, fixed size on desktop */}
</Modal>

// Table responsive (horizontal scroll on mobile)
<div className="overflow-x-auto">
  <table className="w-full text-sm">
    {/* Scrollable on mobile, full width on desktop */}
  </table>
</div>
```

---

## Accessibility

### WCAG 2.1 Level AA Requirements

**All new components must**:

1. ✅ **Semantic HTML**: Use `<button>`, `<label>`, `<form>` elements
2. ✅ **ARIA Labels**: Add `aria-label` for icon-only buttons
3. ✅ **Color Contrast**: Text must have 4.5:1 contrast ratio (WCAG AA)
4. ✅ **Keyboard Navigation**: All interactive elements must be keyboard accessible
5. ✅ **Focus Indicators**: Visible focus outline on all focusable elements
6. ✅ **Form Labels**: Every input has associated `<label>`
7. ✅ **Error Messaging**: Errors linked to inputs via `aria-describedby`
8. ✅ **Loading States**: Announce async operations with `aria-busy`

### Examples

```tsx
// Accessible button
<button
  className="p-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
  aria-label="Delete instance" // For icon-only buttons
>
  <TrashIcon />
</button>

// Accessible form field
<div>
  <label htmlFor="instance-name" className="block text-sm font-semibold">
    Instance Name
  </label>
  <input
    id="instance-name"
    type="text"
    aria-describedby="name-error"  // Links to error message
    aria-required="true"
    required
  />
  {error && (
    <div id="name-error" className="text-error-700 text-sm mt-1">
      {error}
    </div>
  )}
</div>

// Accessible loading indicator
<div role="status" aria-busy={isLoading} aria-label="Creating instance...">
  {isLoading ? <Spinner /> : null}
</div>

// Accessible modal
<Modal role="dialog" aria-labelledby="modal-title">
  <h2 id="modal-title">Confirm Delete</h2>
  {/* Content */}
</Modal>
```

### Testing Accessibility

```bash
# Axe accessibility audit (in tests)
npm run test -- --include="*.a11y.test.tsx"

# Manual browser testing with axe DevTools
# 1. Install: https://www.deque.com/axe/devtools/
# 2. Run scan on component
# 3. Fix HIGH/CRITICAL issues
```

---

## Async States & Loading

### Loading State Patterns

```tsx
// Inline spinner with text
<div className="flex items-center gap-2">
  <Spinner size="sm" />
  <span>Creating instance...</span>
</div>

// Button with loading state
<Button
  disabled={isLoading}
  onClick={handleCreate}
>
  {isLoading ? (
    <>
      <Spinner size="sm" className="mr-2" />
      Creating...
    </>
  ) : (
    'Create Instance'
  )}
</Button>

// Skeleton loader (while data loads)
<div className="space-y-2">
  <Skeleton height="h-8 w-48" />  {/* Title */}
  <Skeleton height="h-4 w-full" />  {/* Content line 1 */}
  <Skeleton height="h-4 w-5/6" />    {/* Content line 2 */}
</div>

// Overlay loading (for modals)
{isLoading && (
  <div className="absolute inset-0 bg-black/20 rounded-lg flex items-center justify-center">
    <Spinner />
  </div>
)}
```

### TanStack Query Integration

```tsx
import { useQuery, useMutation } from '@tanstack/react-query';

// Fetch data
const { data: instances, isLoading, error } = useQuery({
  queryKey: ['instances'],
  queryFn: async () => {
    const res = await fetch('/api/instances');
    return res.json();
  },
});

// Handle loading/error states
if (isLoading) return <Spinner />;
if (error) return <ErrorMessage message={error.message} />;

// Mutation (create/update/delete)
const { mutate: createInstance, isPending } = useMutation({
  mutationFn: async (data) => {
    const res = await fetch('/api/instances', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return res.json();
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['instances'] });
    showSuccessToast('Instance created!');
  },
  onError: (err) => {
    showErrorToast(err.message);
  },
});

return (
  <Button
    onClick={() => createInstance(formData)}
    disabled={isPending}
  >
    {isPending ? <Spinner /> : 'Create'}
  </Button>
);
```

---

## Error Handling & Messages

### Error Message Hierarchy

```
High severity (red):     User lost data or security issue
Medium severity (amber): Feature partially unavailable
Low severity (blue):     Informational or retry-able
```

### Error Display Patterns

```tsx
// Inline field error
<FormField error="Port must be 3128-3140">
  <TextInput value={port} onChange={...} />
</FormField>

// Form-level error
<div className="bg-error-50 border border-error-200 rounded-lg p-4 mb-4">
  <h3 className="font-semibold text-error-900">Failed to create instance</h3>
  <p className="text-error-700 text-sm">{error.message}</p>
</div>

// Toast notification
<Toast type="error" message="Port 3128 already in use" />

// Modal with error state
<Modal isOpen={showError} onClose={handleClose} title="Error">
  <div className="flex gap-3">
    <AlertIcon className="text-error-600 flex-shrink-0" />
    <div>
      <h3 className="font-semibold text-error-900">{error.title}</h3>
      <p className="text-error-700 text-sm">{error.message}</p>
      {error.details && (
        <pre className="mt-2 bg-gray-100 p-2 rounded text-xs overflow-auto">
          {error.details}
        </pre>
      )}
    </div>
  </div>
  <Button onClick={handleClose} className="mt-4">Close</Button>
</Modal>

// Network error with retry
<div className="text-center py-8">
  <AlertTriangleIcon className="mx-auto mb-4 text-warning-600" size={48} />
  <p className="text-gray-700 mb-4">Failed to load instances</p>
  <Button onClick={handleRetry}>Retry</Button>
</div>
```

### Error Messages (User-Friendly)

❌ **BAD**: "400: Invalid request body"
✅ **GOOD**: "Port must be a number between 3128 and 3140"

❌ **BAD**: "NullPointerException in proxy_manager.py"
✅ **GOOD**: "Failed to start instance. Check logs for details."

❌ **BAD**: "401 Unauthorized"
✅ **GOOD**: "Your session expired. Please refresh the page."

---

## Figma & Design Tokens

### Design System in Figma

**File**: Figma project (shared with team)

**Structure**:
```
├── Components
│   ├── Button (Primary, Secondary, Danger, Disabled)
│   ├── Modal (Base, Tabbed, Confirmation)
│   ├── Form Fields (Text, Select, Checkbox, Radio)
│   ├── Badge (Running, Stopped, Failed, Warning)
│   ├── Notifications (Toast, Alert, Error)
│   └── [Component]
├── Patterns
│   ├── Dashboard Card
│   ├── Instance List
│   ├── Settings Modal
│   └── [Pattern]
├── Styles
│   ├── Colors (Dark/Light themes)
│   ├── Typography (Headings, Body, Labels)
│   ├── Shadows & Borders
│   └── Spacing Grid
└── Pages
    ├── Dashboard
    ├── Instances
    ├── Settings
    └── [Page]
```

### Design Token Export

**Token Format** (CSS variables):
```css
/* Colors */
--color-primary-50: #f0f9ff;
--color-primary-500: #3b82f6;
--color-primary-900: #1e3a8a;

/* Typography */
--font-family-sans: 'Inter', sans-serif;
--font-size-h1: 32px;
--font-weight-bold: 700;

/* Spacing */
--spacing-1: 4px;
--spacing-2: 8px;
--spacing-4: 16px;

/* Shadows */
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);

/* Border Radius */
--radius-sm: 4px;
--radius-md: 8px;
--radius-lg: 12px;
```

### Tailwind Config Integration

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: 'var(--color-primary-50)',
          500: 'var(--color-primary-500)',
          900: 'var(--color-primary-900)',
        },
      },
      fontSize: {
        h1: ['32px', { fontWeight: '700' }],
      },
      spacing: {
        4: '16px',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
      },
    },
  },
};
```

### Design Token Validation

```bash
# Verify tokens match between Figma and code
npm run validate:tokens

# Run test to ensure exported tokens are in use
npm run test -- --grep="design-tokens"
```

---

## Testing Design with Playwright

### Visual Regression Testing

```bash
# Take reference screenshots
npm run test:visual:update

# Run visual tests (will fail if UI changes)
npm run test:visual

# Compare screenshots side-by-side on CI failure
# Artifacts: test-results/visual-diffs/
```

### Component Testing

```typescript
// squid_proxy_manager/frontend/src/features/instances/tests/AddInstanceModal.test.tsx
import { render, screen, userEvent } from '@testing-library/react';
import { AddInstanceModal } from '../AddInstanceModal';

describe('AddInstanceModal', () => {
  it('displays all 5 tabs', () => {
    render(<AddInstanceModal isOpen={true} onClose={() => {}} />);

    expect(screen.getByText('Basic')).toBeInTheDocument();
    expect(screen.getByText('HTTPS Settings')).toBeInTheDocument();
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('Test')).toBeInTheDocument();
    expect(screen.getByText('Review')).toBeInTheDocument();
  });

  it('enables tab 2 only when HTTPS toggled on', async () => {
    render(<AddInstanceModal isOpen={true} onClose={() => {}} />);

    const httpsToggle = screen.getByRole('checkbox', { name: /enable https/i });
    await userEvent.click(httpsToggle);

    const httpsSettingsTab = screen.getByRole('button', { name: /https settings/i });
    expect(httpsSettingsTab).not.toHaveClass('opacity-50');
  });

  it('submits form with all required fields', async () => {
    const onSuccess = vi.fn();
    render(<AddInstanceModal isOpen={true} onSuccess={onSuccess} />);

    await userEvent.type(screen.getByPlaceholderText('Instance name'), 'test-proxy');
    await userEvent.selectOption(screen.getByRole('combobox', { name: /port/i }), '3128');
    await userEvent.click(screen.getByRole('button', { name: /create instance/i }));

    expect(onSuccess).toHaveBeenCalledWith({ name: 'test-proxy', port: 3128 });
  });
});
```

### Playwright MCP for Design Inspection

**Using Playwright MCP in IDE** (e.g., VS Code):

```bash
# Install Playwright Inspector
npm install -D @playwright/inspector

# Launch test with inspector
npx playwright test --debug

# In Playwright Inspector:
# - Hover over elements to inspect
# - Pause on click/hover to see state
# - Record interactions as tests
# - Take screenshots at any point
```

**Recording UI Interaction**:
```bash
# Generate test by recording interaction
npx playwright codegen http://localhost:5173

# In recorder:
# 1. Click elements on app
# 2. Playwright generates test code
# 3. Copy code to test file
# 4. Enhance with assertions
```

### Responsive Design Testing

```typescript
// Test component on multiple viewports
import { test, expect } from '@playwright/test';

test.describe('AddInstanceModal - Responsive', () => {
  const viewports = [
    { name: 'Mobile', width: 375, height: 667 },
    { name: 'Tablet', width: 768, height: 1024 },
    { name: 'Desktop', width: 1280, height: 800 },
  ];

  for (const viewport of viewports) {
    test(`renders correctly on ${viewport.name}`, async ({ page }) => {
      page.setViewportSize(viewport);
      await page.goto('http://localhost:5173');

      // Modal should be visible and contain all tabs
      const modal = page.locator('[role="dialog"]');
      await expect(modal).toBeVisible();

      // Tabs should wrap or show correctly for viewport
      const tabs = page.locator('[role="tablist"] button');
      const count = await tabs.count();
      expect(count).toBe(5);

      // Take screenshot for visual inspection
      await expect(page).toHaveScreenshot(`modal-${viewport.name}.png`);
    });
  }
});
```

### Accessibility Testing

```typescript
// Axe accessibility audit
import { injectAxe, checkA11y } from 'axe-playwright';

test('modal meets WCAG 2.1 Level AA', async ({ page }) => {
  await page.goto('http://localhost:5173');

  // Inject axe and run audit
  await injectAxe(page);
  await checkA11y(page, '[role="dialog"]', {
    detailedReport: true,
    detailedReportOptions: {
      html: true,
    },
  });

  // Report violations
  const results = await page.evaluate(() => {
    return (window as any).axe.results;
  });

  expect(results.violations).toHaveLength(0);
});
```

---

## Design Checklist

Before submitting UI component/feature for review:

- [ ] **Visual Design**: Matches Figma mockups
- [ ] **Responsive**: Works on mobile (375px), tablet (768px), desktop (1280px)
- [ ] **Accessibility**: WCAG 2.1 AA compliant (colors, labels, keyboard nav)
- [ ] **States**: All states present (default, hover, active, disabled, loading, error)
- [ ] **Modals**: Uses custom HTML (not `window.confirm()`)
- [ ] **Forms**: All inputs have labels and error states
- [ ] **Loading**: Async operations show spinners + feedback
- [ ] **Errors**: Error messages are user-friendly
- [ ] **Consistency**: Follows component patterns from `ui/` folder
- [ ] **Tests**: Component has unit tests (>80% coverage)
- [ ] **Visual Regression**: Screenshots match baseline
- [ ] **Playwright MCP**: Tested with Playwright for interactions
- [ ] **Documentation**: Storybook or JSDoc comments added

---

## Resources

- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [React 19 Features](https://react.dev/blog/2024/12/19/react-19)
- [Accessibility Guidelines (WCAG)](https://www.w3.org/WAI/WCAG21/quickref/)
- [Figma Design System Setup](https://www.figma.com/design-systems/)
- [Playwright Testing Guide](https://playwright.dev/docs/intro)
- [Component Testing Best Practices](https://testing-library.com/docs/react-testing-library/intro/)

## HA-First Component Authority

When choosing UI primitives in ingress pages:

1. Prefer Home Assistant design system components (`ha-*`).
2. Use project wrappers in `src/ui/ha-wrappers/`.
3. Use custom Tailwind primitives only when HA does not provide the needed element.
4. Use `HAForm`/`ha-form` for proxy create and edit settings forms.
5. Follow integration-card structure for proxy instance cards.

### Wrapper Contracts

- Keep business logic in React feature pages.
- Keep UI primitive rendering in HA wrappers.
- Keep stable `data-testid` hooks on wrapper hosts.
- Avoid React synthetic event assumptions on web components; use native DOM events in wrappers.

### Official Home Assistant References

- https://design.home-assistant.io/#components/ha-form
- https://design.home-assistant.io/#components/ha-switch
- https://design.home-assistant.io/#misc/integration-card
- https://developers.home-assistant.io/docs/frontend/development
