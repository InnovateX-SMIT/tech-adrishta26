import unittest
import os
import sys
import json
import shutil
from pathlib import Path

# Ensure project root is on sys.path when running script directly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Importing the logic we built in the previous steps
from backend.app.core.identity import generate_device_identity
from backend.app.core.registry import (
    register_member, get_member_by_rescue_id, 
    get_member_by_device_id, is_member_active, revoke_member
)

class TestPhase2RegistryAndIdentity(unittest.TestCase):
    
    def setUp(self):
        """Runs before every test: Sets up a safe, temporary testing environment."""
        self.test_dir = "test_env"
        self.keys_dir = os.path.join(self.test_dir, "keys")
        self.registry_path = os.path.join(self.test_dir, "test_registry.json")
        
        os.makedirs(self.keys_dir, exist_ok=True)
        
        # Initialize an empty registry schema matching your requirement
        with open(self.registry_path, 'w') as f:
            json.dump({"version": 1, "members": []}, f)

    def tearDown(self):
        """Runs after every test: Deletes the temporary test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_full_member_lifecycle(self):
        # 1. Generate Identity for a new test device
        test_device_id = "DEVICE-TEST-99"
        keys = generate_device_identity(test_device_id, keys_dir=self.keys_dir)
        
        # ✅ Unique Device ID?
        self.assertEqual(keys["device_id"], test_device_id)
        
        # ✅ Public keys are generated?
        self.assertIn("signing_public_key", keys)
        self.assertIn("encryption_public_key", keys)
        
        # ✅ Private keys are NOT in registry payload?
        self.assertNotIn("private", str(keys).lower())
        
        # ✅ Private keys are saved locally?
        self.assertTrue(os.path.exists(os.path.join(self.keys_dir, f"{test_device_id}_sign.pem")))
        self.assertTrue(os.path.exists(os.path.join(self.keys_dir, f"{test_device_id}_enc.pem")))
        
        # 2. Register Member in the database
        test_rescue_id = "RESQ-TEST-99"
        member = register_member(
            rescue_id=test_rescue_id,
            name="Test Automator",
            team="QA Team",
            role="Tester",
            device_id=test_device_id,
            signing_public_key=keys["signing_public_key"],
            encryption_public_key=keys["encryption_public_key"],
            filepath=self.registry_path
        )
        
        # ✅ Member registered successfully?
        self.assertEqual(member["rescue_id"], test_rescue_id)
        
        # 3. Test Registry Lookups
        
        # ✅ Rescue ID se member mil raha hai?
        found_by_resq = get_member_by_rescue_id(test_rescue_id, filepath=self.registry_path)
        self.assertIsNotNone(found_by_resq)
        self.assertEqual(found_by_resq["name"], "Test Automator")
        
        # ✅ Device ID se member mil raha hai?
        found_by_device = get_member_by_device_id(test_device_id, filepath=self.registry_path)
        self.assertIsNotNone(found_by_device)
        self.assertEqual(found_by_device["rescue_id"], test_rescue_id)
        
        # 4. Test Status and Revocation
        
        # ✅ Active member active return hota hai?
        self.assertTrue(is_member_active(test_rescue_id, filepath=self.registry_path))
        
        # Revoke the member
        revoke_member(test_rescue_id, filepath=self.registry_path)
        
        # ✅ Revoked member active return NAHI hota?
        self.assertFalse(is_member_active(test_rescue_id, filepath=self.registry_path))
        
        # Check that the database actually saved the revoked status
        revoked_member = get_member_by_rescue_id(test_rescue_id, filepath=self.registry_path)
        self.assertEqual(revoked_member["status"], "revoked")

if __name__ == "__main__":
    unittest.main()