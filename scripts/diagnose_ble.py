"""Minimal BLE health check used by troubleshooting and CI/manual tests."""

from __future__ import annotations

import asyncio
import traceback

from bleak import BleakScanner
from ns2pro_bridge.radio import bluetooth_radio_state


async def main() -> None:
    print(f"Bluetooth radio state: {await bluetooth_radio_state()}")
    scanner = BleakScanner(scanning_mode="active")
    try:
        await scanner.start()
        await asyncio.sleep(2)
        print("BLE scan start/stop: OK")
    except Exception:
        traceback.print_exc()
        raise
    finally:
        try:
            await scanner.stop()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
