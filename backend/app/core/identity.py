import base64
import os
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives import serialization

def generate_device_identity(device_id: str, keys_dir: str = "../../../keys") -> dict:
    """
    Generates signing and encryption key pairs for a device.
    Saves private keys locally and returns public keys (in canonical Base64 format) for the registry.
    """
    # Ensure the keys directory exists
    os.makedirs(keys_dir, exist_ok=True)

    # 1. Generate Signing Key Pair (Ed25519)
    signing_private_key = ed25519.Ed25519PrivateKey.generate()
    signing_public_key = signing_private_key.public_key()

    # 2. Generate Encryption Key Pair (X25519)
    encryption_private_key = x25519.X25519PrivateKey.generate()
    encryption_public_key = encryption_private_key.public_key()

    # 3. Save Private Keys locally (Never share these!)
    sign_key_path = os.path.join(keys_dir, f"{device_id}_sign.pem")
    enc_key_path = os.path.join(keys_dir, f"{device_id}_enc.pem")

    def save_private_key(key_obj, filepath):
        with open(filepath, "wb") as f:
            f.write(key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

    save_private_key(signing_private_key, sign_key_path)
    save_private_key(encryption_private_key, enc_key_path)

    # 4. Return Public Keys for the Registry (Standard Base64 formatted)
    raw_signing_pub = signing_public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    raw_enc_pub = encryption_public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

    return {
        "device_id": device_id,
        "signing_public_key": base64.b64encode(raw_signing_pub).decode("utf-8"),
        "encryption_public_key": base64.b64encode(raw_enc_pub).decode("utf-8"),
    }

if __name__ == "__main__":
    result = generate_device_identity("test-device")
    print(result)