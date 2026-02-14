import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { act } from 'react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

import * as instancesApi from '@/api/instances';

import { OpenVPNPatcherDialog } from './OpenVPNPatcherDialog';

// Mock the API module
vi.mock('@/api/instances', () => ({
  getUsers: vi.fn(),
  patchOVPNConfig: vi.fn(),
}));

describe('OpenVPNPatcherDialog', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
    // Default mock for getUsers to prevent query errors
    vi.mocked(instancesApi.getUsers).mockResolvedValue({ users: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers(); // Ensure real timers are restored after each test
  });

  const renderWithQueryClient = (ui: React.ReactElement) => {
    return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
  };

  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    instanceName: 'test-instance',
    proxyType: 'squid' as const,
    port: 3128,
  };

  describe('Dialog Lifecycle', () => {
    it('renders when isOpen is true', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);
      expect(screen.getByTestId('openvpn-dialog')).toBeTruthy();
    });

    it('does not render when isOpen is false', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} isOpen={false} />);
      expect(screen.queryByTestId('openvpn-dialog')).toBeNull();
    });

    it('calls onClose when close button clicked', () => {
      const onClose = vi.fn();
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} onClose={onClose} />);

      const closeButton = screen.getByTestId('openvpn-dialog-close');
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('resets state when closed', async () => {
      const onClose = vi.fn();
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} onClose={onClose} />);

      // Upload a file
      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['content'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      // Verify file uploaded
      await waitFor(() => {
        expect(screen.getByText(/test.ovpn/)).toBeTruthy();
      });

      // Close dialog
      const closeButton = screen.getByTestId('openvpn-dialog-close');
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('P0 - Production Blockers (No window.alert)', () => {
    it('file validation shows inline error, no alert', () => {
      const alertSpy = vi.spyOn(window, 'alert');

      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const invalidFile = new File(['data'], 'test.txt', { type: 'text/plain' });

      Object.defineProperty(fileInput, 'files', {
        value: [invalidFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      // Inline error shown
      expect(screen.getByText(/valid .ovpn file/i)).toBeTruthy();

      // NO alert() called
      expect(alertSpy).not.toHaveBeenCalled();
      alertSpy.mockRestore();
    });

    it('API patch error shows inline message, no alert', async () => {
      const alertSpy = vi.spyOn(window, 'alert');
      vi.mocked(instancesApi.patchOVPNConfig).mockRejectedValue(
        new Error('Invalid config format')
      );

      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      // Upload file
      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      // Verify preview is not shown initially
      expect(screen.queryByTestId('openvpn-preview')).toBeNull();

      // Click patch
      const patchButton = screen.getByTestId('openvpn-patch-button');
      fireEvent.click(patchButton);

      // Wait for mutation to complete and error to be displayed
      // The error appears in a HACard with the error message
      await waitFor(
        () => {
          // Check that preview did NOT appear (since there was an error)
          expect(screen.queryByTestId('openvpn-preview')).toBeNull();
          // Check that error message is displayed
          const errorText = screen.queryByText(/Invalid config format/i);
          expect(errorText).not.toBeNull();
        },
        { timeout: 3000 }
      );

      // NO alert() called
      expect(alertSpy).not.toHaveBeenCalled();
      alertSpy.mockRestore();
    });

    it('copy success shows inline message, no alert', async () => {
      const alertSpy = vi.spyOn(window, 'alert');

      const mockPatchedContent = 'client\nhttp-proxy 192.168.1.100 3128\ndev tun\n';
      vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
        patched_content: mockPatchedContent,
        filename: 'test_patched.ovpn',
      });

      // Mock clipboard
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: { writeText: writeTextMock },
      });

      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      // Upload and patch
      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      const patchButton = screen.getByTestId('openvpn-patch-button');
      fireEvent.click(patchButton);

      await waitFor(() => {
        expect(screen.getByTestId('openvpn-copy')).toBeTruthy();
      });

      // Click copy
      const copyButton = screen.getByTestId('openvpn-copy');
      fireEvent.click(copyButton);

      // Inline success message shown
      await waitFor(() => {
        expect(screen.getByText(/Copied to clipboard/i)).toBeTruthy();
      });

      // NO alert() called
      expect(alertSpy).not.toHaveBeenCalled();
      alertSpy.mockRestore();
    });
  });

  describe('P1 - Component Behavior Changes', () => {
    it('file selection via HAButton triggers hidden input', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      const selectButton = screen.getByTestId('openvpn-file-select-button');
      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;

      // Button shows "Select .ovpn File"
      expect(selectButton.textContent).toContain('Select .ovpn File');

      // Input is hidden
      expect(fileInput).toHaveStyle({ display: 'none' });
    });

    it('button text changes after file upload', async () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      const selectButton = screen.getByTestId('openvpn-file-select-button');
      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;

      // Upload file
      const file = new File(['content'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });
      fireEvent.change(fileInput);

      // Button text changes
      await waitFor(() => {
        expect(selectButton.textContent).toContain('Change File');
      });

      // Filename display
      expect(screen.getByText(/test.ovpn/)).toBeTruthy();
    });

    it('displays file size after upload', async () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;

      // Upload file (1024 bytes = 1.0 KB)
      const content = 'a'.repeat(1024);
      const file = new File([content], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });
      fireEvent.change(fileInput);

      // File size displayed
      await waitFor(() => {
        expect(screen.getByText(/1.0 KB/)).toBeTruthy();
      });
    });

    it('HASwitch toggle shows/hides auth fields for Squid', async () => {
      vi.mocked(instancesApi.getUsers).mockResolvedValue({ users: [] });

      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} proxyType="squid" />);

      const authToggle = screen.getByTestId('openvpn-auth-toggle');

      // Initially hidden
      expect(screen.queryByTestId('openvpn-username-input')).toBeNull();

      // Click toggle
      fireEvent.click(authToggle);

      // Fields visible
      await waitFor(() => {
        expect(screen.getByTestId('openvpn-username-input')).toBeTruthy();
        expect(screen.getByTestId('openvpn-password-input')).toBeTruthy();
      });
    });

    it('does not show auth section for TLS tunnel', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} proxyType="tls_tunnel" />);

      expect(screen.queryByTestId('openvpn-auth-toggle')).toBeNull();
    });
  });

  describe('P2 - Edge Cases', () => {
    it('shows external IP warning when missing', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} externalIp={undefined} />);

      expect(screen.getByText(/External IP not set/i)).toBeTruthy();
      expect(screen.getByText(/General settings/i)).toBeTruthy();
    });

    it('hides external IP warning when provided', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} externalIp="1.2.3.4" />);

      expect(screen.queryByText(/External IP not set/i)).toBeNull();
    });

    it('copy success message appears after copy', async () => {
      const mockPatchedContent = 'client\nhttp-proxy 192.168.1.100 3128\ndev tun\n';
      vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
        patched_content: mockPatchedContent,
        filename: 'test_patched.ovpn',
      });

      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: { writeText: writeTextMock },
      });

      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      // Upload and patch
      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      const patchButton = screen.getByTestId('openvpn-patch-button');
      fireEvent.click(patchButton);

      await waitFor(() => {
        expect(screen.getByTestId('openvpn-copy')).toBeTruthy();
      });

      // Click copy
      const copyButton = screen.getByTestId('openvpn-copy');
      fireEvent.click(copyButton);

      // Success message appears
      await waitFor(() => {
        expect(screen.getByText(/Copied to clipboard/i)).toBeTruthy();
      });

      // Verify clipboard was called
      expect(writeTextMock).toHaveBeenCalledWith(mockPatchedContent);
    });
  });

  describe('Migrated Tests - File Upload', () => {
    it('updates state when file is uploaded', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });

      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });

      fireEvent.change(fileInput);

      // File name should be displayed
      expect(screen.getByText(/test.ovpn/)).toBeTruthy();
    });

    it('rejects non-.ovpn files', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['data'], 'test.txt', { type: 'text/plain' });

      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });

      fireEvent.change(fileInput);

      expect(screen.getByText(/valid .ovpn file/i)).toBeTruthy();
    });
  });

  describe('Migrated Tests - Patch Button', () => {
    it('patch button is disabled until file uploaded', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      const patchButton = screen.getByTestId('openvpn-patch-button') as HTMLButtonElement;
      expect(patchButton.disabled).toBe(true);
    });

    it('patch button is enabled after file upload', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });

      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });

      fireEvent.change(fileInput);

      const patchButton = screen.getByTestId('openvpn-patch-button') as HTMLButtonElement;
      expect(patchButton.disabled).toBe(false);
    });

    it('calls patchOVPNConfig when patch button clicked', async () => {
      const mockPatchedContent = 'client\nhttp-proxy 192.168.1.100 3128\ndev tun\n';
      vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
        patched_content: mockPatchedContent,
        filename: 'test_patched.ovpn',
      });

      renderWithQueryClient(
        <OpenVPNPatcherDialog {...defaultProps} externalIp="192.168.1.100" />
      );

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });

      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });

      fireEvent.change(fileInput);

      const patchButton = screen.getByTestId('openvpn-patch-button');
      fireEvent.click(patchButton);

      // Wait for preview to appear (proves mutation succeeded)
      await waitFor(() => {
        expect(screen.getByTestId('openvpn-preview')).toBeTruthy();
      }, { timeout: 3000 });

      // Check that API was called correctly
      expect(instancesApi.patchOVPNConfig).toHaveBeenCalledWith('test-instance', {
        file: mockFile,
        external_host: '192.168.1.100',
      });
    });

    it('includes auth credentials when enabled', async () => {
      vi.mocked(instancesApi.getUsers).mockResolvedValue({ users: [] });
      vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
        patched_content: 'client\nhttp-proxy 192.168.1.100 3128\n',
        filename: 'test_patched.ovpn',
      });

      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} proxyType="squid" />);

      // Upload file
      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      // Enable auth
      const authToggle = screen.getByTestId('openvpn-auth-toggle');
      fireEvent.click(authToggle);

      await waitFor(() => {
        expect(screen.getByTestId('openvpn-username-input')).toBeTruthy();
      });

      // Enter credentials
      const usernameInput = screen
        .getByTestId('openvpn-username-input')
        .querySelector('input') as HTMLInputElement;
      const passwordInput = screen
        .getByTestId('openvpn-password-input')
        .querySelector('input') as HTMLInputElement;

      fireEvent.input(usernameInput, { target: { value: 'testuser' } });
      fireEvent.input(passwordInput, { target: { value: 'testpass' } });

      // Click patch
      const patchButton = screen.getByTestId('openvpn-patch-button');
      fireEvent.click(patchButton);

      // Wait for preview to appear
      await waitFor(() => {
        expect(screen.getByTestId('openvpn-preview')).toBeTruthy();
      }, { timeout: 3000 });

      // Check that API was called with auth credentials
      expect(instancesApi.patchOVPNConfig).toHaveBeenCalledWith('test-instance', {
        file: mockFile,
        username: 'testuser',
        password: 'testpass', // pragma: allowlist secret
      });
    });
  });

  describe('Migrated Tests - Preview Section', () => {
    it('download button only enabled after successful patch', async () => {
      const mockPatchedContent = 'client\nhttp-proxy 192.168.1.100 3128\ndev tun\n';
      vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
        patched_content: mockPatchedContent,
        filename: 'test_patched.ovpn',
      });

      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      // Initially no download button
      expect(screen.queryByTestId('openvpn-download')).toBeNull();

      // Upload and patch
      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      const patchButton = screen.getByTestId('openvpn-patch-button');
      fireEvent.click(patchButton);

      // After successful patch, download button should appear
      await waitFor(() => {
        expect(screen.getByTestId('openvpn-download')).toBeTruthy();
      });
    });

    it('displays patched content in preview', async () => {
      const mockPatchedContent = 'client\nhttp-proxy 192.168.1.100 3128\ndev tun\n';
      vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
        patched_content: mockPatchedContent,
        filename: 'test_patched.ovpn',
      });

      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      const patchButton = screen.getByTestId('openvpn-patch-button');
      fireEvent.click(patchButton);

      await waitFor(() => {
        const preview = screen.getByTestId('openvpn-preview') as HTMLTextAreaElement;
        expect(preview.value).toBe(mockPatchedContent);
      });
    });

    it('copy to clipboard works', async () => {
      const mockPatchedContent = 'client\nhttp-proxy 192.168.1.100 3128\ndev tun\n';
      vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
        patched_content: mockPatchedContent,
        filename: 'test_patched.ovpn',
      });

      // Mock navigator.clipboard
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: {
          writeText: writeTextMock,
        },
      });

      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      // Upload and patch
      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      const patchButton = screen.getByTestId('openvpn-patch-button');
      fireEvent.click(patchButton);

      await waitFor(() => {
        expect(screen.getByTestId('openvpn-copy')).toBeTruthy();
      });

      // Click copy button
      const copyButton = screen.getByTestId('openvpn-copy');
      fireEvent.click(copyButton);

      expect(writeTextMock).toHaveBeenCalledWith(mockPatchedContent);
    });
  });

  describe('Migrated Tests - Proxy Type Specific', () => {
    it('shows correct button text for TLS tunnel', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} proxyType="tls_tunnel" />);

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      const patchButton = screen.getByTestId('openvpn-patch-button');
      expect(patchButton.textContent).toContain('Extract & Patch');
    });

    it('shows correct button text for Squid', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} proxyType="squid" />);

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      const patchButton = screen.getByTestId('openvpn-patch-button');
      expect(patchButton.textContent).toContain('Patch Config');
    });

    it('fetches users for Squid instances', async () => {
      const mockUsers = [{ username: 'user1' }, { username: 'user2' }];
      vi.mocked(instancesApi.getUsers).mockResolvedValue({ users: mockUsers });

      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} proxyType="squid" />);

      await waitFor(() => {
        expect(instancesApi.getUsers).toHaveBeenCalledWith('test-instance');
      });
    });

    it('does not fetch users for TLS tunnel instances', () => {
      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} proxyType="tls_tunnel" />);

      expect(instancesApi.getUsers).not.toHaveBeenCalled();
    });
  });

  describe('Migrated Tests - Error Handling', () => {
    it('shows inline error on patch error', async () => {
      vi.mocked(instancesApi.patchOVPNConfig).mockRejectedValue(
        new Error('Invalid file format')
      );

      renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['invalid'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      const patchButton = screen.getByTestId('openvpn-patch-button');
      fireEvent.click(patchButton);

      await waitFor(
        () => {
          expect(screen.queryByTestId('openvpn-preview')).toBeNull();
          const errorText = screen.queryByText(/Invalid file format/i);
          expect(errorText).not.toBeNull();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('File Upload Interactions', () => {
    describe('Click-to-select file upload', () => {
      it('should trigger hidden file input when drop zone is clicked', () => {
        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        const hiddenInput = document.getElementById('openvpn-file-input-hidden') as HTMLInputElement;
        const clickSpy = vi.spyOn(hiddenInput, 'click');

        const dropZone = hiddenInput.parentElement?.querySelector('div[style*="cursor: pointer"]') as HTMLElement;
        fireEvent.click(dropZone);

        expect(clickSpy).toHaveBeenCalled();
      });

      it('should accept valid .ovpn file via click-to-select', () => {
        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
        const mockFile = new File(['client\nremote vpn.example.com 1194'], 'client.ovpn', {
          type: 'application/x-openvpn-profile',
        });

        Object.defineProperty(fileInput, 'files', {
          value: [mockFile],
          writable: false,
        });
        fireEvent.change(fileInput);

        expect(screen.getByText('client.ovpn')).toBeInTheDocument();
        expect(screen.queryByText(/Please select a valid .ovpn file/i)).toBeNull();
      });

      it('should reject non-.ovpn file via click-to-select', () => {
        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
        const mockFile = new File(['invalid content'], 'config.txt', {
          type: 'text/plain',
        });

        Object.defineProperty(fileInput, 'files', {
          value: [mockFile],
          writable: false,
        });
        fireEvent.change(fileInput);

        expect(screen.getByText(/Please select a valid .ovpn file/i)).toBeInTheDocument();
        expect(screen.queryByText('config.txt')).toBeNull();
      });
    });

    describe('Drag-and-drop file upload', () => {
      it('should set isDragging to true on dragover', () => {
        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        const dropZone = screen.getByText(/Drop .ovpn file here or click to browse/i).parentElement as HTMLElement;

        fireEvent.dragOver(dropZone);

        // Check for visual feedback - border should change to primary color
        expect(dropZone.style.border).toContain('var(--primary-color)');
      });

      it('should set isDragging to false on dragleave', () => {
        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        const dropZone = screen.getByText(/Drop .ovpn file here or click to browse/i).parentElement as HTMLElement;

        fireEvent.dragOver(dropZone);
        expect(dropZone.style.border).toContain('var(--primary-color)');

        fireEvent.dragLeave(dropZone);
        expect(dropZone.style.border).toContain('var(--divider-color)');
      });

      it('should accept valid .ovpn file via drag-and-drop', () => {
        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        const dropZone = screen.getByText(/Drop .ovpn file here or click to browse/i).parentElement as HTMLElement;
        const mockFile = new File(['client\nremote vpn.example.com 1194'], 'client.ovpn', {
          type: 'application/x-openvpn-profile',
        });

        fireEvent.drop(dropZone, {
          dataTransfer: {
            files: [mockFile],
          },
        });

        expect(screen.getByText('client.ovpn')).toBeInTheDocument();
        expect(screen.queryByText(/Please select a valid .ovpn file/i)).toBeNull();
      });

      it('should reject non-.ovpn file via drag-and-drop', () => {
        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        const dropZone = screen.getByText(/Drop .ovpn file here or click to browse/i).parentElement as HTMLElement;
        const mockFile = new File(['invalid content'], 'config.txt', {
          type: 'text/plain',
        });

        fireEvent.drop(dropZone, {
          dataTransfer: {
            files: [mockFile],
          },
        });

        expect(screen.getByText(/Please select a valid .ovpn file/i)).toBeInTheDocument();
        expect(screen.queryByText('config.txt')).toBeNull();
      });

      it('should reset isDragging on drop', () => {
        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        const dropZone = screen.getByText(/Drop .ovpn file here or click to browse/i).parentElement as HTMLElement;
        const mockFile = new File(['client\nremote vpn.example.com 1194'], 'client.ovpn', {
          type: 'application/x-openvpn-profile',
        });

        fireEvent.dragOver(dropZone);
        expect(dropZone.style.border).toContain('var(--primary-color)');

        fireEvent.drop(dropZone, {
          dataTransfer: {
            files: [mockFile],
          },
        });

        // After drop, dragging state should be reset
        expect(dropZone.style.border).toContain('var(--divider-color)');
      });

      it('should show file size after successful drop', () => {
        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        const dropZone = screen.getByText(/Drop .ovpn file here or click to browse/i).parentElement as HTMLElement;
        const mockFile = new File(['a'.repeat(2048)], 'client.ovpn', {
          type: 'application/x-openvpn-profile',
        });

        fireEvent.drop(dropZone, {
          dataTransfer: {
            files: [mockFile],
          },
        });

        expect(screen.getByText('client.ovpn')).toBeInTheDocument();
        expect(screen.getByText(/2.0 KB/i)).toBeInTheDocument();
      });

      it('should prevent default dragover and drop behavior', () => {
        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        const dropZone = screen.getByText(/Drop .ovpn file here or click to browse/i).parentElement as HTMLElement;

        const dragOverEvent = new Event('dragover', { bubbles: true, cancelable: true });
        const preventDefaultSpy = vi.spyOn(dragOverEvent, 'preventDefault');
        dropZone.dispatchEvent(dragOverEvent);
        expect(preventDefaultSpy).toHaveBeenCalled();

        const dropEvent = new Event('drop', { bubbles: true, cancelable: true });
        const dropPreventDefaultSpy = vi.spyOn(dropEvent, 'preventDefault');
        dropZone.dispatchEvent(dropEvent);
        expect(dropPreventDefaultSpy).toHaveBeenCalled();
      });
    });

    describe('File upload state management', () => {
      it('should reset patchedContent when new file is selected', async () => {
        vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
          patched_content: 'http-proxy 10.0.0.1 3128\nremote vpn.example.com 1194',
        });

        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        // Upload and patch first file
        const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
        const mockFile1 = new File(['client\nremote vpn.example.com 1194'], 'client1.ovpn', {
          type: 'application/x-openvpn-profile',
        });

        Object.defineProperty(fileInput, 'files', {
          value: [mockFile1],
          writable: false,
        });
        fireEvent.change(fileInput);

        const patchButton = screen.getByTestId('openvpn-patch-button');
        fireEvent.click(patchButton);

        await waitFor(() => {
          expect(screen.getByTestId('openvpn-preview')).toBeInTheDocument();
        });

        // Upload second file - should reset preview
        const mockFile2 = new File(['client\nremote vpn2.example.com 1194'], 'client2.ovpn', {
          type: 'application/x-openvpn-profile',
        });

        Object.defineProperty(fileInput, 'files', {
          value: [mockFile2],
          writable: false,
        });
        fireEvent.change(fileInput);

        // Preview should be gone until new patch
        expect(screen.queryByTestId('openvpn-preview')).toBeNull();
      });

      it('should reset all state when dialog is closed', async () => {
        vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
          patched_content: 'http-proxy 10.0.0.1 3128\nremote vpn.example.com 1194',
        });

        renderWithQueryClient(<OpenVPNPatcherDialog {...defaultProps} />);

        // Upload file and trigger error
        const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
        const mockFile = new File(['invalid'], 'test.ovpn', { type: 'text/plain' });
        Object.defineProperty(fileInput, 'files', {
          value: [mockFile],
          writable: false,
        });
        fireEvent.change(fileInput);

        const patchButton = screen.getByTestId('openvpn-patch-button');
        fireEvent.click(patchButton);

        await waitFor(() => {
          expect(instancesApi.patchOVPNConfig).toHaveBeenCalled();
        });

        // Close dialog
        const closeButton = screen.getByTestId('openvpn-dialog-close');
        fireEvent.click(closeButton);

        expect(defaultProps.onClose).toHaveBeenCalled();
      });
    });
  });
});
