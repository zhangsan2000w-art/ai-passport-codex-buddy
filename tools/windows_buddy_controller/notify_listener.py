"""Loopback-only receiver for Codex lifecycle and approval Hook events."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import socket
import threading
import time
from typing import Callable, Dict, Optional

try:
    from .file_bridge import (approval_path, atomic_write_json,
                              default_bridge_dir, ensure_bridge_dirs,
                              event_dir, iter_ready, read_json, response_path,
                              valid_request_id)
except ImportError:
    from file_bridge import (approval_path, atomic_write_json,
                             default_bridge_dir, ensure_bridge_dirs,
                             event_dir, iter_ready, read_json, response_path,
                             valid_request_id)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 17321
DEFAULT_APPROVAL_PORT = 17322
MAX_EVENT_BYTES = 8192


@dataclass
class _ApprovalWaiter:
    event: threading.Event = field(default_factory=threading.Event)
    decision: Optional[str] = None
    request_path: Optional[Path] = None
    response_path: Optional[Path] = None
    created_at: float = field(default_factory=time.monotonic)


class NotifyListener:
    def __init__(self, callback: Callable[[str, object], None],
                 host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 approval_port: int = DEFAULT_APPROVAL_PORT,
                 bridge_dir: Optional[Path] = None) -> None:
        self._callback = callback
        self._host = host
        self._port = port
        self._approval_port = approval_port
        self._bridge_dir = bridge_dir or default_bridge_dir()
        self._thread: Optional[threading.Thread] = None
        self._approval_thread: Optional[threading.Thread] = None
        self._bridge_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._socket: Optional[socket.socket] = None
        self._approval_socket: Optional[socket.socket] = None
        self._approval_lock = threading.Lock()
        self._approvals: Dict[str, _ApprovalWaiter] = {}

    @property
    def port(self) -> int:
        return self._port

    @property
    def approval_port(self) -> int:
        return self._approval_port

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="codex-buddy-notify")
        self._approval_thread = threading.Thread(
            target=self._run_approval_server, daemon=True,
            name="codex-buddy-approval",
        )
        self._bridge_thread = threading.Thread(
            target=self._run_file_bridge, daemon=True,
            name="codex-buddy-file-bridge",
        )
        self._thread.start()
        self._approval_thread.start()
        self._bridge_thread.start()

    def stop(self) -> None:
        self._stop.set()
        sock, self._socket = self._socket, None
        if sock is not None:
            sock.close()
        approval_sock, self._approval_socket = self._approval_socket, None
        if approval_sock is not None:
            approval_sock.close()
        with self._approval_lock:
            waiters = list(self._approvals.values())
        for waiter in waiters:
            if waiter.response_path is not None:
                try:
                    atomic_write_json(waiter.response_path, {"decision": "fallback"})
                except (OSError, ValueError):
                    pass
            waiter.event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._approval_thread is not None:
            self._approval_thread.join(timeout=1.0)
        if self._bridge_thread is not None:
            self._bridge_thread.join(timeout=1.0)

    def resolve_approval(self, request_id: str, decision: str) -> bool:
        if decision not in ("once", "deny"):
            return False
        with self._approval_lock:
            waiter = self._approvals.get(request_id)
            if waiter is None or waiter.event.is_set():
                return False
            if waiter.response_path is not None:
                try:
                    atomic_write_json(waiter.response_path, {"decision": decision})
                except (OSError, ValueError):
                    return False
            waiter.decision = decision
            waiter.event.set()
            if waiter.response_path is not None:
                self._approvals.pop(request_id, None)
                if waiter.request_path is not None:
                    try:
                        waiter.request_path.unlink()
                    except FileNotFoundError:
                        pass
            return True

    def _dispatch_event(self, payload: Dict[str, object]) -> None:
        event_type = payload.get("type")
        if event_type == "codex-turn-complete":
            self._callback("codex_notify", payload)
        elif event_type in {
            "codex-turn-start", "codex-tool-start",
            "codex-tool-complete", "codex-session-end",
        }:
            self._callback("codex_event", payload)

    def _run_file_bridge(self) -> None:
        try:
            root = ensure_bridge_dirs(self._bridge_dir)
            self._callback("notify_status", "Codex 本地文件桥已就绪")
            while not self._stop.is_set():
                for path in iter_ready(event_dir(root), "event-*.json"):
                    try:
                        self._dispatch_event(read_json(path))
                    except (OSError, ValueError, json.JSONDecodeError):
                        self._callback("notify_status", "忽略了无效的本地文件事件")
                    finally:
                        try:
                            path.unlink()
                        except FileNotFoundError:
                            pass

                approval_directory = root / "approvals"
                for path in iter_ready(approval_directory, "approval-*.json"):
                    try:
                        payload = read_json(path)
                        request_id = str(payload.get("request_id") or "")
                        if (payload.get("type") != "codex-permission-request" or
                                not valid_request_id(request_id)):
                            raise ValueError("invalid approval request")
                        with self._approval_lock:
                            if request_id in self._approvals:
                                continue
                            self._approvals[request_id] = _ApprovalWaiter(
                                request_path=path,
                                response_path=response_path(request_id, root),
                            )
                        self._callback("codex_approval", payload)
                    except (OSError, ValueError, json.JSONDecodeError):
                        try:
                            path.unlink()
                        except FileNotFoundError:
                            pass

                with self._approval_lock:
                    for request_id, waiter in list(self._approvals.items()):
                        if waiter.request_path is None:
                            continue
                        if (not waiter.request_path.exists() or
                                time.monotonic() - waiter.created_at > 620.0):
                            self._approvals.pop(request_id, None)
                self._stop.wait(0.1)
        except OSError as error:
            self._callback("notify_status", "Codex 本地文件桥不可用: " + str(error))

    def _run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket = sock
        try:
            sock.bind((self._host, self._port))
            self._port = int(sock.getsockname()[1])
            sock.settimeout(0.5)
            self._callback("notify_status", "Codex 本地提醒端口已就绪")
            while not self._stop.is_set():
                try:
                    data, address = sock.recvfrom(8192)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if address[0] not in ("127.0.0.1", "::1"):
                    continue
                try:
                    payload = json.loads(data.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._callback("notify_status", "忽略了无效的本地提醒")
                    continue
                if not isinstance(payload, dict):
                    continue
                self._dispatch_event(payload)
        except OSError as error:
            self._callback("notify_status", "Codex 本地提醒端口不可用: " + str(error))
        finally:
            if self._socket is sock:
                self._socket = None
            sock.close()

    def _run_approval_server(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._approval_socket = sock
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self._host, self._approval_port))
            self._approval_port = int(sock.getsockname()[1])
            sock.listen(8)
            sock.settimeout(0.5)
            self._callback("approval_status", "Codex 双端审批端口已就绪")
            while not self._stop.is_set():
                try:
                    connection, address = sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                if address[0] not in ("127.0.0.1", "::1"):
                    connection.close()
                    continue
                threading.Thread(
                    target=self._handle_approval_connection,
                    args=(connection,), daemon=True,
                    name="codex-buddy-approval-request",
                ).start()
        except OSError as error:
            self._callback("approval_status", "Codex 双端审批端口不可用: " + str(error))
        finally:
            if self._approval_socket is sock:
                self._approval_socket = None
            sock.close()

    def _handle_approval_connection(self, connection: socket.socket) -> None:
        request_id = ""
        waiter: Optional[_ApprovalWaiter] = None
        try:
            connection.settimeout(5.0)
            data = bytearray()
            while len(data) < MAX_EVENT_BYTES:
                chunk = connection.recv(min(1024, MAX_EVENT_BYTES - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if b"\n" in chunk:
                    break
            if b"\n" not in data:
                return
            payload = json.loads(bytes(data).split(b"\n", 1)[0].decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("type") != "codex-permission-request":
                return
            request_id = str(payload.get("request_id") or "")
            if not request_id or len(request_id.encode("utf-8")) > 63:
                return
            waiter = _ApprovalWaiter()
            with self._approval_lock:
                if request_id in self._approvals:
                    return
                self._approvals[request_id] = waiter
            self._callback("codex_approval", payload)
            connection.settimeout(None)
            while not self._stop.is_set() and not waiter.event.wait(0.25):
                pass
            decision = waiter.decision or "fallback"
            response = json.dumps(
                {"decision": decision}, ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8") + b"\n"
            connection.sendall(response)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return
        finally:
            if request_id:
                with self._approval_lock:
                    if self._approvals.get(request_id) is waiter:
                        self._approvals.pop(request_id, None)
            connection.close()
