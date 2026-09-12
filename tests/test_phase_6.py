import unittest
import os
import sys
import json
import shutil
import time
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import serialization

# Ensure project root is on sys.path when running script directly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.core.decryption_gate import process_incoming_packet, SECURITY_LOGS

class TestPhase6DecryptionGate(unittest.TestCase):
    def setUp(self):
        """Set up a temporary registry and cryptographic keys for testing."""
        self.test_dir = "test_env_phase6"
        os.makedirs(self.test_dir, exist_ok=True)
        self.registry_path = os.path.join(self.test_dir, "test_registry.json")
        
        # Clear logs before each test
        SECURITY_LOGS.clear()

        # 1. Generate keys for Sender (RESQ-001)
        self.sender_sign_priv = ed25519.Ed25519PrivateKey.generate()
        self.sender_sign_pub_hex = self._export_pub(self.sender_sign_priv.public_key())
        
        # 2. Generate keys for Receiver (RESQ-002)
        self.receiver_enc_priv = x25519.X25519PrivateKey.generate()
        self.receiver_enc_pub_hex = self._export_pub(self.receiver_enc_priv.public_key())

        # 3. Generate keys for Revoked Sender (RESQ-003)
        self.revoked_sign_priv = ed25519.Ed25519PrivateKey.generate()
        self.revoked_sign_pub_hex = self._export_pub(self.revoked_sign_priv.public_key())

        # 4. Build the mock registry database
        registry_data = {
            "version": 1,
            "members": [
                {
                    "rescue_id": "RESQ-001",
                    "name": "Active Sender",
                    "signing_public_key": self.sender_sign_pub_hex,
                    "status": "active"
                },
                {
                    "rescue_id": "RESQ-002",
                    "name": "Active Receiver",
                    "encryption_public_key": self.receiver_enc_pub_hex,
                    "status": "active"
                },
                {
                    "rescue_id": "RESQ-003",
                    "name": "Revoked Sender",
                    "signing_public_key": self.revoked_sign_pub_hex,
                    "status": "revoked"
                }
            ]
        }
        with open(self.registry_path, 'w') as f:
            json.dump(registry_data, f)

    def tearDown(self):
        """Clean up the test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _export_pub(self, key_obj) -> str:
        """Helper to get Raw Hex of a public key."""
        return key_obj.public_bytes(
            encoding=serialization.Encoding.Raw, 
            format=serialization.PublicFormat.Raw
        ).hex()

    def _create_mock_phase5_packet(self, sender_id: str, recipient_id: str, message: str, 
                                   sender_priv_sign_key, receiver_pub_enc_hex: str) -> dict:
        """Simulates Phase 5: Encrypts and signs a packet mathematically."""
        # A. Ephemeral Encryption (X25519 + ChaCha20Poly1305)
        ephemeral_priv = x25519.X25519PrivateKey.generate()
        ephemeral_pub_hex = self._export_pub(ephemeral_priv.public_key())
        
        receiver_pub = x25519.X25519PublicKey.from_public_bytes(bytes.fromhex(receiver_pub_enc_hex))
        shared_key = ephemeral_priv.exchange(receiver_pub)
        
        chacha = ChaCha20Poly1305(shared_key)
        nonce = os.urandom(12)
        ciphertext = chacha.encrypt(nonce, message.encode('utf-8'), None)

        # B. Construct Packet Body
        packet = {
            "packet_id": f"PKT-{int(time.time())}",
            "message_id": f"MSG-{int(time.time())}",
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "timestamp": int(time.time()),
            "nonce": nonce.hex(),
            "ephemeral_public_key": ephemeral_pub_hex,
            "ciphertext": ciphertext.hex()
        }

        # C. Generate Canonical Signature (Ed25519)
        canonical_data = json.dumps(packet, sort_keys=True).encode('utf-8')
        signature = sender_priv_sign_key.sign(canonical_data)
        packet["signature"] = signature.hex()

        return packet

    # =========================================================================
    # THE 6 SECURITY SCENARIOS
    # =========================================================================

    def test_1_valid_message(self):
        """Test 1: Registered + active + valid signature + authorized recipient -> ✅ DECRYPT"""
        packet = self._create_mock_phase5_packet(
            "RESQ-001", "RESQ-002", "SOS: trapped person", 
            self.sender_sign_priv, self.receiver_enc_pub_hex
        )
        
        # Receiver processes it using their private key bytes
        receiver_priv_bytes = self.receiver_enc_priv.private_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        result = process_incoming_packet(packet, "RESQ-002", receiver_priv_bytes, self.registry_path)
        
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["message"], "SOS: trapped person")
        self.assertEqual(SECURITY_LOGS[-1]["event"], "MESSAGE_DECRYPTED")

    def test_2_unknown_sender(self):
        """Test 2: Unknown sender -> ❌ REJECT"""
        packet = self._create_mock_phase5_packet(
            "RESQ-999", "RESQ-002", "Fake Message", 
            self.sender_sign_priv, self.receiver_enc_pub_hex
        )
        
        result = process_incoming_packet(packet, "RESQ-002", b'dummy_key', self.registry_path)
        
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "UNKNOWN_SENDER")
        self.assertNotIn("message", result) # Ensure plaintext didn't leak

    def test_3_revoked_sender(self):
        """Test 3: Revoked sender -> ❌ REJECT"""
        packet = self._create_mock_phase5_packet(
            "RESQ-003", "RESQ-002", "I am revoked", 
            self.revoked_sign_priv, self.receiver_enc_pub_hex
        )
        
        result = process_incoming_packet(packet, "RESQ-002", b'dummy_key', self.registry_path)
        
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "SENDER_REVOKED")

    def test_4_modified_packet(self):
        """Test 4: Modified packet / Tampered Ciphertext -> ❌ REJECT"""
        packet = self._create_mock_phase5_packet(
            "RESQ-001", "RESQ-002", "Real Message", 
            self.sender_sign_priv, self.receiver_enc_pub_hex
        )
        
        # Attacker intercepts and changes a single letter in the ciphertext
        packet["ciphertext"] = packet["ciphertext"].replace("a", "b", 1)
        
        result = process_incoming_packet(packet, "RESQ-002", b'dummy_key', self.registry_path)
        
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "INVALID_SIGNATURE")

    def test_5_unauthorized_recipient(self):
        """Test 5: Unauthorized recipient -> ❌ REJECT"""
        # Packet meant for RESQ-005
        packet = self._create_mock_phase5_packet(
            "RESQ-001", "RESQ-005", "Secret Message", 
            self.sender_sign_priv, self.receiver_enc_pub_hex
        )
        
        # Current device belongs to RESQ-002
        result = process_incoming_packet(packet, "RESQ-002", b'dummy_key', self.registry_path)
        
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "UNAUTHORIZED_RECIPIENT")

    def test_6_wrong_decryption_key(self):
        """Test 6: Wrong decryption key -> ❌ REJECT"""
        packet = self._create_mock_phase5_packet(
            "RESQ-001", "RESQ-002", "Valid Message", 
            self.sender_sign_priv, self.receiver_enc_pub_hex
        )
        
        # User provides the WRONG private key (e.g., they generated a new one)
        wrong_priv_key = x25519.X25519PrivateKey.generate()
        wrong_priv_bytes = wrong_priv_key.private_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        result = process_incoming_packet(packet, "RESQ-002", wrong_priv_bytes, self.registry_path)
        
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "DECRYPTION_FAILED")

if __name__ == "__main__":
    unittest.main()