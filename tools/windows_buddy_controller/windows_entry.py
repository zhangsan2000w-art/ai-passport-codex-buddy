"""Single entry point used by the packaged controller and background agent."""

from __future__ import annotations

import sys
from typing import Optional


def main(argv: Optional[list[str]] = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    mode = arguments[0].lower() if arguments else "controller"

    if mode == "hook":
        from tools.windows_buddy_controller import codex_hook
        return codex_hook.main()
    if mode == "background":
        from tools.windows_buddy_controller import background_bridge
        return background_bridge.main()
    if mode == "install":
        from tools.windows_buddy_controller import bundle_installer
        return bundle_installer.install()
    if mode == "install-final":
        from tools.windows_buddy_controller import bundle_installer
        return bundle_installer.install_final()
    if mode == "uninstall":
        from tools.windows_buddy_controller import bundle_installer
        return bundle_installer.uninstall()
    if mode == "hook-doctor":
        from tools.windows_buddy_controller import bundle_installer
        return bundle_installer.doctor()
    if mode == "hook-smoke-test":
        from pathlib import Path
        from tools.windows_buddy_controller import hook_health
        ok, detail = hook_health.smoke_test_agent(Path(sys.executable))
        print(detail)
        return 0 if ok else 1
    if mode == "self-test":
        from tools.windows_buddy_controller import (
            app,
            background_bridge,
            background_install,
            bundle_installer,
            codex_hook,
            hook_health,
            install_codex_hooks,
        )
        del (app, background_bridge, background_install, bundle_installer,
             codex_hook, hook_health, install_codex_hooks)
        print("Codex Buddy desktop bundle self-test OK")
        return 0
    if mode == "controller":
        from tools.windows_buddy_controller import app
        app.main()
        return 0
    print("未知启动模式。")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
