import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from backend.app.config import settings
from backend.app.core.crypto import (
    CryptoError,
    decode_ed25519_public_key_b64,
    decode_x25519_public_key_b64,
    encode_public_key_b64,
    generate_ed25519_keypair,
    generate_x25519_keypair,
    load_ed25519_private_key_pem,
    load_x25519_private_key_pem,
    serialize_private_key_pem,
)
from backend.app.models.crypto import (
    DeviceCryptoInitResponse,
    DeviceCryptoStatusResponse,
)
from backend.app.models.registry import MemberStatus
from backend.app.services.registry_service import (
    MemberNotFoundError,
    RegistryService,
    registry_service as default_registry_service,
)


class CryptoServiceError(CryptoError):
    """Base exception for crypto service operations."""
    pass


class DeviceAlreadyInitializedError(CryptoServiceError):
    """Raised when a device is already initialized with matching key material."""
    pass


class InconsistentKeyStateError(CryptoServiceError):
    """Raised when partial, mismatched, or corrupted key material is detected."""
    pass


class DeviceRevokedError(CryptoServiceError):
    """Raised when key operations are attempted on a revoked device."""
    pass


class CriticalConsistencyError(CryptoServiceError):
    """Raised when an operation and its rollback both fail, requiring manual intervention."""
    pass


class CryptoService:
    """Manages cryptographic key lifecycle, two-phase staging, and local private-key storage.

    Development Storage Notice:
    Private keys are stored on the local filesystem as unencrypted PKCS8 PEM files
    protected by filesystem permissions. They are never returned in APIs, never logged,
    never placed in frontend state, and never committed to Git.
    """

    def __init__(
        self,
        keys_dir: Optional[Path] = None,
        registry_service_instance: Optional[RegistryService] = None,
    ):
        self.keys_dir = keys_dir or settings.keys_dir
        self.registry_service = registry_service_instance or default_registry_service

    def _get_device_dir(self, device_id: str) -> Path:
        return self.keys_dir / device_id

    def _get_signing_key_path(self, device_id: str) -> Path:
        return self._get_device_dir(device_id) / "signing_private.pem"

    def _get_encryption_key_path(self, device_id: str) -> Path:
        return self._get_device_dir(device_id) / "encryption_private.pem"

    def check_key_consistency(self, device_id: str) -> None:
        """Inspects both local filesystem and registry to verify key consistency.

        Raises:
            DeviceAlreadyInitializedError: If all 4 key indicators exist and derived public keys match registry.
            InconsistentKeyStateError: If keys are mismatched, corrupted, or partially present.
            MemberNotFoundError: If the device is not registered.
        """
        member = self.registry_service.get_member_by_device_id(device_id)
        if not member:
            raise MemberNotFoundError(f"Device '{device_id}' not found in registry.")

        signing_file_exists = self._get_signing_key_path(device_id).is_file()
        encryption_file_exists = self._get_encryption_key_path(device_id).is_file()
        registry_signing_exists = member.signing_public_key is not None
        registry_encryption_exists = member.encryption_public_key is not None

        indicators = [
            signing_file_exists,
            encryption_file_exists,
            registry_signing_exists,
            registry_encryption_exists,
        ]
        present_count = sum(1 for ind in indicators if ind)

        if present_count == 0:
            # Completely uninitialized: safe to proceed
            return

        if present_count == 4:
            # All 4 exist: verify derived public keys match registry exactly
            try:
                signing_pem = self._get_signing_key_path(device_id).read_bytes()
                encryption_pem = self._get_encryption_key_path(device_id).read_bytes()

                signing_priv = load_ed25519_private_key_pem(signing_pem)
                encryption_priv = load_x25519_private_key_pem(encryption_pem)

                derived_signing_pub_b64 = encode_public_key_b64(signing_priv.public_key())
                derived_encryption_pub_b64 = encode_public_key_b64(encryption_priv.public_key())

                if (
                    derived_signing_pub_b64 == member.signing_public_key
                    and derived_encryption_pub_b64 == member.encryption_public_key
                ):
                    raise DeviceAlreadyInitializedError(
                        f"Device '{device_id}' is already cryptographically initialized."
                    )
                else:
                    raise InconsistentKeyStateError(
                        f"Inconsistent cryptographic state: local private keys do not match public keys in registry for device '{device_id}'. Manual recovery required."
                    )
            except (DeviceAlreadyInitializedError, InconsistentKeyStateError):
                raise
            except Exception as exc:
                raise InconsistentKeyStateError(
                    f"Failed to verify existing key consistency for device '{device_id}': {exc}"
                ) from exc

        # Partial key state (1, 2, or 3 indicators present)
        raise InconsistentKeyStateError(
            f"Inconsistent cryptographic state detected for device '{device_id}'. "
            f"Local keys exist={signing_file_exists and encryption_file_exists}, "
            f"Registry keys exist={registry_signing_exists and registry_encryption_exists}. "
            f"Manual recovery required."
        )

    def initialize_device_keys(self, device_id: str) -> DeviceCryptoInitResponse:
        """Initializes cryptographic keypairs for a device using two-phase staging atomicity.

        Workflow:
        1. Validates device existence and active status.
        2. Validates key state (rejects if already initialized or inconsistent).
        3. Generates Ed25519 and X25519 keypairs.
        4. Writes private keys to a temporary staging directory.
        5. Updates registry with Base64 raw 32-byte public keys.
        6. On registry success: moves staging files to permanent device directory.
        7. On staging failure: rolls back registry to exact previous state.

        Returns safe public metadata without exposing private keys.
        """
        member = self.registry_service.get_member_by_device_id(device_id)
        if not member:
            raise MemberNotFoundError(f"Device '{device_id}' not found in registry.")

        if member.status == MemberStatus.REVOKED:
            raise DeviceRevokedError(f"Cannot initialize cryptographic keys for revoked device '{device_id}'.")

        # Two-sided key consistency check
        self.check_key_consistency(device_id)

        # Capture original state for exact rollback
        orig_signing = member.signing_public_key
        orig_encryption = member.encryption_public_key

        # 1. Generate keypairs
        signing_priv, signing_pub = generate_ed25519_keypair()
        encryption_priv, encryption_pub = generate_x25519_keypair()

        signing_pub_b64 = encode_public_key_b64(signing_pub)
        encryption_pub_b64 = encode_public_key_b64(encryption_pub)

        # 2. Stage private keys in a temporary staging directory
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        staging_dir = self.keys_dir / f".staging_{device_id}_{uuid.uuid4().hex[:8]}"
        staging_dir.mkdir(parents=True, exist_ok=True)

        try:
            (staging_dir / "signing_private.pem").write_bytes(serialize_private_key_pem(signing_priv))
            (staging_dir / "encryption_private.pem").write_bytes(serialize_private_key_pem(encryption_priv))
        except Exception as exc:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise CryptoServiceError(f"Failed to write staged private keys: {exc}") from exc

        # 3. Update public keys in registry
        try:
            self.registry_service.update_member_public_keys(
                device_id=device_id,
                signing_public_key=signing_pub_b64,
                encryption_public_key=encryption_pub_b64,
            )
        except Exception as exc:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise CryptoServiceError(f"Registry public key update failed: {exc}") from exc

        # 4. Finalize private keys from staging to permanent device directory
        target_dir = self._get_device_dir(device_id)
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            sign_target = target_dir / "signing_private.pem"
            enc_target = target_dir / "encryption_private.pem"
            os.replace(staging_dir / "signing_private.pem", sign_target)
            os.replace(staging_dir / "encryption_private.pem", enc_target)
            try:
                os.chmod(target_dir, 0o700)
                os.chmod(sign_target, 0o600)
                os.chmod(enc_target, 0o600)
            except OSError:
                pass
            shutil.rmtree(staging_dir, ignore_errors=True)
        except Exception as exc:
            # Staging finalization failed: perform exact rollback of registry
            try:
                self.registry_service.update_member_public_keys(
                    device_id=device_id,
                    signing_public_key=orig_signing,
                    encryption_public_key=orig_encryption,
                )
            except Exception as rb_exc:
                shutil.rmtree(staging_dir, ignore_errors=True)
                raise CriticalConsistencyError(
                    f"Critical failure: private key finalization failed ({exc}) and registry rollback failed ({rb_exc}). "
                    f"Device '{device_id}' requires manual administrative intervention."
                ) from rb_exc

            shutil.rmtree(staging_dir, ignore_errors=True)
            raise CryptoServiceError(f"Failed to finalize private keys on disk: {exc}") from exc

        return DeviceCryptoInitResponse(
            device_id=device_id,
            rescue_id=member.rescue_id,
            signing_public_key=signing_pub_b64,
            encryption_public_key=encryption_pub_b64,
            status="initialized",
        )

    def get_device_crypto_status(self, device_id: str) -> DeviceCryptoStatusResponse:
        """Retrieves public cryptographic readiness status for a device."""
        member = self.registry_service.get_member_by_device_id(device_id)
        if not member:
            raise MemberNotFoundError(f"Device '{device_id}' not found in registry.")

        signing_file_exists = self._get_signing_key_path(device_id).is_file()
        encryption_file_exists = self._get_encryption_key_path(device_id).is_file()
        registry_keys_present = (
            member.signing_public_key is not None
            and member.encryption_public_key is not None
        )

        is_initialized = signing_file_exists and encryption_file_exists and registry_keys_present

        return DeviceCryptoStatusResponse(
            device_id=device_id,
            rescue_id=member.rescue_id,
            is_initialized=is_initialized,
            signing_public_key=member.signing_public_key,
            encryption_public_key=member.encryption_public_key,
        )

    def load_device_signing_private_key(self, device_id: str):
        """Loads the local Ed25519 signing private key for a device."""
        key_path = self._get_signing_key_path(device_id)
        if not key_path.is_file():
            raise CryptoServiceError(f"Signing private key not found for device '{device_id}'.")
        return load_ed25519_private_key_pem(key_path.read_bytes())

    def load_device_encryption_private_key(self, device_id: str):
        """Loads the local X25519 encryption private key for a device."""
        key_path = self._get_encryption_key_path(device_id)
        if not key_path.is_file():
            raise CryptoServiceError(f"Encryption private key not found for device '{device_id}'.")
        return load_x25519_private_key_pem(key_path.read_bytes())


# Default singleton instance
crypto_service = CryptoService()
