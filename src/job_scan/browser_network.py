"""A browser proxy that connects only to validated public destination addresses."""

import asyncio
import ipaddress
import socket
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from urllib.parse import urlsplit


async def public_address(host: str, port: int) -> str:
    addresses = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Browser destinations must have public addresses.")
    return str(addresses[0][4][0])


async def copy_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    while data := await reader.read(65536):
        writer.write(data)
        await writer.drain()


async def proxy_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    upstream: asyncio.StreamWriter | None = None
    pumps: list[asyncio.Task[None]] = []
    try:
        headers = await reader.readuntil(b"\r\n\r\n")
        first, rest = headers.split(b"\r\n", 1)
        method, target, version = first.decode("ascii").split(" ")
        url = urlsplit("https://" + target if method == "CONNECT" else target)
        if url.scheme not in {"http", "https"} or url.hostname is None or url.username is not None:
            raise ValueError("Unsupported proxy destination.")
        port = url.port or (443 if url.scheme == "https" else 80)
        address = await public_address(url.hostname, port)
        # Numeric address binds validation to the actual TCP connection, including TLS tunnels.
        remote, upstream = await asyncio.open_connection(address, port)
        if method == "CONNECT":
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
        else:
            path = url.path or "/"
            if url.query:
                path += "?" + url.query
            upstream.write(f"{method} {path} {version}\r\n".encode("ascii") + rest)
            await upstream.drain()
        pumps = [
            asyncio.create_task(copy_stream(reader, upstream)),
            asyncio.create_task(copy_stream(remote, writer)),
        ]
        await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
    except OSError, ValueError, asyncio.IncompleteReadError, asyncio.LimitOverrunError:
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
    finally:
        for pump in pumps:
            pump.cancel()
        if pumps:
            await asyncio.gather(*pumps, return_exceptions=True)
        if upstream is not None:
            upstream.close()
        writer.close()


@asynccontextmanager
async def public_proxy() -> AsyncGenerator[str]:
    """Route HTTP, HTTPS, redirects and WebSockets through one connection policy."""
    active: set[asyncio.Task[None]] = set()

    async def connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        if task is not None:
            active.add(task)
        try:
            await proxy_connection(reader, writer)
        finally:
            if task is not None:
                active.discard(task)

    server = await asyncio.start_server(connected, "127.0.0.1", 0)
    try:
        async with server:
            port = server.sockets[0].getsockname()[1]
            yield f"http://127.0.0.1:{port}"
    finally:
        for task in active:
            task.cancel()
        await asyncio.gather(*active, return_exceptions=True)
