"""Seed demo device keys for registered active members in RESQ.

Usage:
    python backend/scripts/seed_demo_keys.py [--device-id DEVICE-002]
"""
import argparse
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from backend.app.services.registry_service import registry_service
from backend.app.services.crypto_service import crypto_service, CryptoServiceError


def seed_devices(target_device_id: str = None):
    members = registry_service.get_all_members()
    target_members = [m for m in members if not target_device_id or m.device_id == target_device_id]

    print(f"[*] Inspecting {len(target_members)} member(s) for cryptographic key provisioning...")

    provisioned = 0
    skipped = 0

    for m in target_members:
        if m.status.value != "active":
            print(f"[-] Skipping revoked member: {m.rescue_id} ({m.device_id})")
            skipped += 1
            continue

        try:
            status = crypto_service.get_device_crypto_status(m.device_id)
            if status.is_initialized:
                print(f"[=] Already initialized: {m.rescue_id} ({m.device_id})")
                skipped += 1
                continue

            resp = crypto_service.initialize_device_keys(m.device_id)
            print(f"[+] Provisioned keys for: {m.rescue_id} ({m.device_id}) - {m.name}")
            provisioned += 1
        except Exception as exc:
            print(f"[!] Error provisioning {m.device_id}: {exc}")

    print(f"\n[Done] Provisioned: {provisioned}, Skipped: {skipped}, Total: {len(target_members)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo device keys for RESQ members")
    parser.add_argument("--device-id", type=str, default=None, help="Optional specific device ID to provision")
    args = parser.parse_args()
    seed_devices(args.device_id)
