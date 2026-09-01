"""One-shot Windows BLE diagnostic for a Codex Buddy card."""

from __future__ import annotations

import asyncio

from bleak import BleakClient, BleakScanner

from .ble_client import NUS_SERVICE_UUID, NUS_TX_UUID


async def diagnose() -> int:
    print("STAGE=scan", flush=True)
    devices = await BleakScanner.discover(timeout=10.0)
    candidates = [device for device in devices
                  if (device.name or "").startswith("Codex")]
    print("CODEX_COUNT=%d" % len(candidates), flush=True)
    if len(candidates) != 1:
        return 2

    target = candidates[0]
    print("DEVICE=%s [%s]" % (target.name, target.address), flush=True)
    client = BleakClient(
        target,
        pair=True,
        timeout=60.0,
        winrt={"use_cached_services": False},
    )
    try:
        print("STAGE=connect", flush=True)
        await client.connect()
        print("STAGE=connected", flush=True)
        characteristic = client.services.get_characteristic(NUS_TX_UUID)
        print("TX_CHARACTERISTIC=%s" % ("present" if characteristic else "missing"),
              flush=True)
        print("STAGE=start_notify", flush=True)
        await client.start_notify(NUS_TX_UUID, lambda _sender, _data: None)
        print("STAGE=notify_ready", flush=True)
        await asyncio.sleep(1.0)
        await client.stop_notify(NUS_TX_UUID)
        return 0
    except Exception as error:
        print("ERROR_TYPE=%s" % type(error).__name__, flush=True)
        print("ERROR=%s" % error, flush=True)
        return 1
    finally:
        if client.is_connected:
            await client.disconnect()
        print("STAGE=disconnected", flush=True)


def main() -> int:
    return asyncio.run(diagnose())


if __name__ == "__main__":
    raise SystemExit(main())
