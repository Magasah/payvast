"""Pure-ASGI middleware: request body cap and security headers on every API response."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    (b"cross-origin-resource-policy", b"same-origin"),
    # JSON API: nothing here is ever rendered as a page.
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
]


class SecurityMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for name, value in scope["headers"]:
            if name == b"content-length":
                try:
                    too_big = int(value) > self.max_body_bytes
                except ValueError:
                    too_big = True
                if too_big:
                    await _reject(send, 413, b'{"detail":"payload_too_large"}')
                    return

        received = 0

        async def capped_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise _BodyTooLarge
            return message

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {k.lower() for k, _ in headers}
                headers.extend(h for h in SECURITY_HEADERS if h[0] not in present)
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, capped_receive, send_with_headers)
        except _BodyTooLarge:
            await _reject(send, 413, b'{"detail":"payload_too_large"}')


class _BodyTooLarge(Exception):
    pass


async def _reject(send: Send, status: int, body: bytes) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json"), *SECURITY_HEADERS],
        }
    )
    await send({"type": "http.response.body", "body": body})
