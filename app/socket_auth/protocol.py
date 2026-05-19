"""פרוטוקול הודעות JSON מעל TCP (אורך 4 בתים + גוף UTF-8)."""
from __future__ import annotations

import json
import socket
import struct
from typing import Any

MAX_MESSAGE_BYTES = 64 * 1024


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    received = 0
    while received < size:
        part = sock.recv(size - received)
        if not part:
            raise ConnectionError("החיבור נסגר לפני שקיבלנו את כל ההודעה")
        chunks.append(part)
        received += len(part)
    return b"".join(chunks)


def send_message(sock: socket.socket, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(data) > MAX_MESSAGE_BYTES:
        raise ValueError("ההודעה גדולה מדי")
    sock.sendall(struct.pack(">I", len(data)) + data)


def recv_message(sock: socket.socket) -> dict[str, Any]:
    header = _recv_exact(sock, 4)
    length = struct.unpack(">I", header)[0]
    if length == 0 or length > MAX_MESSAGE_BYTES:
        raise ValueError("גודל הודעה לא חוקי")
    body = _recv_exact(sock, length)
    parsed = json.loads(body.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("ההודעה חייבת להיות אובייקט JSON")
    return parsed
