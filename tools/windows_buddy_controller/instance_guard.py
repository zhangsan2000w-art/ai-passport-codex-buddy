"""Windows single-instance guard and local stop signal for the Buddy bridge."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import socket
import time
from typing import Optional


MUTEX_NAME = "Local\\CodexBuddyBridge-9C8D57C5"
CONTROL_HOST = "127.0.0.1"
CONTROL_PORT = 17323
ERROR_ALREADY_EXISTS = 183


class BridgeInstanceGuard:
    def __init__(self) -> None:
        self._handle: Optional[int] = None

    def acquire(self) -> bool:
        if self._handle is not None:
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
        if self._handle is None:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle(wintypes.HANDLE(self._handle))
        self._handle = None


def request_background_stop() -> None:
    data = b"stop"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(data, (CONTROL_HOST, CONTROL_PORT))
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
