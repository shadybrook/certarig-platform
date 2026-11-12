"""Local length-framed RPC; no TCP listener and no engine socket in Edge or workers."""

from __future__ import annotations

import json
import os
import socket
import socketserver
import struct
from pathlib import Path
from typing import Any

from .contracts import encoded

MAX_FRAME = 384 * 1024**2


def receive(stream: socket.socket) -> dict[str, Any]:
    def read(n: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < n:
            part = stream.recv(min(65536, n - len(chunks)))
            if not part:
                raise ValueError("incomplete broker frame")
            chunks.extend(part)
        return bytes(chunks)

    size = struct.unpack("!I", read(4))[0]
    if size > MAX_FRAME:
        raise ValueError("broker frame too large")
    value = json.loads(read(size))
    if not isinstance(value, dict):
        raise ValueError("broker frame must be an object")
    return value


def send(stream: socket.socket, value: dict[str, Any]) -> None:
    data = encoded(value)
    if len(data) > MAX_FRAME:
        raise ValueError("broker frame too large")
    stream.sendall(struct.pack("!I", len(data)) + data)


class BrokerClient:
    def __init__(self, path: Path) -> None:
        self.path = path

    def call(self, method: str, owner: str, role: str, body: dict[str, Any]) -> dict[str, Any]:
        with socket.socket(socket.AF_UNIX) as stream:
            stream.settimeout(10)
            stream.connect(str(self.path))
            send(stream, {"method": method, "owner": owner, "role": role, "body": body})
            result = receive(stream)
        if "error" in result:
            error = result["error"]
            if error["type"] == "PermissionError":
                raise PermissionError(error["message"])
            if error["type"] == "KeyError":
                raise KeyError(error["message"])
            raise ValueError(error["message"])
        return dict(result["result"])


def server(path: Path, broker: Any) -> socketserver.ThreadingUnixStreamServer:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.stat().st_uid != os.getuid() or path.parent.stat().st_mode & 0o077:
        raise ValueError("broker socket requires a private directory owned by this user")
    if path.exists():
        # Never replace a live broker endpoint.
        try:
            with socket.socket(socket.AF_UNIX) as probe:
                probe.connect(str(path))
        except ConnectionRefusedError:
            path.unlink()
        else:
            raise ValueError("broker socket is already in use")

    class Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            self.request.settimeout(10)
            try:
                request = receive(self.request)
                result = broker.call(request["method"], request["owner"], request["role"], request["body"])
                send(self.request, {"result": result})
            except Exception as exc:
                send(
                    self.request,
                    {
                        "error": {
                            "type": "KeyError" if isinstance(exc, StopIteration) else type(exc).__name__,
                            "message": str(exc),
                        }
                    },
                )

    value = socketserver.ThreadingUnixStreamServer(str(path), Handler)
    value.daemon_threads = True
    os.chmod(path, 0o600)
    return value
