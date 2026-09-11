"""Cross-platform single-instance guard and local stop signal."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import socket
import tempfile
import time
from typing import Optional


MUTEX_NAME = "Local\\CodexBuddyBridge-9C8D57C5"
CONTROL_HOST = "127.0.0.1"
CONTROL_PORT = 17325
LEGACY_CONTROL_PORTS = (17323,)
ERROR_ALREADY_EXISTS = 183


class BridgeInstanceGuard:
    def __init__(self) -> None:
        self._handle: Optional[int] = None
        self._lock_file = None

    def acquire(self) -> bool:
        if self._handle is not None or self._lock_file is not None:
            return True
        if os.name != "nt":
            import fcntl

            lock_path = Path(tempfile.gettempdir()) / "codex-buddy-bridge.lock"
            handle = lock_path.open("a+b")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                handle.close()
                return False
            self._lock_file = handle
            return True
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL,
                                          wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if not handle:
            return False
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False
        self._handle = int(handle)
        return True

    def close(self) -> None:
        if self._lock_file is not None:
            import fcntl

            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            self._lock_file.close()
            self._lock_file = None
            return
        if self._handle is None:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle(wintypes.HANDLE(self._handle))
        self._handle = None


def request_background_stop() -> None:
    data = b"stop"
    for port in (CONTROL_PORT,) + LEGACY_CONTROL_PORTS:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(data, (CONTROL_HOST, port))
        except OSError:
            pass


def acquire_after_stopping_background(timeout: float = 5.0) -> Optional[BridgeInstanceGuard]:
    guard = BridgeInstanceGuard()
    if guard.acquire():
        return guard
    request_background_stop()
    deadline = time.monotonic() + max(0.1, timeout)
    while time.monotonic() < deadline:
        time.sleep(0.1)
        if guard.acquire():
            return guard
    return None
