import base64
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app.core.crypto import (
    CryptoError,
    DecryptionAuthenticationError,
    InvalidKeyTypeError,
    InvalidPublicKeyError,
    build_envelope_aad,
    canonicalize_payload,
    decode_ed25519_public_key_b64,
    decode_x25519_public_key_b64,
    decrypt_authenticated,
    derive_encryption_key,
    derive_shared_secret,
    encode_public_key_b64,
    encrypt_authenticated,
    generate_ed25519_keypair,
    generate_x25519_keypair,
    load_ed25519_private_key_pem,
    load_x25519_private_key_pem,
    serialize_private_key_pem,
    sign_bytes,
    verify_signature,
)
from backend.app.main import app
from backend.app.models.crypto import EncryptionEnvelope
from backend.app.services.crypto_service import (
    CryptoService,
    DeviceAlreadyInitializedError,
    InconsistentKeyStateError,
    crypto_service,
)
from backend.app.services.registry_service import RegistryService, registry_service
from backend.app.storage.json_store import load_json, save_json

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_crypto_and_registry(tmp_path: Path):
    """Isolates both registry file and keys directory to tmp_path for all crypto tests."""
    temp_registry = tmp_path / "registry.json"
    save_json(temp_registry, {"version": 1, "members": []})

    temp_keys = tmp_path / "keys"
    temp_keys.mkdir(parents=True, exist_ok=True)

    orig_reg_path = registry_service.registry_path
    orig_crypto_keys = crypto_service.keys_dir

    registry_service.registry_path = temp_registry
    crypto_service.keys_dir = temp_keys
    crypto_service.registry_service = registry_service

    yield tmp_path

    registry_service.registry_path = orig_reg_path
    crypto_service.keys_dir = orig_crypto_keys
    crypto_service.registry_service = registry_service


# ---------------------------------------------------------------------------
# 1. Key Generation & Serialization Tests
# ---------------------------------------------------------------------------

def test_ed25519_key_generation_and_serialization():
    priv, pub = generate_ed25519_keypair()
    pub_b64 = encode_public_key_b64(pub)
    assert len(base64.b64decode(pub_b64)) == 32

    decoded_pub = decode_ed25519_public_key_b64(pub_b64)
    assert encode_public_key_b64(decoded_pub) == pub_b64

    pem = serialize_private_key_pem(priv)
    assert b"BEGIN PRIVATE KEY" in pem
    loaded_priv = load_ed25519_private_key_pem(pem)
    assert encode_public_key_b64(loaded_priv.public_key()) == pub_b64


def test_x25519_key_generation_and_serialization():
    priv, pub = generate_x25519_keypair()
    pub_b64 = encode_public_key_b64(pub)
    assert len(base64.b64decode(pub_b64)) == 32

    decoded_pub = decode_x25519_public_key_b64(pub_b64)
    assert encode_public_key_b64(decoded_pub) == pub_b64

    pem = serialize_private_key_pem(priv)
    assert b"BEGIN PRIVATE KEY" in pem
    loaded_priv = load_x25519_private_key_pem(pem)
    assert encode_public_key_b64(loaded_priv.public_key()) == pub_b64


def test_private_key_type_safety_rejects_cross_loading():
    ed_priv, _ = generate_ed25519_keypair()
    x_priv, _ = generate_x25519_keypair()

    ed_pem = serialize_private_key_pem(ed_priv)
    x_pem = serialize_private_key_pem(x_priv)

    # Attempting to load Ed25519 PEM as X25519 must fail
    with pytest.raises(InvalidKeyTypeError):
        load_x25519_private_key_pem(ed_pem)

    # Attempting to load X25519 PEM as Ed25519 must fail
    with pytest.raises(InvalidKeyTypeError):
        load_ed25519_private_key_pem(x_pem)


# ---------------------------------------------------------------------------
# 2. Digital Signatures & Canonicalization Tests
# ---------------------------------------------------------------------------

def test_signature_valid_verifies():
    priv, pub = generate_ed25519_keypair()
    data = b"Triage Report: Sector 4 Blackout Active"
    sig_b64 = sign_bytes(priv, data)

    assert verify_signature(pub, data, sig_b64) is True


def test_signature_modified_payload_fails():
    priv, pub = generate_ed25519_keypair()
    data = b"Authentic Message"
    sig_b64 = sign_bytes(priv, data)

    assert verify_signature(pub, b"Tampered Message", sig_b64) is False


def test_signature_modified_signature_fails():
    priv, pub = generate_ed25519_keypair()
    data = b"Authentic Message"
    sig_bytes = bytearray(base64.b64decode(sign_bytes(priv, data)))
    sig_bytes[0] ^= 0xFF
    bad_sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")

    assert verify_signature(pub, data, bad_sig_b64) is False


def test_signature_wrong_public_key_fails():
    priv1, _ = generate_ed25519_keypair()
    _, pub2 = generate_ed25519_keypair()
    data = b"Authentic Message"
    sig_b64 = sign_bytes(priv1, data)

    assert verify_signature(pub2, data, sig_b64) is False


def test_canonicalization_insertion_order_independence():
    dict1 = {"team": "Alpha", "priority": 1, "unit": "RESQ-001"}
    dict2 = {"unit": "RESQ-001", "team": "Alpha", "priority": 1}

    bytes1 = canonicalize_payload(dict1)
    bytes2 = canonicalize_payload(dict2)

    assert bytes1 == bytes2
    assert bytes1 == b'{"priority":1,"team":"Alpha","unit":"RESQ-001"}'


# ---------------------------------------------------------------------------
# 3. Key Agreement & Authenticated Encryption Tests
# ---------------------------------------------------------------------------

def test_key_agreement_two_parties_derive_same_secret():
    alice_priv, alice_pub = generate_x25519_keypair()
    bob_priv, bob_pub = generate_x25519_keypair()

    secret_alice = derive_shared_secret(alice_priv, bob_pub)
    secret_bob = derive_shared_secret(bob_priv, alice_pub)

    assert secret_alice == secret_bob
    assert len(secret_alice) == 32


def test_key_agreement_different_keys_derive_different_secret():
    alice_priv, _ = generate_x25519_keypair()
    bob_priv, bob_pub = generate_x25519_keypair()
    carol_priv, carol_pub = generate_x25519_keypair()

    secret_alice_bob = derive_shared_secret(alice_priv, bob_pub)
    secret_carol_bob = derive_shared_secret(carol_priv, bob_pub)

    assert secret_alice_bob != secret_carol_bob


def test_authenticated_encryption_roundtrip():
    recipient_priv, recipient_pub = generate_x25519_keypair()
    plaintext = b"Life-critical distress dispatch: Medic needed at Station 3"
    caller_aad = b"routing_metadata:hop_count=2"

    envelope = encrypt_authenticated(recipient_pub, plaintext, associated_data=caller_aad)
    decrypted = decrypt_authenticated(recipient_priv, envelope)

    assert decrypted == plaintext


def test_encryption_supports_empty_plaintext():
    recipient_priv, recipient_pub = generate_x25519_keypair()
    empty_plaintext = b""

    envelope = encrypt_authenticated(recipient_pub, empty_plaintext)
    # Ciphertext must contain at least the 16-byte Poly1305 authentication tag
    raw_ciphertext = base64.b64decode(envelope.ciphertext)
    assert len(raw_ciphertext) == 16

    decrypted = decrypt_authenticated(recipient_priv, envelope)
    assert decrypted == b""


def test_encryption_generates_fresh_salt_nonce_and_ciphertext():
    recipient_priv, recipient_pub = generate_x25519_keypair()
    plaintext = b"Identical Plaintext Message"

    env1 = encrypt_authenticated(recipient_pub, plaintext)
    env2 = encrypt_authenticated(recipient_pub, plaintext)

    assert env1.nonce != env2.nonce
    assert env1.salt != env2.salt
    assert env1.ephemeral_public_key != env2.ephemeral_public_key
    assert env1.ciphertext != env2.ciphertext

    assert decrypt_authenticated(recipient_priv, env1) == plaintext
    assert decrypt_authenticated(recipient_priv, env2) == plaintext


def test_tampered_ciphertext_fails_decryption():
    recipient_priv, recipient_pub = generate_x25519_keypair()
    envelope = encrypt_authenticated(recipient_pub, b"Sensitive Data")

    raw_ct = bytearray(base64.b64decode(envelope.ciphertext))
    raw_ct[0] ^= 0x01
    envelope.ciphertext = base64.b64encode(raw_ct).decode("utf-8")

    with pytest.raises(DecryptionAuthenticationError):
        decrypt_authenticated(recipient_priv, envelope)


def test_tampered_nonce_fails_decryption():
    recipient_priv, recipient_pub = generate_x25519_keypair()
    envelope = encrypt_authenticated(recipient_pub, b"Sensitive Data")

    raw_nonce = bytearray(base64.b64decode(envelope.nonce))
    raw_nonce[0] ^= 0x01
    envelope.nonce = base64.b64encode(raw_nonce).decode("utf-8")

    with pytest.raises(DecryptionAuthenticationError):
        decrypt_authenticated(recipient_priv, envelope)


def test_tampered_salt_fails_decryption():
    recipient_priv, recipient_pub = generate_x25519_keypair()
    envelope = encrypt_authenticated(recipient_pub, b"Sensitive Data")

    raw_salt = bytearray(base64.b64decode(envelope.salt))
    raw_salt[0] ^= 0x01
    envelope.salt = base64.b64encode(raw_salt).decode("utf-8")

    with pytest.raises(DecryptionAuthenticationError):
        decrypt_authenticated(recipient_priv, envelope)


def test_tampered_caller_associated_data_fails_decryption():
    recipient_priv, recipient_pub = generate_x25519_keypair()
    envelope = encrypt_authenticated(
        recipient_pub, b"Payload", associated_data=b"original_aad"
    )

    envelope.associated_data = base64.b64encode(b"tampered_aad").decode("utf-8")

    with pytest.raises(DecryptionAuthenticationError):
        decrypt_authenticated(recipient_priv, envelope)


def test_tampered_header_metadata_fails_decryption():
    recipient_priv, recipient_pub = generate_x25519_keypair()
    envelope = encrypt_authenticated(recipient_pub, b"Payload")

    # Tampering with algorithm metadata must cause AAD mismatch
    envelope.cipher = "ChaCha20-Poly1305-Tampered"  # type: ignore

    with pytest.raises(DecryptionAuthenticationError):
        decrypt_authenticated(recipient_priv, envelope)


def test_wrong_recipient_private_key_fails_decryption():
    _, recipient_pub = generate_x25519_keypair()
    attacker_priv, _ = generate_x25519_keypair()

    envelope = encrypt_authenticated(recipient_pub, b"Restricted Ops Intel")

    with pytest.raises(DecryptionAuthenticationError):
        decrypt_authenticated(attacker_priv, envelope)


def test_malformed_envelope_rejected_by_pydantic():
    recipient_priv, recipient_pub = generate_x25519_keypair()
    env = encrypt_authenticated(recipient_pub, b"Data")

    # Invalid nonce length (must be 12 bytes)
    bad_dict = env.model_dump()
    bad_dict["nonce"] = base64.b64encode(b"short").decode("utf-8")

    with pytest.raises(ValueError) as exc:
        EncryptionEnvelope(**bad_dict)
    assert "12 bytes" in str(exc.value)


# ---------------------------------------------------------------------------
# 4. Device Key Initialization & API Integration Tests
# ---------------------------------------------------------------------------

def test_device_key_initialization_updates_registry_and_filesystem():
    # Register member
    reg_resp = client.post(
        "/api/registry/members",
        json={"name": "Dev Commander", "team": "Alpha", "role": "Lead"},
    )
    assert reg_resp.status_code == 201
    dev_id = reg_resp.json()["device_id"]

    # Initialize keys via endpoint
    init_resp = client.post(f"/api/crypto/devices/{dev_id}/initialize")
    assert init_resp.status_code == 201
    data = init_resp.json()

    assert data["device_id"] == dev_id
    assert data["signing_public_key"] is not None
    assert data["encryption_public_key"] is not None
    assert data["status"] == "initialized"

    # Verify no private keys in response
    for key in data.keys():
        assert "private" not in key.lower()
        assert "secret" not in key.lower()

    # Verify registry record updated
    member_resp = client.get(f"/api/registry/devices/{dev_id}")
    assert member_resp.status_code == 200
    m_data = member_resp.json()
    assert m_data["signing_public_key"] == data["signing_public_key"]
    assert m_data["encryption_public_key"] == data["encryption_public_key"]

    # Verify status endpoint reports initialized
    status_resp = client.get(f"/api/crypto/devices/{dev_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["is_initialized"] is True


def test_public_keys_persist_across_reloads():
    reg_resp = client.post(
        "/api/registry/members",
        json={"name": "Persistent Unit", "team": "Ops", "role": "Medic"},
    )
    dev_id = reg_resp.json()["device_id"]
    init_resp = client.post(f"/api/crypto/devices/{dev_id}/initialize")
    pub_signing = init_resp.json()["signing_public_key"]

    # Fresh service instance reading from disk
    fresh_service = RegistryService(registry_path=registry_service.registry_path)
    member = fresh_service.get_member_by_device_id(dev_id)
    assert member is not None
    assert member.signing_public_key == pub_signing


def test_reinitializing_device_rejected_with_409():
    reg_resp = client.post(
        "/api/registry/members",
        json={"name": "Alpha Responder", "team": "Ops", "role": "Scout"},
    )
    dev_id = reg_resp.json()["device_id"]
    client.post(f"/api/crypto/devices/{dev_id}/initialize")

    # Second initialization must be rejected
    repeat_resp = client.post(f"/api/crypto/devices/{dev_id}/initialize")
    assert repeat_resp.status_code == 409
    assert "already cryptographically initialized" in repeat_resp.json()["detail"].lower()


def test_inconsistent_key_state_mismatch_rejected_with_409():
    reg_resp = client.post(
        "/api/registry/members",
        json={"name": "Inconsistent Unit", "team": "Ops", "role": "Scout"},
    )
    dev_id = reg_resp.json()["device_id"]
    client.post(f"/api/crypto/devices/{dev_id}/initialize")

    # Corrupt the registry public key so it no longer matches the local private key
    different_priv, different_pub = generate_ed25519_keypair()
    different_pub_b64 = encode_public_key_b64(different_pub)
    registry_service.update_member_public_keys(
        device_id=dev_id,
        signing_public_key=different_pub_b64,
        encryption_public_key=None,
    )

    # Calling initialize or consistency check must detect mismatch and reject
    resp = client.post(f"/api/crypto/devices/{dev_id}/initialize")
    assert resp.status_code == 409
    assert "inconsistent" in resp.json()["detail"].lower()


def test_partial_key_state_rejected_with_409():
    reg_resp = client.post(
        "/api/registry/members",
        json={"name": "Partial Unit", "team": "Ops", "role": "Scout"},
    )
    dev_id = reg_resp.json()["device_id"]

    # Create only one private key file manually (partial state)
    dev_dir = crypto_service._get_device_dir(dev_id)
    dev_dir.mkdir(parents=True, exist_ok=True)
    ed_priv, _ = generate_ed25519_keypair()
    (dev_dir / "signing_private.pem").write_bytes(serialize_private_key_pem(ed_priv))

    resp = client.post(f"/api/crypto/devices/{dev_id}/initialize")
    assert resp.status_code == 409
    assert "inconsistent" in resp.json()["detail"].lower()


def test_initializing_nonexistent_device_fails_404():
    resp = client.post("/api/crypto/devices/DEVICE-999/initialize")
    assert resp.status_code == 404


def test_initializing_revoked_device_fails_400():
    reg_resp = client.post(
        "/api/registry/members",
        json={"name": "Revoked Unit", "team": "Alpha", "role": "Medic"},
    )
    res_id = reg_resp.json()["rescue_id"]
    dev_id = reg_resp.json()["device_id"]

    # Revoke first
    client.post(f"/api/registry/members/{res_id}/revoke")

    # Initializing revoked device must fail
    resp = client.post(f"/api/crypto/devices/{dev_id}/initialize")
    assert resp.status_code == 400
    assert "revoked" in resp.json()["detail"].lower()


def test_staging_rollback_restores_original_state():
    reg_resp = client.post(
        "/api/registry/members",
        json={"name": "Rollback Test", "team": "Alpha", "role": "Medic"},
    )
    dev_id = reg_resp.json()["device_id"]

    # Simulate filesystem failure during finalization by making the target device dir a read-only file
    target_dir = crypto_service._get_device_dir(dev_id)
    target_dir.write_text("blocking file")

    with pytest.raises(Exception):
        crypto_service.initialize_device_keys(dev_id)

    # Check that registry public keys were rolled back to None
    member = registry_service.get_member_by_device_id(dev_id)
    assert member.signing_public_key is None
    assert member.encryption_public_key is None

    # Clean up blocking file
    target_dir.unlink()


def test_isolation_keys_created_in_tmp_path(isolate_crypto_and_registry: Path):
    assert crypto_service.keys_dir == isolate_crypto_and_registry / "keys"
    reg_resp = client.post(
        "/api/registry/members",
        json={"name": "Isolated Device", "team": "Alpha", "role": "Scout"},
    )
    dev_id = reg_resp.json()["device_id"]
    client.post(f"/api/crypto/devices/{dev_id}/initialize")

    # Assert keys exist in tmp_path / "keys"
    key_dir = isolate_crypto_and_registry / "keys" / dev_id
    assert (key_dir / "signing_private.pem").is_file()
    assert (key_dir / "encryption_private.pem").is_file()
