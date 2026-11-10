"""The proxy pins the connection address and rejects private destinations."""

import asyncio

import pytest

from job_scan.browser_network import public_address, public_proxy


@pytest.mark.enable_socket
@pytest.mark.parametrize("tunnel", [False, True])
def test_proxy_preserves_http_and_tls_tunnels(
    tunnel: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        seen = []

        async def origin(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            request = await reader.readuntil(b"\r\n\r\n")
            seen.append(request)
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK")
            await writer.drain()
            writer.close()

        async def resolved(host: str, _port: int) -> str:
            assert host == "jobs.example"
            return "127.0.0.1"  # Simulate a validated public address using our local origin.

        monkeypatch.setattr("job_scan.browser_network.public_address", resolved)
        server = await asyncio.start_server(origin, "127.0.0.1", 0)
        async with server, public_proxy() as proxy:
            port = server.sockets[0].getsockname()[1]
            reader, writer = await asyncio.open_connection(
                "127.0.0.1", int(proxy.rsplit(":", 1)[1])
            )
            if tunnel:
                writer.write(f"CONNECT jobs.example:{port} HTTP/1.1\r\n\r\n".encode())
                await writer.drain()
                assert b"200 Connection Established" in await reader.readuntil(b"\r\n\r\n")
                writer.write(b"GET /job?selected=42 HTTP/1.1\r\nHost: jobs.example\r\n\r\n")
            else:
                writer.write(
                    f"GET http://jobs.example:{port}/job?selected=42 HTTP/1.1\r\n"
                    "Host: jobs.example\r\n\r\n".encode()
                )
            await writer.drain()
            assert (await reader.read()).endswith(b"OK")
            writer.close()
        assert seen == [b"GET /job?selected=42 HTTP/1.1\r\nHost: jobs.example\r\n\r\n"]

    asyncio.run(scenario())


@pytest.mark.enable_socket
def test_proxy_cannot_reach_private_destinations() -> None:
    async def scenario() -> None:
        async with public_proxy() as proxy:
            reader, writer = await asyncio.open_connection(
                "127.0.0.1", int(proxy.rsplit(":", 1)[1])
            )
            writer.write(b"CONNECT 127.0.0.1:80 HTTP/1.1\r\n\r\n")
            await writer.drain()
            assert b"502 Bad Gateway" in await reader.read()
            writer.close()

    asyncio.run(scenario())


@pytest.mark.enable_socket
def test_dns_result_is_checked_and_returned_without_second_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        loop = asyncio.get_running_loop()

        async def dns(
            *_args: object, **_kwargs: object
        ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
            return [(2, 1, 6, "", ("8.8.8.8", 443))]

        monkeypatch.setattr(loop, "getaddrinfo", dns)
        assert await public_address("jobs.example", 443) == "8.8.8.8"

    asyncio.run(scenario())


@pytest.mark.enable_socket
def test_chromium_cannot_bypass_proxy_for_loopback() -> None:
    from job_scan.retrieval import RetrievalError, _retrieve

    async def scenario() -> None:
        contacts = []

        async def private_service(
            _reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            contacts.append(True)
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: 40\r\n\r\n"
                b"<h1>Engineer</h1><p>Fully remote job</p>"
            )
            await writer.drain()
            writer.close()

        server = await asyncio.start_server(private_service, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            with pytest.raises(RetrievalError, match="blocked or unavailable"):
                await _retrieve(f"http://127.0.0.1:{port}/job")
        assert not contacts

    asyncio.run(scenario())
