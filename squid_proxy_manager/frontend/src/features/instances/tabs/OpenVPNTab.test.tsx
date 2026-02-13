import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import * as instancesApi from '@/api/instances';

import { OpenVPNTab } from './OpenVPNTab';

// Mock the API module
vi.mock('@/api/instances', () => ({
  getUsers: vi.fn(),
  patchOVPNConfig: vi.fn(),
}));

describe('OpenVPNTab', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const renderWithQueryClient = (ui: React.ReactElement) => {
    return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
  };

  describe('Squid Instance', () => {
    it('renders for Squid instance', () => {
      vi.mocked(instancesApi.getUsers).mockResolvedValue({ users: [] });

      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

      expect(screen.getByText(/Upload your OpenVPN config file/)).toBeTruthy();
      expect(screen.getByTestId('openvpn-file-input')).toBeTruthy();
      expect(screen.getByTestId('openvpn-patch-button')).toBeTruthy();
    });

    it('shows auth section for Squid instances', () => {
      vi.mocked(instancesApi.getUsers).mockResolvedValue({ users: [] });

      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

      expect(screen.getByText(/Authentication \(Optional\)/)).toBeTruthy();
      expect(screen.getByTestId('openvpn-auth-checkbox')).toBeTruthy();
    });

    it('does not show auth section for TLS tunnel instances', () => {
      renderWithQueryClient(
        <OpenVPNTab instanceName="tls-tunnel" proxyType="tls_tunnel" port={4443} />
      );

      expect(screen.queryByText(/Authentication \(Optional\)/)).toBeNull();
      expect(screen.queryByTestId('openvpn-auth-checkbox')).toBeNull();
    });

    it('enables auth inputs when checkbox is checked', async () => {
      vi.mocked(instancesApi.getUsers).mockResolvedValue({ users: [] });

      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

      const authCheckbox = screen.getByTestId('openvpn-auth-checkbox') as HTMLInputElement;
      expect(authCheckbox.checked).toBe(false);

      fireEvent.click(authCheckbox);

      await waitFor(() => {
        expect(screen.getByTestId('openvpn-username-input')).toBeTruthy();
        expect(screen.getByTestId('openvpn-password-input')).toBeTruthy();
      });
    });

    it('fetches users for Squid instances', async () => {
      const mockUsers = [{ username: 'user1' }, { username: 'user2' }];
      vi.mocked(instancesApi.getUsers).mockResolvedValue({ users: mockUsers });

      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

      await waitFor(() => {
        expect(instancesApi.getUsers).toHaveBeenCalledWith('squid-proxy');
      });
    });
  });

  describe('TLS Tunnel Instance', () => {
    it('renders for TLS tunnel instance', () => {
      renderWithQueryClient(
        <OpenVPNTab instanceName="tls-tunnel" proxyType="tls_tunnel" port={4443} />
      );

      expect(screen.getByText(/extract your VPN server address/)).toBeTruthy();
      expect(screen.getByTestId('openvpn-file-input')).toBeTruthy();
      expect(screen.getByTestId('openvpn-patch-button')).toBeTruthy();
    });

    it('shows correct button text for TLS tunnel', () => {
      renderWithQueryClient(
        <OpenVPNTab instanceName="tls-tunnel" proxyType="tls_tunnel" port={4443} />
      );

      const patchButton = screen.getByTestId('openvpn-patch-button');
      expect(patchButton.textContent).toContain('Extract & Patch Config');
    });

    it('does not fetch users for TLS tunnel instances', () => {
      renderWithQueryClient(
        <OpenVPNTab instanceName="tls-tunnel" proxyType="tls_tunnel" port={4443} />
      );

      expect(instancesApi.getUsers).not.toHaveBeenCalled();
    });
  });

  describe('File Upload', () => {
    it('updates state when file is uploaded', () => {
      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });

      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });

      fireEvent.change(fileInput);

      // File name should be displayed
      expect(screen.getByText(/Selected: test.ovpn/)).toBeTruthy();
    });

    it('rejects non-.ovpn files', () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['data'], 'test.txt', { type: 'text/plain' });

      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });

      fireEvent.change(fileInput);

      expect(alertSpy).toHaveBeenCalledWith('Please select a valid .ovpn file');
      alertSpy.mockRestore();
    });
  });

  describe('Patch Button', () => {
    it('patch button is disabled until file uploaded', () => {
      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

      const patchButton = screen.getByTestId('openvpn-patch-button') as HTMLButtonElement;
      expect(patchButton.disabled).toBe(true);
    });

    it('patch button is enabled after file upload', () => {
      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

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
        filename: 'squid-proxy_patched.ovpn',
      });

      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} externalIp="192.168.1.100" />
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

      await waitFor(() => {
        expect(instancesApi.patchOVPNConfig).toHaveBeenCalledWith('squid-proxy', {
          file: mockFile,
          external_host: '192.168.1.100',
        });
      });
    });

    it('includes auth credentials when enabled', async () => {
      vi.mocked(instancesApi.getUsers).mockResolvedValue({ users: [] });
      vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
        patched_content: 'client\nhttp-proxy 192.168.1.100 3128\n',
        filename: 'squid-proxy_patched.ovpn',
      });

      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

      // Upload file
      const fileInput = screen.getByTestId('openvpn-file-input') as HTMLInputElement;
      const mockFile = new File(['client\ndev tun\n'], 'test.ovpn', { type: 'text/plain' });
      Object.defineProperty(fileInput, 'files', {
        value: [mockFile],
        writable: false,
      });
      fireEvent.change(fileInput);

      // Enable auth
      const authCheckbox = screen.getByTestId('openvpn-auth-checkbox');
      fireEvent.click(authCheckbox);

      await waitFor(() => {
        expect(screen.getByTestId('openvpn-username-input')).toBeTruthy();
      });

      // Enter credentials
      const usernameInput = screen.getByTestId('openvpn-username-input').querySelector('input') as HTMLInputElement;
      const passwordInput = screen.getByTestId('openvpn-password-input').querySelector('input') as HTMLInputElement;

      fireEvent.input(usernameInput, { target: { value: 'testuser' } });
      fireEvent.input(passwordInput, { target: { value: 'testpass' } });

      // Click patch
      const patchButton = screen.getByTestId('openvpn-patch-button');
      fireEvent.click(patchButton);

      await waitFor(() => {
        expect(instancesApi.patchOVPNConfig).toHaveBeenCalledWith('squid-proxy', {
          file: mockFile,
          username: 'testuser',
          password: 'testpass',
        });
      });
    });
  });

  describe('Preview Section', () => {
    it('download button only enabled after successful patch', async () => {
      const mockPatchedContent = 'client\nhttp-proxy 192.168.1.100 3128\ndev tun\n';
      vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
        patched_content: mockPatchedContent,
        filename: 'squid-proxy_patched.ovpn',
      });

      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

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
        filename: 'squid-proxy_patched.ovpn',
      });

      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
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

      await waitFor(() => {
        const preview = screen.getByTestId('openvpn-preview') as HTMLTextAreaElement;
        expect(preview.value).toBe(mockPatchedContent);
      });
    });

    it('copy to clipboard works', async () => {
      const mockPatchedContent = 'client\nhttp-proxy 192.168.1.100 3128\ndev tun\n';
      vi.mocked(instancesApi.patchOVPNConfig).mockResolvedValue({
        patched_content: mockPatchedContent,
        filename: 'squid-proxy_patched.ovpn',
      });

      // Mock navigator.clipboard
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: {
          writeText: writeTextMock,
        },
      });

      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

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
      expect(alertSpy).toHaveBeenCalledWith('Copied to clipboard!');

      alertSpy.mockRestore();
    });
  });

  describe('External IP Warning', () => {
    it('shows external IP warning when not set', () => {
      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

      expect(screen.getByText(/External IP Not Set/)).toBeTruthy();
      expect(screen.getByText(/localhost/)).toBeTruthy();
    });

    it('does not show warning when external IP is set', () => {
      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} externalIp="192.168.1.100" />
      );

      expect(screen.queryByText(/External IP Not Set/)).toBeNull();
    });
  });

  describe('Error Handling', () => {
    it('shows alert on patch error', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
      vi.mocked(instancesApi.patchOVPNConfig).mockRejectedValue(new Error('Invalid file format'));

      renderWithQueryClient(
        <OpenVPNTab instanceName="squid-proxy" proxyType="squid" port={3128} />
      );

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
        expect(alertSpy).toHaveBeenCalledWith('Failed to patch config: Invalid file format');
      });

      alertSpy.mockRestore();
    });
  });
});
