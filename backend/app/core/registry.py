import json
import os

# Resolves the path to data/registry.json based on the project structure
# backend/app/core/registry.py -> ../../../data/registry.json
DEFAULT_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "../../../data/registry.json")

def _load_registry(filepath: str = DEFAULT_REGISTRY_PATH) -> dict:
    """Helper function to load the JSON file safely."""
    if not os.path.exists(filepath):
        # Create directory and return empty registry if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        return {"members": []}
        
    with open(filepath, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"members": []}

def _save_registry(data: dict, filepath: str = DEFAULT_REGISTRY_PATH):
    """Helper function to save data back to the JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def register_member(rescue_id: str, name: str, team: str, role: str, 
                    device_id: str, signing_public_key: str, 
                    encryption_public_key: str, 
                    filepath: str = DEFAULT_REGISTRY_PATH) -> dict:
    """Registers a new rescue member and saves their public keys."""
    registry = _load_registry(filepath)
    
    # Check for duplicates to prevent accidental double-registration
    for member in registry["members"]:
        if member["rescue_id"] == rescue_id:
            raise ValueError(f"Member with Rescue ID {rescue_id} already exists.")
        if member["device_id"] == device_id:
            raise ValueError(f"Device ID {device_id} is already registered.")

    new_member = {
        "rescue_id": rescue_id,
        "name": name,
        "team": team,
        "role": role,
        "device_id": device_id,
        "signing_public_key": signing_public_key,
        "encryption_public_key": encryption_public_key,
        "status": "active"  # Default status on creation
    }
    
    registry["members"].append(new_member)
    _save_registry(registry, filepath)
    
    return new_member

def get_member_by_rescue_id(rescue_id: str, filepath: str = DEFAULT_REGISTRY_PATH) -> dict:
    """Finds a member using their RESQ ID."""
    registry = _load_registry(filepath)
    for member in registry["members"]:
        if member["rescue_id"] == rescue_id:
            return member
    return None

def get_member_by_device_id(device_id: str, filepath: str = DEFAULT_REGISTRY_PATH) -> dict:
    """Finds a member using their device's unique ID."""
    registry = _load_registry(filepath)
    for member in registry["members"]:
        if member["device_id"] == device_id:
            return member
    return None

def is_member_active(rescue_id: str, filepath: str = DEFAULT_REGISTRY_PATH) -> bool:
    """Checks if a member is currently authorized (active)."""
    member = get_member_by_rescue_id(rescue_id, filepath)
    if member:
        return member.get("status") == "active"
    return False

def revoke_member(rescue_id: str, filepath: str = DEFAULT_REGISTRY_PATH) -> bool:
    """Revokes a member's access by changing their status."""
    registry = _load_registry(filepath)
    for member in registry["members"]:
        if member["rescue_id"] == rescue_id:
            member["status"] = "revoked"
            _save_registry(registry, filepath)
            return True
    return False