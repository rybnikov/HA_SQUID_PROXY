"""OpenVPN config file patcher for Squid and TLS Tunnel proxies."""


def validate_ovpn_content(content: str) -> tuple[bool, str]:
    """Validate basic .ovpn file structure.

    Returns (is_valid, error_message).
    """
    if not content or len(content.strip()) == 0:
        return False, "File is empty"

    if len(content) > 1024 * 1024:  # 1MB max
        return False, "File too large (max 1MB)"

    # Basic structure check - should have at least one recognized directive
    recognized = [
        "client",
        "dev",
        "proto",
        "remote",
        "resolv-retry",
        "nobind",
        "persist-key",
        "persist-tun",
        "ca",
        "cert",
        "key",
        "tls-auth",
        "tls-crypt",
        "cipher",
        "verb",
    ]
    has_directive = any(
        line.strip().split()[0] in recognized
        for line in content.split("\n")
        if line.strip() and not line.strip().startswith("#")
    )

    if not has_directive:
        return False, "File does not appear to be a valid OpenVPN config"

    return True, ""


def patch_ovpn_for_squid(
    content: str,
    proxy_host: str,
    proxy_port: int,
    username: str | None = None,
    password: str | None = None,
) -> str:
    """Patch .ovpn config to route through Squid HTTP proxy.

    Adds http-proxy directive and inline auth if credentials provided.
    """
    lines = content.split("\n")
    result = []
    http_proxy_added = False

    for line in lines:
        # Remove existing http-proxy directives to avoid conflicts
        if line.strip().startswith("http-proxy"):
            continue
        result.append(line)

    # Add http-proxy directive after client directive
    for i, line in enumerate(result):
        if line.strip().startswith("client"):
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

    return "\n".join(result)


def patch_ovpn_for_tls_tunnel(content: str, tunnel_host: str, tunnel_port: int) -> tuple[str, str]:
    """Patch .ovpn config to connect through TLS tunnel.

    Extracts VPN server address from original 'remote' directive and
    replaces it with tunnel endpoint. Also applies DPI evasion settings:
    - Forces proto tcp (TLS tunnel requires TCP)
    - Removes explicit-exit-notify (UDP-only, causes errors on TCP)
    - Adds tun-mtu, mssfix, sndbuf/rcvbuf tuning
    - Adds connect-retry-max and float for resilience

    Returns:
        - patched_content: Config with remote replaced and DPI settings applied
        - vpn_server: Extracted "host:port" from original remote directive
    """
    lines = content.split("\n")
    result = []
    vpn_server = None
    remote_replaced = False
    proto_replaced = False

    # Directives to remove (UDP-only or incompatible with TLS tunnel)
    remove_directives = {"explicit-exit-notify"}

    # Track which DPI settings already exist
    existing_directives: set[str] = set()

    # First pass: collect existing directive names
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith(";"):
            directive = stripped.split()[0]
            existing_directives.add(directive)

    # Build DPI evasion block to insert near the top of the file
    dpi_settings: list[str] = []
    if "tun-mtu" not in existing_directives:
        dpi_settings.append("tun-mtu 1500")
    if "mssfix" not in existing_directives:
        dpi_settings.append("mssfix 1300")
    if "sndbuf" not in existing_directives:
        dpi_settings.append("sndbuf 0")
    if "rcvbuf" not in existing_directives:
        dpi_settings.append("rcvbuf 0")
    if "connect-retry-max" not in existing_directives:
        dpi_settings.append("connect-retry-max 100")
    if "float" not in existing_directives:
        dpi_settings.append("float")

    for line in lines:
        stripped = line.strip()

        # Skip empty/comment lines — keep them as-is
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            result.append(line)
            continue

        directive = stripped.split()[0]

        # Remove UDP-only directives
        if directive in remove_directives:
            result.append(f"# {line.rstrip()}  # removed for TLS tunnel (UDP-only)")
            continue

        # Replace first 'remote' directive and inject DPI settings right after
        if directive == "remote" and not remote_replaced:
            parts = stripped.split()
            if len(parts) >= 3:
                vpn_host = parts[1]
                vpn_port = parts[2]
                vpn_server = f"{vpn_host}:{vpn_port}"
            elif len(parts) >= 2:
                vpn_host = parts[1]
                vpn_server = f"{vpn_host}:1194"

            result.append(f"remote {tunnel_host} {tunnel_port}")
            # Insert DPI evasion block right after the new remote directive
            if dpi_settings:
                result.append("")
                result.append("# DPI evasion settings (added by TLS tunnel patcher)")
                result.extend(dpi_settings)
                result.append("")
            remote_replaced = True
            continue

        # Force proto tcp
        if directive == "proto":
            result.append("proto tcp")
            proto_replaced = True
            continue

        result.append(line)

    # If no remote directive found, add one with DPI settings
    if not remote_replaced:
        inserted = False
        for i, line in enumerate(result):
            if line.strip().startswith("client"):
                insert_pos = i + 1
                result.insert(insert_pos, f"remote {tunnel_host} {tunnel_port}")
                if dpi_settings:
                    result.insert(insert_pos + 1, "")
                    result.insert(
                        insert_pos + 2, "# DPI evasion settings (added by TLS tunnel patcher)"
                    )
                    for j, setting in enumerate(dpi_settings):
                        result.insert(insert_pos + 3 + j, setting)
                    result.insert(insert_pos + 3 + len(dpi_settings), "")
                inserted = True
                break
        if not inserted:
            result.insert(0, f"remote {tunnel_host} {tunnel_port}")
            if dpi_settings:
                result.insert(1, "")
                result.insert(2, "# DPI evasion settings (added by TLS tunnel patcher)")
                for j, setting in enumerate(dpi_settings):
                    result.insert(3 + j, setting)
                result.insert(3 + len(dpi_settings), "")

    # Add proto tcp if it wasn't already in the file and wasn't replaced
    if not proto_replaced and "proto" not in existing_directives:
        # Insert after the DPI block (find the comment marker)
        for i, line in enumerate(result):
            if line.strip() == "# DPI evasion settings (added by TLS tunnel patcher)":
                result.insert(i, "proto tcp")
                break

    return "\n".join(result), vpn_server or ""
