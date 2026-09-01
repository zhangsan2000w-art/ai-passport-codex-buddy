"""Chinese Windows controller and local Codex notification bridge."""

import json
import queue
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict

if __package__:
    from .ble_client import BleWorker, DeviceInfo
    from .codex_state import CodexStateTracker
    from .controller_settings import load_settings, save_settings
    from .background_install import autostart_is_installed, launch_background
    from .instance_guard import acquire_after_stopping_background
    from .notify_listener import NotifyListener
    from .protocol import (build_heartbeat, build_name, build_owner,
                           build_status_request, build_time_sync, build_unpair,
                           parse_device_message, redact_protocol_line)
    from .scenarios import ScenarioController
else:
    from ble_client import BleWorker, DeviceInfo
    from codex_state import CodexStateTracker
    from controller_settings import load_settings, save_settings
    from background_install import autostart_is_installed, launch_background
    from instance_guard import acquire_after_stopping_background
    from notify_listener import NotifyListener
    from protocol import (build_heartbeat, build_name, build_owner,
                          build_status_request, build_time_sync, build_unpair,
                          parse_device_message, redact_protocol_line)
    from scenarios import ScenarioController


class BuddyControllerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Codex Buddy 控制器")
        self.geometry("980x720")
        self.minsize(850, 620)
        self.events: queue.Queue = queue.Queue()
        self.ble = BleWorker(lambda kind, value: self.events.put((kind, value)))
        self.notify_listener = NotifyListener(
            lambda kind, value: self.events.put((kind, value))
        )
        self.scenario = ScenarioController()
        self.codex_state = CodexStateTracker()
        self.controller_settings = load_settings()
        self.connected = False
        self.auto_running = False
        self.live_mode = False
        self.hook_live = False
        self.device_by_label: Dict[str, DeviceInfo] = {}
        self.connecting_address = ""
        self._build_ui()
        self.notify_listener.start()
        self.after(50, self._poll_events)
        self.after(10000, self._heartbeat_timer)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self) -> None:
        connection = ttk.LabelFrame(self, text="蓝牙连接", padding=8)
        connection.pack(fill="x", padx=8, pady=6)
        self.device_box = ttk.Combobox(connection, state="readonly", width=58)
        self.device_box.pack(side="left", padx=4)
        ttk.Button(connection, text="扫描", command=self.ble.scan).pack(side="left", padx=3)
        ttk.Button(connection, text="连接", command=self._connect).pack(side="left", padx=3)
        ttk.Button(connection, text="断开", command=self.ble.disconnect).pack(side="left", padx=3)
        self.status_var = tk.StringVar(value="未连接")
        ttk.Label(connection, textvariable=self.status_var).pack(side="left", padx=12)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8)
        controls = ttk.Frame(body)
        controls.pack(side="left", fill="y", padx=(0, 8))
        log_frame = ttk.LabelFrame(body, text="协议日志", padding=5)
        log_frame.pack(side="left", fill="both", expand=True)

        identity = ttk.LabelFrame(controls, text="设备信息", padding=8)
        identity.pack(fill="x", pady=4)
        self.owner_var = tk.StringVar(value=self.controller_settings.owner)
        self.name_var = tk.StringVar(value="Codex Buddy")
        self._entry_row(identity, "使用者", self.owner_var)
        self._entry_row(identity, "设备名称", self.name_var)
        ttk.Button(identity, text="同步时间、使用者和状态", command=self._send_bootstrap).pack(fill="x", pady=2)
        ttk.Button(identity, text="设置设备名称", command=lambda: self._send(build_name(self.name_var.get()))).pack(fill="x", pady=2)
        ttk.Button(identity, text="读取设备状态", command=lambda: self._send(build_status_request())).pack(fill="x", pady=2)
        ttk.Button(identity, text="请求取消配对", command=lambda: self._send(build_unpair())).pack(fill="x", pady=2)

        live = ttk.LabelFrame(controls, text="Codex 实时桥", padding=8)
        live.pack(fill="x", pady=4)
        self.codex_bridge_var = tk.StringVar(value="等待 Codex Hook 事件")
        ttk.Label(live, textvariable=self.codex_bridge_var, wraplength=265,
                  justify="left").pack(fill="x", pady=(0, 4))
        live_actions = ttk.Frame(live)
        live_actions.pack(fill="x")
        self.live_approve_button = ttk.Button(
            live_actions, text="一次允许", command=lambda: self._resolve_live_approval("once")
        )
        self.live_approve_button.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.live_deny_button = ttk.Button(
            live_actions, text="拒绝", command=lambda: self._resolve_live_approval("deny")
        )
        self.live_deny_button.pack(side="left", fill="x", expand=True, padx=(2, 0))
        self.live_approve_button.configure(state="disabled")
        self.live_deny_button.configure(state="disabled")

        manual = ttk.LabelFrame(controls, text="手动测试场景", padding=8)
        manual.pack(fill="x", pady=4)
        for label, action in (("空闲", self.scenario.set_idle),
                              ("工作中", self.scenario.set_busy),
                              ("任务完成", self.scenario.set_completed),
                              ("休眠", self.scenario.set_sleep)):
            ttk.Button(manual, text=label,
                       command=lambda fn=action: self._scenario(fn)).pack(fill="x", pady=2)

        approval = ttk.LabelFrame(controls, text="授权请求测试", padding=8)
        approval.pack(fill="x", pady=4)
        self.prompt_id_var = tk.StringVar(value="req_test_001")
        self.tool_var = tk.StringVar(value="Shell")
        self.hint_var = tk.StringVar(value="git status")
        self._entry_row(approval, "请求编号", self.prompt_id_var)
        self._entry_row(approval, "工具", self.tool_var)
        self._entry_row(approval, "提示", self.hint_var)
        ttk.Button(approval, text="发送授权请求", command=self._send_approval).pack(fill="x", pady=2)
        ttk.Button(approval, text="清除请求", command=lambda: self._scenario(self.scenario.clear_prompt)).pack(fill="x", pady=2)

        automatic = ttk.LabelFrame(controls, text="自动循环测试", padding=8)
        automatic.pack(fill="x", pady=4)
        self.auto_interval = tk.IntVar(value=8)
        ttk.Spinbox(automatic, from_=3, to=60, textvariable=self.auto_interval, width=6).pack(side="left")
        ttk.Label(automatic, text=" 秒").pack(side="left")
        self.auto_button = ttk.Button(automatic, text="开始", command=self._toggle_auto)
        self.auto_button.pack(side="right")

        self.log = tk.Text(log_frame, wrap="word", state="disabled", font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        ttk.Button(self, text="清空日志", command=self._clear_log).pack(anchor="e", padx=10, pady=5)

    @staticmethod
    def _entry_row(parent: ttk.Widget, label: str, variable: tk.StringVar) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=1)
        ttk.Label(row, text=label, width=12).pack(side="left")
        ttk.Entry(row, textvariable=variable, width=28).pack(side="left", fill="x", expand=True)

    def _connect(self) -> None:
        info = self.device_by_label.get(self.device_box.get())
        if info is None:
            messagebox.showinfo("请选择设备", "请先扫描并选择一个 Codex-* 设备。")
            return
        self.connecting_address = info.address
        self.ble.connect(info.address)

    def _send(self, payload: bytes) -> None:
        if not self.connected:
            self._append("! 设备未连接")
            return
        self.ble.send(payload)

    def _send_bootstrap(self) -> None:
        owner = self.owner_var.get().strip() or "用户"
        if owner != self.controller_settings.owner:
            self.controller_settings.owner = owner
            save_settings(self.controller_settings)
        now = int(time.time())
        offset = -int(time.timezone if not time.localtime().tm_isdst else time.altzone)
        self._send(build_time_sync(now, offset))
        self._send(build_owner(owner))
        self._send(build_status_request())

    def _heartbeat(self) -> None:
        values = self.codex_state.heartbeat() if self.live_mode else self.scenario.heartbeat()
        self._send(build_heartbeat(total=values["total"], running=values["running"],
                                   waiting=values["waiting"], message=values["message"],
                                   entries=values["entries"], tokens=values["tokens"],
                                   tokens_today=values["tokens_today"],
                                   prompt=values.get("prompt")))

    def _scenario(self, action: Any) -> None:
        self.live_mode = False
        action()
        self._heartbeat()

    def _send_approval(self) -> None:
        self.live_mode = False
        request_id = self.scenario.set_fresh_approval(
            self.tool_var.get(), self.hint_var.get()
        )
        self.prompt_id_var.set(request_id)
        self._heartbeat()
        if self.connected:
            self.status_var.set("测试审批已同步到卡片，等待卡片操作")
            self._append("测试审批已同步到卡片")
        else:
            self.status_var.set("测试审批已登记，连接卡片后自动同步")

    def _toggle_auto(self) -> None:
        self.auto_running = not self.auto_running
        self.auto_button.configure(text="停止" if self.auto_running else "开始")
        if self.auto_running:
            self._auto_step()

    def _auto_step(self) -> None:
        if not self.auto_running:
            return
        self.live_mode = False
        scenario = self.scenario.advance_auto()
        self._append("AUTO " + scenario.name)
        self._heartbeat()
        self.after(max(3, self.auto_interval.get()) * 1000, self._auto_step)

    def _heartbeat_timer(self) -> None:
        if self.connected:
            self._heartbeat()
        self.after(10000, self._heartbeat_timer)

    def _poll_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "devices":
                    self.device_by_label = {
                        "%s  [%s]" % (device.name, device.address): device for device in value
                    }
                    self.device_box["values"] = list(self.device_by_label)
                    if self.device_by_label:
                        self.device_box.current(0)
                elif kind == "connected":
                    self.connected = bool(value)
                    if self.connected:
                        if self.connecting_address:
                            self.controller_settings.last_device_address = self.connecting_address
                            save_settings(self.controller_settings)
                        self.connecting_address = ""
                        self.after(250, self._send_bootstrap)
                        self.after(500, self._heartbeat)
                elif kind == "status":
                    self.status_var.set(str(value))
                elif kind == "tx":
                    self._append("TX " + redact_protocol_line(str(value)))
                elif kind == "rx":
                    self._handle_rx(str(value))
                elif kind == "error":
                    self._append("ERROR " + str(value))
                elif kind == "notify_status":
                    self._append(str(value))
                elif kind == "approval_status":
                    self._append(str(value))
                elif kind == "codex_event":
                    self._handle_codex_event(value)
                elif kind == "codex_approval":
                    self._handle_codex_approval(value)
                elif kind == "codex_notify":
                    self._handle_codex_notify(value)
        except queue.Empty:
            pass
        self.after(50, self._poll_events)

    def _handle_rx(self, line: str) -> None:
        self._append("RX " + redact_protocol_line(line))
        try:
            message = parse_device_message(line)
            if message.kind == "permission":
                decisions = {"once": "单次允许", "always": "始终允许", "deny": "拒绝"}
                decision = decisions.get(str(message.payload["decision"]).lower(),
                                         str(message.payload["decision"]))
                request_id = str(message.payload["id"])
                raw_decision = str(message.payload["decision"]).lower()
                if self.notify_listener.resolve_approval(request_id, raw_decision):
                    self._mark_approval_resolved(request_id, raw_decision, "卡片")
                    self.status_var.set("卡片已提交授权结果: " + decision)
                elif not self.live_mode and self.scenario.resolve_approval(
                        request_id, raw_decision):
                    self.status_var.set("卡片已完成测试审批: " + decision)
                    self._append("卡片已处理测试审批: " + decision)
                    self._heartbeat()
                else:
                    self.status_var.set("授权已处理或请求已失效")
                    self._append("忽略了已处理或不匹配的卡片审批")
            elif message.kind == "status":
                self.status_var.set("已收到设备状态")
                self._append(json.dumps(message.payload.get("data", {}), indent=2,
                                        ensure_ascii=False))
        except (ValueError, json.JSONDecodeError) as error:
            self._append("解析失败 " + str(error))

    def _handle_codex_notify(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        if payload.get("source") != "hook" and self.hook_live:
            self._append("忽略重复的旧式 Codex 完成提醒")
            return
        self._handle_codex_event(payload)
        message = str(payload.get("message") or "Codex 任务已完成")
        project = str(payload.get("project") or "")
        self._append("CODEX 完成" + (" · " + project if project else "") + ": " + message)
        self.status_var.set("已收到 Codex 任务完成提醒")

    def _handle_codex_event(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        if payload.get("source") == "hook":
            self.hook_live = True
        if not self.codex_state.apply(payload):
            return
        self.live_mode = True
        event_type = str(payload.get("type") or "")
        labels = {
            "codex-turn-start": "Codex 开始工作",
            "codex-tool-start": "Codex 正在使用工具",
            "codex-tool-complete": "Codex 工具执行完成",
            "codex-turn-complete": "Codex 任务完成",
            "codex-session-end": "Codex 会话结束",
        }
        self._append(labels.get(event_type, "Codex 状态更新"))
        self._refresh_codex_panel()
        if self.connected:
            self._heartbeat()

    def _handle_codex_approval(self, payload: object) -> None:
        if not isinstance(payload, dict) or not self.codex_state.apply(payload):
            return
        self.live_mode = True
        self.hook_live = True
        tool = str(payload.get("tool") or "Codex")
        self._append("Codex 请求授权: " + tool)
        self.status_var.set("等待电脑或卡片审批")
        self._refresh_codex_panel()
        if self.connected:
            self._heartbeat()

    def _resolve_live_approval(self, decision: str) -> None:
        approval = self.codex_state.current_approval
        if approval is None:
            self._append("没有等待处理的 Codex 审批")
            return
        if not self.notify_listener.resolve_approval(approval.request_id, decision):
            self._append("审批已由另一端处理")
            self._refresh_codex_panel()
            return
        self._mark_approval_resolved(approval.request_id, decision, "电脑")

    def _mark_approval_resolved(self, request_id: str, decision: str,
                                source: str) -> None:
        self.codex_state.apply({
            "type": "codex-permission-resolved",
            "request_id": request_id,
            "decision": decision,
        })
        label = "一次允许" if decision == "once" else "拒绝"
        self._append("%s已%s Codex 请求" % (source, label))
        self.status_var.set("%s审批已提交" % source)
        self._refresh_codex_panel()
        if self.connected:
            self._heartbeat()

    def _refresh_codex_panel(self) -> None:
        approval = self.codex_state.current_approval
        if approval is None:
            heartbeat = self.codex_state.heartbeat()
            self.codex_bridge_var.set(str(heartbeat["message"]))
            self.live_approve_button.configure(state="disabled")
            self.live_deny_button.configure(state="disabled")
            return
        hint = " ".join(approval.hint.split())
        self.codex_bridge_var.set(
            "等待审批 · %s%s" % (approval.tool, "\n" + hint if hint else "")
        )
        self.live_approve_button.configure(state="normal")
        self.live_deny_button.configure(state="normal")

    def _append(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", time.strftime("%H:%M:%S ") + text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _close(self) -> None:
        self.auto_running = False
        self.notify_listener.stop()
        self.ble.stop()
        self.destroy()


def main() -> None:
    guard = acquire_after_stopping_background()
    if guard is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Codex Buddy", "后台桥仍在退出，请稍后再打开控制器。")
        root.destroy()
        return
    restart_background = autostart_is_installed()
    try:
        BuddyControllerApp().mainloop()
    finally:
        guard.close()
        if restart_background:
            launch_background()


if __name__ == "__main__":
    main()
