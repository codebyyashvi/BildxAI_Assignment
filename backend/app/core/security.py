import socket
import ipaddress
from urllib.parse import urlparse
from app.core.exceptions import PermanentError
from app.core.config import settings

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "::1",
    "metadata.google.internal",
    "169.254.169.254",
}

def is_ip_private(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True
        for net in BLOCKED_IP_NETWORKS:
            if ip in net:
                return True
        return False
    except ValueError:
        # Not a valid IP address literal
        return False

def validate_image_url(url: str, allow_local_for_testing: bool = False) -> None:
    """
    Validates image URL against SSRF and protocol restrictions.
    Enforces HTTP/HTTPS and prevents access to internal/private IP spaces.
    """
    if not url or not isinstance(url, str):
        raise PermanentError("Image URL must be a non-empty string.")

    try:
        parsed = urlparse(url.strip())
    except Exception as e:
        raise PermanentError(f"Malformed URL: {str(e)}")

    if parsed.scheme.lower() not in ("http", "https"):
        raise PermanentError(f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise PermanentError("URL must contain a valid hostname.")

    hostname_lower = hostname.lower()
    if not allow_local_for_testing and hostname_lower in BLOCKED_HOSTNAMES:
        raise PermanentError(f"Access to restricted host '{hostname}' is forbidden.")

    # Check if host is direct IP address or resolves to private space
    if not allow_local_for_testing:
        # Check direct IP literal first
        if is_ip_private(hostname):
            raise PermanentError(f"Host '{hostname}' is a private/internal IP address, access denied.")

        # Perform DNS check only if not in test environment
        if settings.ENVIRONMENT != "test":
            try:
                addr_info = socket.getaddrinfo(hostname, None)
                for item in addr_info:
                    ip_str = item[4][0]
                    if is_ip_private(ip_str):
                        raise PermanentError(f"Target host '{hostname}' resolves to private/internal IP '{ip_str}', access denied.")
            except socket.gaierror:
                raise PermanentError(f"Could not resolve host '{hostname}'. Host is unreachable or invalid.")
