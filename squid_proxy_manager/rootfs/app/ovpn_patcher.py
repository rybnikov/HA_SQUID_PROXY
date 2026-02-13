"""OpenVPN config file patcher for Squid and TLS Tunnel proxies."""

import re
from typing import Optional, Tuple

def validate_ovpn_content(content: str) -> Tuple[bool, str]:
    """Validate basic .ovpn file structure.

    Returns (is_valid, error_message).
    """
    if not content or len(content.strip()) == 0:
        return False, "File is empty"

    if len(content) > 1024 * 1024:  # 1MB max
        return False, "File too large (max 1MB)"

    # Basic structure check - should have at least one recognized directive
    recognized = ['client', 'dev', 'proto', 'remote', 'resolv-retry', 'nobind', 'persist-key', 'persist-tun', 'ca', 'cert', 'key', 'tls-auth', 'tls-crypt', 'cipher', 'verb']
    has_directive = any(line.strip().split()[0] in recognized for line in content.split('\n') if line.strip() and not line.strip().startswith('#'))

    if not has_directive:
        return False, "File does not appear to be a valid OpenVPN config"

    return True, ""

def patch_ovpn_for_squid(
    content: str,
    proxy_host: str,
    proxy_port: int,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> str:
    """Patch .ovpn config to route through Squid HTTP proxy.

    Adds http-proxy directive and inline auth if credentials provided.
    """
    lines = content.split('\n')
    result = []
    http_proxy_added = False

    for line in lines:
        # Remove existing http-proxy directives to avoid conflicts
        if line.strip().startswith('http-proxy'):
            continue
        result.append(line)

    # Add http-proxy directive after client directive
    for i, line in enumerate(result):
        if line.strip().startswith('client'):
            result.insert(i + 1, f"http-proxy {proxy_host} {proxy_port}")
            http_proxy_added = True

            # Add inline auth if provided
            if username and password:
                result.insert(i + 2, "<http-proxy-user-pass>")
                result.insert(i + 3, username)
                result.insert(i + 4, password)
                result.insert(i + 5, "</http-proxy-user-pass>")
            break

    # If no 'client' directive found, add at beginning
    if not http_proxy_added:
        proxy_line = f"http-proxy {proxy_host} {proxy_port}"
        if username and password:
            result.insert(0, "</http-proxy-user-pass>")
            result.insert(0, password)
            result.insert(0, username)
            result.insert(0, "<http-proxy-user-pass>")
        result.insert(0, proxy_line)

    return '\n'.join(result)

def patch_ovpn_for_tls_tunnel(
    content: str,
    tunnel_host: str,
    tunnel_port: int
) -> Tuple[str, str]:
    """Patch .ovpn config to connect through TLS tunnel.

    Extracts VPN server address from original 'remote' directive and
    replaces it with tunnel endpoint.

    Returns:
        - patched_content: Config with remote replaced
        - vpn_server: Extracted "host:port" from original remote directive
    """
    lines = content.split('\n')
    result = []
    vpn_server = None
    remote_replaced = False

    for line in lines:
        # Replace first 'remote' directive
        if line.strip().startswith('remote') and not remote_replaced:
            # Extract original VPN server address
            parts = line.strip().split()
            if len(parts) >= 3:
                vpn_host = parts[1]
                vpn_port = parts[2]
                vpn_server = f"{vpn_host}:{vpn_port}"
            elif len(parts) >= 2:
                # If no port specified, assume 1194 (OpenVPN default)
                vpn_host = parts[1]
                vpn_server = f"{vpn_host}:1194"

            # Replace with tunnel endpoint
            result.append(f"remote {tunnel_host} {tunnel_port}")
            remote_replaced = True
        else:
            result.append(line)

    # If no remote directive found, add one
    if not remote_replaced:
        # Insert after 'client' or at beginning
        inserted = False
        for i, line in enumerate(result):
            if line.strip().startswith('client'):
                result.insert(i + 1, f"remote {tunnel_host} {tunnel_port}")
                inserted = True
                break
        if not inserted:
            result.insert(0, f"remote {tunnel_host} {tunnel_port}")

    return '\n'.join(result), vpn_server or ""
