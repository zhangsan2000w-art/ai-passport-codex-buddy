# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import site
import sys
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).resolve().parents[1]
entry = root / "tools" / "windows_buddy_controller" / "windows_entry.py"

# Keep packaging reproducible and confined to the active virtual environment.
# Some managed Windows accounts expose an unreadable user-site directory even
# when user-site packages are disabled.
site.getusersitepackages = lambda: ""

if sys.platform == "win32":
    platform_name = "Windows"
    hidden = collect_submodules("bleak.backends.winrt") + collect_submodules("winrt")
elif sys.platform == "darwin":
    platform_name = "macOS"
    hidden = collect_submodules("bleak.backends.corebluetooth")
else:
    platform_name = "Linux"
    hidden = collect_submodules("bleak.backends.bluezdbus")

a = Analysis(
    [str(entry)],
    pathex=[str(root)],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    # One app-hosted executable serves the GUI, background process and Hook.
    # Keeping every Bluetooth entry point inside the same bundle gives macOS a
    # stable TCC identity and a required Bluetooth usage description.
    agent = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="CodexBuddyAgent",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    runtime = COLLECT(
        agent,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="Codex-Buddy-macOS-v0.1.4-runtime",
    )
    app = BUNDLE(
        runtime,
        name="Codex Buddy.app",
        icon=None,
        bundle_identifier="cn.codexbuddy.desktop",
        version="0.1.4",
        info_plist={
            "NSPrincipalClass": "NSApplication",
            "NSBluetoothAlwaysUsageDescription":
                "Codex Buddy 使用蓝牙连接您的 AI Passport 卡片。",
        },
    )
else:
    agent = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="CodexBuddyAgent",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    controller = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="CodexBuddyController",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    coll = COLLECT(
        agent,
        controller,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=f"Codex-Buddy-{platform_name}-v0.1.4",
    )
