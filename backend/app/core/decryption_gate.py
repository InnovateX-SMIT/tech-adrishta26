import json
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.exceptions import InvalidSignature

# Import our registry functions from Phase 2
from backend.app.core.registry import get_member_by_rescue_id

# In a production app, this would write to a secure database or file
SECURITY_LOGS = []

def log_security_event(event: str, packet_id: str, sender_id: str, recipient_id: str, reason: str = None):
    """Logs security decisions without ever touching plaintext."""
    log_entry = {
        "event": event,
        "packet_id": packet_id,
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "timestamp": int(time.time())
    }
    if reason:
        log_entry["reason"] = reason
        
    SECURITY_LOGS.append(log_entry)
    return log_entry

def _verify_signature(packet: dict, sender_public_key_hex: str) -> bool:
    """Reconstructs the canonical packet and verifies the Ed25519 signature."""
    try:
        # Reconstruct the exact data that was signed (everything except the signature itself)
        signed_data = {k: v for k, v in packet.items() if k != "signature"}
        canonical_data = json.dumps(signed_data, sort_keys=True).encode('utf-8')
        
        public_key_bytes = bytes.fromhex(sender_public_key_hex)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        signature_bytes = bytes.fromhex(packet["signature"])
        
        public_key.verify(signature_bytes, canonical_data)
        return True
    except (InvalidSignature, ValueError, KeyError, TypeError):
        return False

def _decrypt_payload(ciphertext_hex: str, nonce_hex: str, ephemeral_public_key_hex: str, receiver_private_key_bytes: bytes) -> str:
    """Uses X25519 Key Agreement + ChaCha20Poly1305 to decrypt the payload."""
    receiver_priv = X25519PrivateKey.from_private_bytes(receiver_private_key_bytes)
    ephemeral_pub = X25519PublicKey.from_public_bytes(bytes.fromhex(ephemeral_public_key_hex))
    
    # Generate the shared secret
    shared_key = receiver_priv.exchange(ephemeral_pub)
    
    # Decrypt using ChaCha20-Poly1305
    chacha = ChaCha20Poly1305(shared_key)
    plaintext_bytes = chacha.decrypt(
        nonce=bytes.fromhex(nonce_hex),
        data=bytes.fromhex(ciphertext_hex),
        associated_data=None
    )
    return plaintext_bytes.decode('utf-8')

def process_incoming_packet(packet: dict, current_receiver_id: str, receiver_private_key_bytes: bytes, registry_path: str = None) -> dict:
    """
    The ultimate security gate. 
    Processes a packet through the 5-step verification flow before allowing decryption.
    """
    packet_id = packet.get("packet_id", "UNKNOWN")
    sender_id = packet.get("sender_id", "UNKNOWN")
    recipient_id = packet.get("recipient_id", "UNKNOWN")

    # STEP 1: Sender Registry Lookup
    sender = get_member_by_rescue_id(sender_id, filepath=registry_path) if registry_path else get_member_by_rescue_id(sender_id)
    if not sender:
        log_security_event("MESSAGE_REJECTED", packet_id, sender_id, recipient_id, "UNKNOWN_SENDER")
        return {"status": "REJECTED", "reason": "UNKNOWN_SENDER"}

    # STEP 2: Sender Status Validation
    if sender.get("status") != "active":
        reason = f"SENDER_{sender.get('status').upper()}"
        log_security_event("MESSAGE_REJECTED", packet_id, sender_id, recipient_id, reason)
        return {"status": "REJECTED", "reason": reason}

    # STEP 3: Digital Signature Verification
    if not _verify_signature(packet, sender["signing_public_key"]):
        log_security_event("MESSAGE_REJECTED", packet_id, sender_id, recipient_id, "INVALID_SIGNATURE")
        return {"status": "REJECTED", "reason": "INVALID_SIGNATURE"}

    # STEP 4: Recipient Authorization
    if recipient_id != current_receiver_id:
        log_security_event("MESSAGE_REJECTED", packet_id, sender_id, recipient_id, "UNAUTHORIZED_RECIPIENT")
        return {"status": "REJECTED", "reason": "UNAUTHORIZED_RECIPIENT"}

    # STEP 5: Decryption Gate
    try:
        plaintext = _decrypt_payload(
            ciphertext_hex=packet["ciphertext"],
            nonce_hex=packet["nonce"],
            ephemeral_public_key_hex=packet["ephemeral_public_key"],
            receiver_private_key_bytes=receiver_private_key_bytes
        )
    except Exception:
        log_security_event("MESSAGE_REJECTED", packet_id, sender_id, recipient_id, "DECRYPTION_FAILED")
        return {"status": "REJECTED", "reason": "DECRYPTION_FAILED"}

    # SUCCESS: If all checks pass, log the success and return the plaintext
    log_security_event("MESSAGE_DECRYPTED", packet_id, sender_id, recipient_id)
    return {
        "status": "SUCCESS",
        "message": plaintext,
        "sender_name": sender.get("name")
    }