import base64
import json
import os
from typing import Optional, Tuple, Union
from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from backend.app.models.crypto import EncryptionEnvelope


class CryptoError(Exception):
    """Base exception for cryptographic operations."""
    pass


class InvalidKeyTypeError(CryptoError):
    """Raised when loaded key does not match the expected cryptographic type."""
    pass


class InvalidPublicKeyError(CryptoError):
    """Raised when a public key cannot be decoded or has an invalid length."""
    pass


class DecryptionAuthenticationError(CryptoError):
    """Raised when authenticated decryption fails due to tag mismatch or tampering."""
    pass


def build_envelope_aad(
    version: int,
    key_agreement: str,
    kdf: str,
    cipher: str,
    ephemeral_public_key_b64: str,
    salt_b64: str,
    nonce_b64: str,
    caller_aad_b64: Optional[str] = None,
) -> bytes:
    """Canonical shared helper to build authenticated associated data (AAD).

    Binds the envelope metadata header and optional caller associated data
    to prevent algorithm substitution or metadata tampering. Both encryption
    and decryption MUST use this exact helper.
    """
    header_part = f"{version}|{key_agreement}|{kdf}|{cipher}|{ephemeral_public_key_b64}|{salt_b64}|{nonce_b64}"
    if caller_aad_b64:
        return f"{header_part}:{caller_aad_b64}".encode("utf-8")
    return header_part.encode("utf-8")


def generate_ed25519_keypair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Generates an Ed25519 keypair for digital signatures."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def generate_x25519_keypair() -> Tuple[x25519.X25519PrivateKey, x25519.X25519PublicKey]:
    """Generates an X25519 keypair for Diffie-Hellman key agreement."""
    private_key = x25519.X25519PrivateKey.generate()
    return private_key, private_key.public_key()


def encode_public_key_b64(key: Union[ed25519.Ed25519PublicKey, x25519.X25519PublicKey]) -> str:
    """Serializes a public key to raw 32 bytes and encodes as Base64."""
    raw_bytes = key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw_bytes).decode("utf-8")


def decode_ed25519_public_key_b64(b64_str: str) -> ed25519.Ed25519PublicKey:
    """Decodes a Base64 string into an Ed25519PublicKey, validating exact 32-byte length."""
    try:
        raw = base64.b64decode(b64_str)
        if len(raw) != 32:
            raise InvalidPublicKeyError(f"Ed25519 public key must be exactly 32 bytes, got {len(raw)}.")
        return ed25519.Ed25519PublicKey.from_public_bytes(raw)
    except Exception as exc:
        if isinstance(exc, InvalidPublicKeyError):
            raise
        raise InvalidPublicKeyError(f"Failed to decode Ed25519 public key: {exc}") from exc


def decode_x25519_public_key_b64(b64_str: str) -> x25519.X25519PublicKey:
    """Decodes a Base64 string into an X25519PublicKey, validating exact 32-byte length."""
    try:
        raw = base64.b64decode(b64_str)
        if len(raw) != 32:
            raise InvalidPublicKeyError(f"X25519 public key must be exactly 32 bytes, got {len(raw)}.")
        return x25519.X25519PublicKey.from_public_bytes(raw)
    except Exception as exc:
        if isinstance(exc, InvalidPublicKeyError):
            raise
        raise InvalidPublicKeyError(f"Failed to decode X25519 public key: {exc}") from exc


def serialize_private_key_pem(key: Union[ed25519.Ed25519PrivateKey, x25519.X25519PrivateKey]) -> bytes:
    """Serializes a private key to unencrypted PKCS8 PEM format for local prototype storage."""
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def load_ed25519_private_key_pem(pem_bytes: bytes) -> ed25519.Ed25519PrivateKey:
    """Loads an Ed25519 private key from PKCS8 PEM bytes with strict type checking."""
    try:
        loaded = serialization.load_pem_private_key(pem_bytes, password=None)
        if not isinstance(loaded, ed25519.Ed25519PrivateKey):
            raise InvalidKeyTypeError(f"Expected Ed25519PrivateKey, got {type(loaded).__name__}.")
        return loaded
    except Exception as exc:
        if isinstance(exc, InvalidKeyTypeError):
            raise
        raise CryptoError(f"Failed to load Ed25519 private key: {exc}") from exc


def load_x25519_private_key_pem(pem_bytes: bytes) -> x25519.X25519PrivateKey:
    """Loads an X25519 private key from PKCS8 PEM bytes with strict type checking."""
    try:
        loaded = serialization.load_pem_private_key(pem_bytes, password=None)
        if not isinstance(loaded, x25519.X25519PrivateKey):
            raise InvalidKeyTypeError(f"Expected X25519PrivateKey, got {type(loaded).__name__}.")
        return loaded
    except Exception as exc:
        if isinstance(exc, InvalidKeyTypeError):
            raise
        raise CryptoError(f"Failed to load X25519 private key: {exc}") from exc


def sign_bytes(private_key: ed25519.Ed25519PrivateKey, data: bytes) -> str:
    """Signs arbitrary bytes using Ed25519 and returns Base64 signature."""
    signature = private_key.sign(data)
    return base64.b64encode(signature).decode("utf-8")


def verify_signature(public_key: ed25519.Ed25519PublicKey, data: bytes, signature_b64: str) -> bool:
    """Verifies an Ed25519 signature against data.

    Returns True if valid, False if invalid, tampered, wrong length, or malformed.
    Never raises internal cryptography errors to caller.
    """
    try:
        sig_bytes = base64.b64decode(signature_b64)
        if len(sig_bytes) != 64:
            return False
        public_key.verify(sig_bytes, data)
        return True
    except (InvalidSignature, ValueError, Exception):
        return False


def canonicalize_payload(payload: dict) -> bytes:
    """Produces deterministic UTF-8 canonical JSON bytes regardless of key insertion order."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def derive_shared_secret(
    private_key: x25519.X25519PrivateKey,
    peer_public_key: x25519.X25519PublicKey,
) -> bytes:
    """Performs X25519 Diffie-Hellman key exchange to derive a 32-byte shared secret."""
    return private_key.exchange(peer_public_key)


def derive_encryption_key(
    shared_secret: bytes,
    salt: bytes,
    info: bytes = b"resq-chacha20-poly1305-v1",
) -> bytes:
    """Derives a 32-byte symmetric key using HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=info,
    )
    return hkdf.derive(shared_secret)


def encrypt_authenticated(
    recipient_public_key: x25519.X25519PublicKey,
    plaintext: bytes,
    associated_data: Optional[bytes] = None,
) -> EncryptionEnvelope:
    """Encrypts plaintext with ChaCha20-Poly1305 using fresh ephemeral X25519, salt, and nonce.

    Explicitly supports empty plaintext b"".
    """
    # 1. Generate fresh ephemeral X25519 keypair
    ephemeral_priv, ephemeral_pub = generate_x25519_keypair()
    ephemeral_pub_b64 = encode_public_key_b64(ephemeral_pub)

    # 2. Generate fresh random 16-byte HKDF salt
    salt = os.urandom(16)
    salt_b64 = base64.b64encode(salt).decode("utf-8")

    # 3. Derive symmetric key via X25519 + HKDF-SHA256
    shared_secret = derive_shared_secret(ephemeral_priv, recipient_public_key)
    symmetric_key = derive_encryption_key(shared_secret, salt)

    # 4. Generate fresh 12-byte nonce
    nonce = os.urandom(12)
    nonce_b64 = base64.b64encode(nonce).decode("utf-8")

    # 5. Build AAD binding envelope header + caller AAD
    caller_aad_b64 = base64.b64encode(associated_data).decode("utf-8") if associated_data else None
    aad_bytes = build_envelope_aad(
        version=1,
        key_agreement="X25519",
        kdf="HKDF-SHA256",
        cipher="ChaCha20-Poly1305",
        ephemeral_public_key_b64=ephemeral_pub_b64,
        salt_b64=salt_b64,
        nonce_b64=nonce_b64,
        caller_aad_b64=caller_aad_b64,
    )

    # 6. Encrypt with ChaCha20-Poly1305
    chacha = ChaCha20Poly1305(symmetric_key)
    ciphertext = chacha.encrypt(nonce, plaintext, aad_bytes)
    ciphertext_b64 = base64.b64encode(ciphertext).decode("utf-8")

    return EncryptionEnvelope(
        version=1,
        key_agreement="X25519",
        kdf="HKDF-SHA256",
        cipher="ChaCha20-Poly1305",
        ephemeral_public_key=ephemeral_pub_b64,
        salt=salt_b64,
        nonce=nonce_b64,
        ciphertext=ciphertext_b64,
        associated_data=caller_aad_b64,
    )


def decrypt_authenticated(
    recipient_private_key: x25519.X25519PrivateKey,
    envelope: EncryptionEnvelope,
) -> bytes:
    """Decrypts and verifies an EncryptionEnvelope using recipient's long-term X25519 private key.

    Reconstructs AAD using the identical shared helper.
    Raises DecryptionAuthenticationError if tag verification fails or data is tampered with.
    """
    # 1. Parse ephemeral public key, salt, nonce, ciphertext
    ephemeral_pub = decode_x25519_public_key_b64(envelope.ephemeral_public_key)
    salt = base64.b64decode(envelope.salt)
    nonce = base64.b64decode(envelope.nonce)
    ciphertext = base64.b64decode(envelope.ciphertext)

    # 2. Derive symmetric key
    shared_secret = derive_shared_secret(recipient_private_key, ephemeral_pub)
    symmetric_key = derive_encryption_key(shared_secret, salt)

    # 3. Reconstruct identical AAD using shared helper
    aad_bytes = build_envelope_aad(
        version=envelope.version,
        key_agreement=envelope.key_agreement,
        kdf=envelope.kdf,
        cipher=envelope.cipher,
        ephemeral_public_key_b64=envelope.ephemeral_public_key,
        salt_b64=envelope.salt,
        nonce_b64=envelope.nonce,
        caller_aad_b64=envelope.associated_data,
    )

    # 4. Decrypt and authenticate
    chacha = ChaCha20Poly1305(symmetric_key)
    try:
        return chacha.decrypt(nonce, ciphertext, aad_bytes)
    except InvalidTag as exc:
        raise DecryptionAuthenticationError(
            "ChaCha20-Poly1305 authentication failed: ciphertext, nonce, salt, or metadata has been tampered with."
        ) from exc
