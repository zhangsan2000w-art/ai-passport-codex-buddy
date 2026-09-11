"""Invisible desktop bridge with automatic Codex Buddy BLE reconnect."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import queue
import socket
import sys
import time
from typing import Optional

if __package__:
    from .ble_client import BleWorker, DeviceInfo
    from .codex_state import CodexStateTracker
    from .controller_settings import (ControllerSettings, default_settings_path,
                                      load_settings, save_settings)
    from .instance_guard import (BridgeInstanceGuard, CONTROL_HOST,
                                 CONTROL_PORT)
    from .notify_listener import NotifyListener
    from .protocol import (build_heartbeat, build_owner, build_status_request,
                           build_time_sync, parse_device_message,
                           redact_protocol_line)
else:
    from ble_client import BleWorker, DeviceInfo
    from codex_state import CodexStateTracker
    from controller_settings import (ControllerSettings, default_settings_path,
                                     load_settings, save_settings)
    from instance_guard import BridgeInstanceGuard, CONTROL_HOST, CONTROL_PORT
    from notify_listener import NotifyListener
    from protocol import (build_heartbeat, build_owner, build_status_request,
                          build_time_sync, parse_device_message,
                          redact_protocol_line)


RECONNECT_SECONDS = 5.0
HEARTBEAT_SECONDS = 10.0


def _logger() -> logging.Logger:
    logger = logging.getLogger("codex-buddy-background")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    log_path = default_settings_path().with_name("background.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_path, maxBytes=256 * 1024,
                                  backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                           datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    return logger


class BackgroundBridge:
    def __init__(self, settings_path: Optional[Path] = None,
                 logger: Optional[logging.Logger] = None) -> None:
        self.settings_path = settings_path
        self.settings = load_settings(settings_path)
        self.events: queue.Queue = queue.Queue()
        self.ble = BleWorker(lambda kind, value: self.events.put((kind, value)))
        self.notify_listener = NotifyListener(
            lambda kind, value: self.events.put((kind, value))
        )
        self.codex_state = CodexStateTracker()
        self.connected = False
        self.scanning = False
        self.connecting_address = ""
        self.current_address = ""
        self.next_scan_at = 0.0
        self.next_heartbeat_at = 0.0
        self.running = True
        self.log = logger or _logger()
        self.control_socket: Optional[socket.socket] = None

    def run(self) -> None:
        self._open_control_socket()
        self.notify_listener.start()
        self.log.info("后台桥已启动")
        try:
            while self.running:
                self._poll_control()
                self._poll_one_event()
                self._tick()
        finally:
            self.notify_listener.stop()
            self.ble.stop()
            if self.control_socket is not None:
                self.control_socket.close()
            self.log.info("后台桥已停止")

    def _open_control_socket(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((CONTROL_HOST, CONTROL_PORT))
            sock.setblocking(False)
            self.control_socket = sock
        except OSError as error:
            sock.close()
            self.log.warning("后台控制端口不可用: %s", error)

    def _poll_control(self) -> None:
        if self.control_socket is None:
            return
        try:
            data, address = self.control_socket.recvfrom(32)
        except BlockingIOError:
            return
        except OSError:
            return
        if address[0] in ("127.0.0.1", "::1") and data.strip() == b"stop":
            self.running = False

    def _poll_one_event(self) -> None:
        try:
            kind, value = self.events.get(timeout=0.1)
        except queue.Empty:
            return
        if kind == "devices":
            self._handle_devices(value)
        elif kind == "connected":
            self._handle_connected(bool(value))
        elif kind == "error":
            self.log.warning("BLE: %s", value)
            self.scanning = False
            self.connecting_address = ""
            self.next_scan_at = time.monotonic() + RECONNECT_SECONDS
        elif kind == "status":
            self.log.info("BLE: %s", value)
        elif kind == "notify_status" or kind == "approval_status":
            self.log.info("%s", value)
        elif kind == "codex_event" or kind == "codex_notify":
            self._handle_codex_event(value)
        elif kind == "codex_approval":
            self._handle_codex_approval(value)
        elif kind == "rx":
            self._handle_rx(str(value))
        elif kind == "tx":
            self.log.info("TX %s", redact_protocol_line(str(value)))

    def _tick(self) -> None:
        now = time.monotonic()
        if (not self.connected and not self.scanning and
                not self.connecting_address and now >= self.next_scan_at):
            self.scanning = True
            self.ble.scan()
        if self.connected and now >= self.next_heartbeat_at:
            self._heartbeat()
            self.next_heartbeat_at = now + HEARTBEAT_SECONDS

    def _handle_devices(self, value: object) -> None:
        self.scanning = False
        devices = list(value) if isinstance(value, list) else []
        selected: Optional[DeviceInfo] = None
        if self.settings.last_device_address:
            selected = next((device for device in devices
                             if device.address == self.settings.last_device_address), None)
        elif len(devices) == 1:
            selected = devices[0]
        if selected is None:
            self.next_scan_at = time.monotonic() + RECONNECT_SECONDS
            if len(devices) > 1 and not self.settings.last_device_address:
                self.log.info("发现多张卡片，先用控制器选择一次目标设备")
            return
        self.connecting_address = selected.address
        self.log.info("正在自动连接 %s", selected.name)
        self.ble.connect(selected.address)

    def _handle_connected(self, connected: bool) -> None:
        if not connected:
            was_connected = self.connected
            self.connected = False
            if not self.connecting_address:
                self.next_scan_at = time.monotonic() + RECONNECT_SECONDS
            if was_connected:
                self.log.info("卡片已断开，等待自动重连")
            return
        self.connected = True
        self.current_address = (self.connecting_address or
                                self.settings.last_device_address)
        self.connecting_address = ""
        if self.current_address and self.current_address != self.settings.last_device_address:
            self.settings.last_device_address = self.current_address
            save_settings(self.settings, self.settings_path)
        self.log.info("卡片已自动连接")
        self._send_bootstrap()
        self._heartbeat()
        self.next_heartbeat_at = time.monotonic() + HEARTBEAT_SECONDS

    def _send(self, payload: bytes) -> None:
        if self.connected:
            self.ble.send(payload)

    def _send_bootstrap(self) -> None:
        now = int(time.time())
        local = time.localtime()
        offset = -int(time.altzone if local.tm_isdst else time.timezone)
        self._send(build_time_sync(now, offset))
        self._send(build_owner(self.settings.owner))
        self._send(build_status_request())

    def _heartbeat(self) -> None:
        values = self.codex_state.heartbeat()
        self._send(build_heartbeat(
            total=values["total"], running=values["running"],
            waiting=values["waiting"], message=values["message"],
            entries=values["entries"], tokens=values["tokens"],
            tokens_today=values["tokens_today"], prompt=values.get("prompt"),
        ))

    def _handle_codex_event(self, payload: object) -> None:
        if not isinstance(payload, dict) or not self.codex_state.apply(payload):
            return
        event_type = str(payload.get("type") or "")
        labels = {
            "codex-turn-start": "Codex 开始工作",
            "codex-tool-start": "Codex 正在使用工具",
            "codex-tool-complete": "Codex 工具执行完成",
            "codex-turn-complete": "Codex 任务完成",
            "codex-session-end": "Codex 会话结束",
        }
        self.log.info("%s", labels.get(event_type, "Codex 状态更新"))
        self._heartbeat()

    def _handle_codex_approval(self, payload: object) -> None:
        if not isinstance(payload, dict) or not self.codex_state.apply(payload):
            return
        self.log.info("Codex 请求授权: %s", payload.get("tool") or "Codex")
        self._heartbeat()

    def _handle_rx(self, line: str) -> None:
        self.log.info("RX %s", redact_protocol_line(line))
        try:
            message = parse_device_message(line)
        except (ValueError, TypeError) as error:
            self.log.warning("忽略无效卡片消息: %s", error)
            return
        if message.kind != "permission":
            return
        request_id = str(message.payload["id"])
        decision = str(message.payload["decision"])
        if not self.notify_listener.resolve_approval(request_id, decision):
            self.log.info("审批已处理或请求已失效")
            return
        self.codex_state.apply({
            "type": "codex-permission-resolved",
            "request_id": request_id,
            "decision": decision,
        })
        self.log.info("卡片已提交%s", "一次允许" if decision == "once" else "拒绝")
        self._heartbeat()


def main() -> int:
    guard = BridgeInstanceGuard()
    if not guard.acquire():
        return 0
    try:
        BackgroundBridge().run()
    finally:
        guard.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
