"""Best-effort systemd notify. This is a supervisor heartbeat, not a SIL loop."""

from __future__ import annotations

import os
import socket
import threading
import time


def notify(status: str) -> None:
    address = os.environ.get("NOTIFY_SOCKET")
    if not address:
        return
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        target = ("\0" + address[1:]) if address.startswith("@") else address
        sock.sendto(status.encode("utf-8"), target)
        sock.close()
    except OSError:
        return


def start_watchdog(interval_s: float = 10.0) -> threading.Thread | None:
    if not os.environ.get("NOTIFY_SOCKET"):
        return None
    notify("READY=1")

    def _loop() -> None:
        while True:
            notify("WATCHDOG=1")
            time.sleep(interval_s)

    thread = threading.Thread(target=_loop, name="certarig-watchdog", daemon=True)
    thread.start()
    return thread
