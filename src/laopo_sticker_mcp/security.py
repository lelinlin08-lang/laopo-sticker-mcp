from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def assert_safe_public_https_url(url: str) -> None:
    """Reject local/private targets before the server downloads an attachment."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("附件下载地址必须是公开 HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("附件下载地址不能包含用户名或密码")

    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("附件下载域名无法解析") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("附件下载地址不能指向本机、内网或保留网段")
